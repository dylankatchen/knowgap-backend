# services/skill_video_service.py
import logging
import re
import uuid
from datetime import datetime, timezone

from config import Config
from mongodb import get_db
from services.achieveup_auth_service import (
    achieveup_verify_token,
    get_user_canvas_token,
    require_instructor
)
from services.achieveup_service import (
    achieveup_question_skills_collection,
    achieveup_skill_matrices_collection,
    achieveup_course_descriptions_collection,
    get_saved_course_channels,
    check_course_instructor,
    require_course_instructor
)
from utils.ai_utils import generate_skill_search_topics
from utils.youtube_utils import fetch_videos_for_topic, get_video_metadata, fetch_video_transcript, fetch_videos_for_topic_and_channel

logger = logging.getLogger(__name__)

db = get_db()

skill_videos_collection = db[Config.ACHIEVEUP_SKILL_VIDEOS_COLLECTION]
skill_video_votes_collection = db[Config.ACHIEVEUP_SKILL_VIDEO_VOTES_COLLECTION]
quizzes_collection = db[Config.QUIZZES_COLLECTION]


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _serialize_video(doc):
    return {
        '_id': doc['_id'],
        'course_id': doc.get('course_id'),
        'matrix_id': doc.get('matrix_id'),
        'skill_name': doc.get('skill_name'),
        'title': doc.get('title'),
        'link': doc.get('link'),
        'channel': doc.get('channel'),
        'thumbnail': doc.get('thumbnail'),
        'source': doc.get('source'),
        'status': doc.get('status'),
        'added_by': doc.get('added_by'),
        'instructor_verified': doc.get('instructor_verified', False),
        'prioritize': doc.get('prioritize', False),
        'timestamp_seconds': doc.get('timestamp_seconds'),
        'created_at': doc['created_at'].isoformat() if isinstance(doc.get('created_at'), datetime) else doc.get('created_at'),
        'updated_at': doc['updated_at'].isoformat() if isinstance(doc.get('updated_at'), datetime) else doc.get('updated_at'),
    }


def _display_rank(doc):
    """Sort key: 0 for instructor-added videos, 1 for AI picks from linked
    channels, 2 for other AI picks (including ones saved before this PR)."""
    if doc.get('source') == 'manual':
        return 0
    return 1 if doc.get('prioritize') else 2


async def _resolve_matrix_id(course_id: str, matrix_id: str, skill_name: str) -> str:
    """Resolve a matrix_id for (course_id, skill_name) when the caller doesn't know it."""
    if matrix_id:
        return matrix_id

    matrix = await achieveup_skill_matrices_collection.find_one({
        'course_id': course_id,
        'skills': skill_name
    })
    if matrix:
        return matrix['_id']

    return 'primary'


async def get_skill_videos(token: str, course_id: str, skill_name: str, matrix_id: str = None) -> dict:
    """Get the curated video list for a skill — both instructor-added and AI-suggested videos are
    visible to everyone; the frontend tags them by `source` (manual vs ai_suggested)."""
    try:
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result

        user = user_result['user']

        resolved_matrix_id = await _resolve_matrix_id(course_id, matrix_id, skill_name)

        query = {
            'course_id': course_id,
            'matrix_id': resolved_matrix_id,
            'skill_name': skill_name,
            'status': 'published',
        }

        videos = []
        async for doc in skill_videos_collection.find(query).sort('created_at', 1):
            videos.append(doc)
        # Instructor-added first, then AI picks from linked channels, then
        # other AI picks. The sort is stable, so each group stays oldest-first.
        videos.sort(key=_display_rank)

        video_ids = [v['_id'] for v in videos]
        vote_counts = await get_video_vote_counts(course_id, resolved_matrix_id, skill_name, video_ids, user.get('id'))

        serialized = []
        for v in videos:
            video_json = _serialize_video(v)
            counts = vote_counts.get(v['_id'], {})
            video_json['upvotes'] = counts.get('upvotes', 0)
            video_json['downvotes'] = counts.get('downvotes', 0)
            video_json['student_vote'] = counts.get('student_vote')
            serialized.append(video_json)

        return {'videos': serialized, 'matrix_id': resolved_matrix_id}

    except Exception as e:
        logger.error(f"Get skill videos error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}


async def add_skill_video(token: str, course_id: str, skill_name: str, link: str,
                           matrix_id: str = None, title: str = None, channel: str = None,
                           thumbnail: str = None, source: str = 'manual') -> dict:
    """Instructor adds a video to a skill's curated list."""
    try:
        user, error = await require_instructor(token)
        if error:
            return error

        if not link:
            return {'error': 'Missing link', 'message': 'Video link is required', 'statusCode': 400}

        resolved_matrix_id = await _resolve_matrix_id(course_id, matrix_id, skill_name)

        if not title or not channel or not thumbnail:
            metadata = await get_video_metadata(link)
            if 'error' not in metadata:
                title = title or metadata.get('title')
                channel = channel or metadata.get('channel')
                thumbnail = thumbnail or metadata.get('thumbnail')

        now = _now()
        video_doc = {
            '_id': str(uuid.uuid4()),
            'course_id': course_id,
            'matrix_id': resolved_matrix_id,
            'skill_name': skill_name,
            'title': title or 'Untitled Video',
            'link': link.strip(),
            'channel': channel or 'Unknown Channel',
            'thumbnail': thumbnail or '',
            'source': source,
            "prioritize": False,
            'status': 'published',
            'added_by': user['id'],
            'created_at': now,
            'updated_at': now,
        }

        await skill_videos_collection.insert_one(video_doc)
        return _serialize_video(video_doc)

    except Exception as e:
        logger.error(f"Add skill video error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}


async def update_skill_video(token: str, video_id: str, updates: dict) -> dict:
    """Instructor edits a video, or accepts an AI-suggested candidate by flipping its status."""
    try:
        _, error = await require_instructor(token)
        if error:
            return error

        allowed_fields = {'title', 'link', 'channel', 'thumbnail', 'status'}
        set_fields = {k: v for k, v in (updates or {}).items() if k in allowed_fields}

        if not set_fields:
            return {'error': 'No valid fields to update', 'statusCode': 400}

        set_fields['updated_at'] = _now()

        result = await skill_videos_collection.find_one_and_update(
            {'_id': video_id},
            {'$set': set_fields},
            return_document=True
        )

        if not result:
            return {'error': 'Video not found', 'statusCode': 404}

        return _serialize_video(result)

    except Exception as e:
        logger.error(f"Update skill video error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}


async def remove_skill_video(token: str, video_id: str) -> dict:
    """Instructor removes a video and its votes."""
    try:
        _, error = await require_instructor(token)
        if error:
            return error

        result = await skill_videos_collection.delete_one({'_id': video_id})
        if result.deleted_count == 0:
            return {'error': 'Video not found', 'statusCode': 404}

        await skill_video_votes_collection.delete_many({'video_id': video_id})

        return {'success': True, 'message': 'Video removed successfully'}

    except Exception as e:
        logger.error(f"Remove skill video error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}


async def verify_ai_video(token: str, video_id: str) -> dict:
    """Instructor marks an AI-suggested video as reviewed/approved — this is distinct
    from `source` (who added it) so it doesn't change source-gated behavior."""
    try:
        _, error = await require_instructor(token)
        if error:
            return error

        video = await skill_videos_collection.find_one({'_id': video_id})
        if not video:
            return {'error': 'Video not found', 'statusCode': 404}

        if video.get('source') != 'ai_suggested':
            return {
                'error': 'Only AI-suggested videos can be verified',
                'message': 'This video was already added by an instructor.',
                'statusCode': 400
            }

        result = await skill_videos_collection.find_one_and_update(
            {'_id': video_id},
            {'$set': {'instructor_verified': True, 'updated_at': _now()}},
            return_document=True
        )

        return _serialize_video(result)

    except Exception as e:
        logger.error(f"Verify AI video error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}


async def generate_ai_video_recommendations(token: str, course_id: str, skill_name: str,
                                            matrix_id: str = None, count: int = 6) -> dict:
    """Instructor triggers AI-generated video recommendations for a skill.

    These publish immediately alongside instructor-added videos — students see both,
    distinguished by `source` ('ai_suggested' vs 'manual') rather than gated behind
    a separate instructor-approval step.
    """
    try:
        user, error = await require_course_instructor(token, course_id)
        if error:
            return error

        resolved_matrix_id = await _resolve_matrix_id(course_id, matrix_id, skill_name)

        matrix = await achieveup_skill_matrices_collection.find_one({'_id': resolved_matrix_id})
        # course_name is kept current by the submission sync; the matrix name is only a
        # stand-in for the AI prompt on courses that haven't synced yet.
        course_name = (matrix.get('course_name') or matrix.get('matrix_name') or course_id) if matrix else course_id

        # 1. Course context: instructor-entered description, fall back to live Canvas syllabus
        course_context = ''
        description_doc = await achieveup_course_descriptions_collection.find_one({
            'course_id': str(course_id),
            'instructor_id': user['id']
        })
        if description_doc and description_doc.get('description'):
            course_context = description_doc['description']
        else:
            canvas_token = await get_user_canvas_token(user['id'])
            if canvas_token:
                from services.achieveup_canvas_service import get_course_detailed_info
                course_info = await get_course_detailed_info(canvas_token, course_id)
                if 'error' not in course_info:
                    course_context = course_info.get('public_description') or course_info.get('syllabus_body', '')

        # 2. Sample question text for this skill
        sample_questions = []
        async for qs_doc in achieveup_question_skills_collection.find({
            'course_id': course_id,
            'skills': skill_name
        }).limit(3):
            question = await quizzes_collection.find_one({'questionid': qs_doc.get('question_id')})
            if question and question.get('question_text'):
                sample_questions.append(question['question_text'])

        # 3. Generate search topics
        topics_result = await generate_skill_search_topics(skill_name, course_name, course_context, sample_questions)
        if not topics_result.get('success'):
            return {'error': 'Failed to generate search topics', 'message': topics_result.get('error'), 'statusCode': 502}

        # 4. Search YouTube for each topic
        existing_links = set()
        async for existing in skill_videos_collection.find(
            {'course_id': course_id, 'matrix_id': resolved_matrix_id, 'skill_name': skill_name},
            {'link': 1}
        ):
            existing_links.add(existing['link'])

        candidates = []

        # A. Get instructor-configured preferred channels for this course.
        # A plain database read, so a missing Canvas token or a Canvas outage
        # doesn't block generation.
        configured_channels = [
            c['channel_id'] for c in
            await get_saved_course_channels(course_id, user['id'])]

        # B. Priority Pass: Search using configured channel IDs first
        if configured_channels:
            logger.info(f"Prioritizing search across configured channels: {configured_channels}")
            # Calculate how many videos to request per channel
            per_channel_limit = max(1, count // len(configured_channels))

            channel_searches: int = 0
            for topic in topics_result['topics']:
                if len(candidates) >= count or channel_searches >= Config.MAX_CHANNEL_SEARCHES:
                    break
                for channel in configured_channels:
                    if len(candidates) >= count or channel_searches >= Config.MAX_CHANNEL_SEARCHES:
                        break

                    channel_searches += 1

                    # Pass the clean 'topic' and 'channel' separately to the YouTube API wrapper
                    channel_videos = await fetch_videos_for_topic_and_channel(
                        topic=topic,
                        channel_id=channel,
                        limit=per_channel_limit)

                    for video in channel_videos:
                        if video.get('link') and video['link'] not in existing_links:
                            video["prioritize"] = True
                            existing_links.add(video['link'])
                            candidates.append(video)
                        if len(candidates) >= count:
                            break

        # C. Fallback Pass: Standard global search if more candidate videos are still needed
        if len(candidates) < count:
            logger.info(f"Fallback to standard YouTube search. Current candidate count: {len(candidates)}/{count}")
            for topic in topics_result['topics']:
                if len(candidates) >= count:
                    break

                needed = count - len(candidates)
                global_videos = await fetch_videos_for_topic(topic=topic, limit=needed)

                for video in global_videos:
                    if video.get('link') and video['link'] not in existing_links:
                        existing_links.add(video['link'])
                        candidates.append(video)
                    if len(candidates) >= count:
                        break

        # 5. Insert as published — visible to students immediately, tagged ai_suggested
        now = _now()
        ai_video_docs = []
        for video in candidates:
            doc = {
                '_id': str(uuid.uuid4()),
                'course_id': course_id,
                'matrix_id': resolved_matrix_id,
                'skill_name': skill_name,
                'title': video['title'],
                'link': video['link'],
                'channel': video['channel'],
                'thumbnail': video['thumbnail'],
                'source': 'ai_suggested',
                "prioritize": video.get("prioritize", False),
                'status': 'published',
                'added_by': user['id'],
                'created_at': now,
                'updated_at': now,
            }
            ai_video_docs.append(doc)

        if ai_video_docs:
            await skill_videos_collection.insert_many(ai_video_docs)

        return {'videos': [_serialize_video(d) for d in ai_video_docs]}

    except Exception as e:
        logger.error(f"Generate AI video recommendations error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}


async def vote_skill_video(token: str, video_id: str, vote_type: str) -> dict:
    """Student rates whether a video was helpful for a skill."""
    try:
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result

        student_id = user_result['user']['id']

        valid_votes = {'upvote', 'downvote', 'remove'}
        if vote_type not in valid_votes:
            return {'error': 'Invalid vote type', 'statusCode': 400}

        video = await skill_videos_collection.find_one({'_id': video_id})
        if not video:
            return {'error': 'Video not found', 'statusCode': 404}

        filter_doc = {
            'student_id': student_id,
            'video_id': video_id,
        }

        if vote_type == 'remove':
            await skill_video_votes_collection.delete_one(filter_doc)
            return {'success': True, 'message': 'Vote removed successfully'}

        now = _now()
        update_doc = {
            '$set': {
                'vote_type': vote_type,
                'timestamp': now,
            },
            '$setOnInsert': {
                'student_id': student_id,
                'video_id': video_id,
                'course_id': video['course_id'],
                'matrix_id': video['matrix_id'],
                'skill_name': video['skill_name'],
            }
        }

        await skill_video_votes_collection.update_one(filter_doc, update_doc, upsert=True)
        return {'success': True, 'message': 'Vote recorded successfully'}

    except Exception as e:
        logger.error(f"Vote skill video error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}


async def get_video_vote_counts(course_id: str, matrix_id: str, skill_name: str,
                                 video_ids: list, student_id: str = None) -> dict:
    """Returns {video_id: {upvotes, downvotes, student_vote}} for the given video_ids."""
    if not video_ids:
        return {}

    counts = {vid: {'upvotes': 0, 'downvotes': 0, 'student_vote': None} for vid in video_ids}

    pipeline = [
        {'$match': {'video_id': {'$in': video_ids}}},
        {'$group': {
            '_id': {'video_id': '$video_id', 'vote_type': '$vote_type'},
            'count': {'$sum': 1}
        }}
    ]

    async for result in skill_video_votes_collection.aggregate(pipeline):
        vid = result['_id']['video_id']
        vote_type = result['_id']['vote_type']
        if vid not in counts:
            continue
        if vote_type == 'upvote':
            counts[vid]['upvotes'] = result['count']
        elif vote_type == 'downvote':
            counts[vid]['downvotes'] = result['count']

    if student_id:
        async for vote in skill_video_votes_collection.find({
            'video_id': {'$in': video_ids},
            'student_id': student_id
        }):
            if vote['video_id'] in counts:
                counts[vote['video_id']]['student_vote'] = vote['vote_type']

    return counts


_TIMESTAMP_BUCKET_SECONDS = 30


def _find_best_transcript_bucket(transcript: list, skill_name: str):
    """Scores ~30s transcript buckets by skill-keyword occurrence. Returns the best
    bucket's start second, or None if no bucket contains any keyword."""
    keywords = [w for w in re.split(r'[\s\-]+', skill_name.lower()) if w]
    if not keywords:
        return None

    buckets = {}
    for segment in transcript:
        bucket_start = int(segment.get('start', 0) // _TIMESTAMP_BUCKET_SECONDS) * _TIMESTAMP_BUCKET_SECONDS
        buckets.setdefault(bucket_start, []).append(segment.get('text', ''))

    best_start = None
    best_score = 0
    for bucket_start, texts in buckets.items():
        bucket_text = ' '.join(texts).lower()
        score = sum(bucket_text.count(keyword) for keyword in keywords)
        if score > best_score:
            best_score = score
            best_start = bucket_start

    return best_start


async def find_relevant_moment(token: str, video_id: str) -> dict:
    """Instructor opt-in: find the transcript moment most relevant to a
    video's skill, and store it as a deep-link timestamp."""
    try:
        user, error = await require_instructor(token)
        if error:
            return error

        video = await skill_videos_collection.find_one({'_id': video_id})
        if not video:
            return {'error': 'Video not found', 'statusCode': 404}

        error = await check_course_instructor(user, video['course_id'])
        if error:
            return error

        transcript_result = await fetch_video_transcript(video['link'])
        if not transcript_result.get('success'):
            return {
                'error': 'No transcript available',
                'message': transcript_result.get('error', 'This video has no captions to search.'),
                'statusCode': 422
            }

        best_start = _find_best_transcript_bucket(transcript_result['transcript'], video['skill_name'])
        if best_start is None:
            return {
                'error': 'No relevant moment found',
                'message': "Couldn't find a clearly relevant moment in this video's captions.",
                'statusCode': 422
            }

        result = await skill_videos_collection.find_one_and_update(
            {'_id': video_id},
            {'$set': {'timestamp_seconds': best_start, 'updated_at': _now()}},
            return_document=True
        )

        return _serialize_video(result)

    except Exception as e:
        logger.error(f"Find relevant moment error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}
