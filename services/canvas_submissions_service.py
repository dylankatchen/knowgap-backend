# services/canvas_submissions_service.py

"""
Canvas Quiz Submissions Service
================================

Fetches and processes student quiz submissions from Canvas API.
Provides real student performance data for badge generation and analytics.
"""

import aiohttp
import asyncio
import ssl
import logging
from datetime import datetime
from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from services.achieveup_auth_service import achieveup_verify_token, get_user_canvas_token
from services.achieveup_canvas_service import create_canvas_session, CANVAS_API_URL
from config import Config

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup
client = AsyncIOMotorClient(
    Config.DB_CONNECTION_STRING,
    tlsAllowInvalidCertificates=(Config.ENV == 'development')
)
db = client[Config.DATABASE]
submissions_collection = db.get_collection('AchieveUp_Quiz_Submissions')

async def check_rate_limit(response):
    """
    Check Canvas rate limit headers and pause if running low.
    Canvas returns X-Rate-Limit-Remaining to indicate budget left.
    """
    remaining = response.headers.get('X-Rate-Limit-Remaining')
    if remaining is not None:
        try:
            remaining_val = float(remaining)
            if remaining_val < 50:
                wait_time = max(5, int(60 - remaining_val))
                logger.warning(f"Canvas rate limit low ({remaining_val} remaining). Pausing {wait_time}s...")
                await asyncio.sleep(wait_time)
            elif remaining_val < 100:
                # Light throttle when getting close
                await asyncio.sleep(1)
        except (ValueError, TypeError):
            pass

async def get_student_quiz_submission(canvas_token: str, course_id: str, quiz_id: str, student_id: str) -> dict:
    """
    Fetch a specific student's quiz submission from Canvas API.
    
    Args:
        canvas_token: Canvas API token
        course_id: Canvas course ID
        quiz_id: Canvas quiz ID
        student_id: Canvas student/user ID
        
    Returns:
        dict: Submission data with questions and scores
    """
    try:
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }
        
        # Get quiz submission
        url = f"{CANVAS_API_URL}/courses/{course_id}/quizzes/{quiz_id}/submissions"
        params = {
            'user_id': student_id,
            'include[]': ['submission', 'quiz', 'user']
        }
        
        async with create_canvas_session() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Canvas submission fetch error: {response.status} - {error_text}")
                    return {
                        'error': f'Failed to fetch submission: {response.status}',
                        'statusCode': response.status
                    }
                
                data = await response.json()
                
                # Canvas returns submissions in 'quiz_submissions' array
                submissions = data.get('quiz_submissions', [])
                if not submissions:
                    return {
                        'error': 'No submission found',
                        'message': 'Student has not submitted this quiz',
                        'statusCode': 404
                    }
                
                # Get the most recent submission
                submission = submissions[0]
                
                # Fetch detailed submission data with questions
                submission_id = submission.get('id')
                questions_url = f"{CANVAS_API_URL}/quiz_submissions/{submission_id}/questions"
                
                async with session.get(questions_url, headers=headers) as q_response:
                    if q_response.status == 200:
                        questions_data = await q_response.json()
                        submission['questions'] = questions_data.get('quiz_submission_questions', [])
                    else:
                        logger.warning(f"Could not fetch submission questions: {q_response.status}")
                        submission['questions'] = []
                
                return submission
                
    except aiohttp.ClientError as e:
        logger.error(f"Canvas API connection error: {str(e)}")
        return {
            'error': 'Canvas API connection failed',
            'message': str(e),
            'statusCode': 500
        }
    except Exception as e:
        logger.error(f"Get student quiz submission error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_all_course_submissions(canvas_token: str, course_id: str, quiz_id: str) -> dict:
    """
    Fetch all student submissions for a quiz in a course.
    
    Args:
        canvas_token: Canvas API token
        course_id: Canvas course ID
        quiz_id: Canvas quiz ID
        
    Returns:
        dict: List of all submissions
    """
    try:
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{CANVAS_API_URL}/courses/{course_id}/quizzes/{quiz_id}/submissions"
        params = {
            'per_page': 100,
            'include[]': ['submission', 'user']
        }
        
        all_submissions = []
        
        async with create_canvas_session() as session:
            # Handle pagination
            while url:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Canvas submissions fetch error: {response.status} - {error_text}")
                        return {
                            'error': f'Failed to fetch submissions: {response.status}',
                            'statusCode': response.status
                        }
                    
                    data = await response.json()
                    submissions = data.get('quiz_submissions', [])
                    all_submissions.extend(submissions)
                    
                    # Check rate limit headers before continuing
                    await check_rate_limit(response)
                    
                    # Check for next page
                    link_header = response.headers.get('Link', '')
                    url = None
                    if 'rel="next"' in link_header:
                        # Parse next URL from Link header
                        for link in link_header.split(','):
                            if 'rel="next"' in link:
                                url = link.split(';')[0].strip('<> ')
                                break
                    
                    params = {}  # Clear params for subsequent requests (URL has them)
        
        return {
            'submissions': all_submissions,
            'count': len(all_submissions)
        }
        
    except Exception as e:
        logger.error(f"Get all course submissions error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def process_submission_data(submission: dict) -> dict:
    """
    Process Canvas submission data into standardized format.
    
    Args:
        submission: Raw Canvas submission data
        
    Returns:
        dict: Processed submission with question scores
    """
    try:
        processed = {
            'submission_id': str(submission.get('id')),
            'student_id': str(submission.get('user_id')),
            'quiz_id': str(submission.get('quiz_id')),
            'attempt': submission.get('attempt', 1),
            'score': submission.get('score', 0),
            'kept_score': submission.get('kept_score', 0),
            'score_before_regrade': submission.get('score_before_regrade'),
            'points_possible': submission.get('quiz_points_possible', 0),
            'submitted_at': submission.get('submitted_at'),
            'started_at': submission.get('started_at'),
            'finished_at': submission.get('finished_at'),
            'workflow_state': submission.get('workflow_state'),
            'questions': []
        }
        
        # Process individual questions
        for question in submission.get('questions', []):
            question_data = {
                'question_id': str(question.get('id')),
                'question_type': question.get('question_type'),
                'points': question.get('points', 0),
                'points_possible': question.get('points_possible', 0),
                'correct': question.get('correct', False),
                'answer': question.get('answer'),
                'correct_answer': question.get('correct_answer')
            }
            processed['questions'].append(question_data)
        
        return processed
        
    except Exception as e:
        logger.error(f"Process submission data error: {str(e)}")
        return {}

async def store_submission_data(course_id: str, submission_data: dict, force_cache: bool = False) -> bool:
    """
    Store processed submission data in MongoDB for caching.
    
    Args:
        course_id: Canvas course ID
        submission_data: Processed submission data
        force_cache: If True, always cache. If False, only cache if ENABLE_SUBMISSION_CACHE is True
        
    Returns:
        bool: Success status
    """
    try:
        # Check if caching is enabled (default: False to minimize storage)
        enable_cache = getattr(Config, 'ENABLE_SUBMISSION_CACHE', False)
        
        if not enable_cache and not force_cache:
            logger.debug("Submission caching disabled, skipping storage")
            return False
        
        submission_data['course_id'] = course_id
        submission_data['cached_at'] = datetime.utcnow()
        
        # Upsert submission (update if exists, insert if new)
        await submissions_collection.update_one(
            {
                'submission_id': submission_data['submission_id'],
                'student_id': submission_data['student_id'],
                'quiz_id': submission_data['quiz_id']
            },
            {'$set': submission_data},
            upsert=True
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Store submission data error: {str(e)}")
        return False

async def get_cached_submission(student_id: str, course_id: str, quiz_id: str) -> Optional[dict]:
    """
    Retrieve cached submission from MongoDB.
    Only used if caching is enabled.
    
    Args:
        student_id: Canvas student ID
        course_id: Canvas course ID
        quiz_id: Canvas quiz ID
        
    Returns:
        dict or None: Cached submission if exists and fresh
    """
    try:
        # Check if caching is enabled
        enable_cache = getattr(Config, 'ENABLE_SUBMISSION_CACHE', False)
        if not enable_cache:
            return None
        
        submission = await submissions_collection.find_one({
            'student_id': student_id,
            'course_id': course_id,
            'quiz_id': quiz_id
        })
        
        if submission:
            # Check cache freshness (default: 1 hour)
            cache_ttl = int(getattr(Config, 'SUBMISSION_CACHE_TTL', 3600))
            cache_age = (datetime.utcnow() - submission.get('cached_at', datetime.min)).total_seconds()
            
            if cache_age < cache_ttl:
                submission.pop('_id', None)
                return submission
        
        return None
        
    except Exception as e:
        logger.error(f"Get cached submission error: {str(e)}")
        return None

async def get_student_submissions_for_course(token: str, student_id: str, course_id: str, use_cache: bool = False) -> dict:
    """
    Get all quiz submissions for a student in a course.
    By default, fetches directly from Canvas API to minimize storage.
    
    Args:
        token: AchieveUp auth token
        student_id: Canvas student ID
        course_id: Canvas course ID
        use_cache: If True, attempt to use cached data first
        
    Returns:
        dict: All submissions for the student in the course
    """
    try:
        # Verify token and get Canvas token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result['user']['id']
        canvas_token = await get_user_canvas_token(user_id)
        
        if not canvas_token:
            return {
                'error': 'Canvas token not found',
                'message': 'Please connect your Canvas account',
                'statusCode': 400
            }
        
        # Get all quizzes in the course
        from services.achieveup_canvas_service import get_instructor_course_quizzes
        quizzes_result = await get_instructor_course_quizzes(canvas_token, course_id)
        
        if 'error' in quizzes_result:
            return quizzes_result
        
        quizzes = quizzes_result if isinstance(quizzes_result, list) else []
        
        # Fetch submissions for each quiz
        all_submissions = []
        for quiz in quizzes:
            quiz_id = quiz.get('id')
            
            # Try cache first only if explicitly requested
            if use_cache:
                cached = await get_cached_submission(student_id, course_id, quiz_id)
                if cached:
                    all_submissions.append(cached)
                    continue
            
            # Fetch directly from Canvas (no caching by default)
            submission = await get_student_quiz_submission(canvas_token, course_id, quiz_id, student_id)
            
            if 'error' not in submission:
                # Process submission
                processed = await process_submission_data(submission)
                if processed:
                    all_submissions.append(processed)
                    # Only cache if explicitly enabled
                    if use_cache:
                        await store_submission_data(course_id, processed)
        
        return {
            'student_id': student_id,
            'course_id': course_id,
            'submissions': all_submissions,
            'total_submissions': len(all_submissions)
        }
        
    except Exception as e:
        logger.error(f"Get student submissions for course error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def sync_course_submissions(token: str, course_id: str) -> dict:
    """
    Sync all submissions for a course from Canvas to local cache.
    Useful for batch updates and analytics.
    
    Args:
        token: AchieveUp auth token
        course_id: Canvas course ID
        
    Returns:
        dict: Sync status and statistics
    """
    try:
        # Verify token and get Canvas token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result['user']['id']
        canvas_token = await get_user_canvas_token(user_id)
        
        if not canvas_token:
            return {
                'error': 'Canvas token not found',
                'message': 'Please connect your Canvas account',
                'statusCode': 400
            }
        
        return await sync_course_submissions_direct(canvas_token, course_id)
        
    except Exception as e:
        logger.error(f"Sync course submissions error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def sync_course_submissions_direct(canvas_token: str, course_id: str) -> dict:
    """
    Sync all submissions for a course using a raw Canvas token.
    Intended for background tasks (app.py) or internal calls.
    """
    try:
        # Get all quizzes in the course
        from services.achieveup_canvas_service import get_instructor_course_quizzes
        quizzes_result = await get_instructor_course_quizzes(canvas_token, course_id)
        
        if 'error' in quizzes_result:
            return quizzes_result
        
        quizzes = quizzes_result if isinstance(quizzes_result, list) else []
        
        total_synced = 0
        total_errors = 0
        
        async with create_canvas_session() as session:
            # Sync submissions for each quiz
            for quiz in quizzes:
                quiz_id = quiz.get('id')
                quiz_title = quiz.get('title', 'Unknown')
                
                # Get all submissions for this quiz
                submissions_result = await get_all_course_submissions(canvas_token, course_id, quiz_id)
                
                if 'error' in submissions_result:
                    total_errors += 1
                    logger.error(f"Failed to sync quiz {quiz_id} ({quiz_title}): {submissions_result.get('error')}")
                    continue
                
                submissions = submissions_result.get('submissions', [])
                
                # Process and store each submission
                from services.mastery_service import update_student_mastery, mastery_collection
                
                # Clear previous mastery data for this course to prevent $inc duplication 
                # upon every sync interval (since we aggregate across all time)
                if quiz == quizzes[0]: # Only do this once per course sync
                    await mastery_collection.delete_many({'course_id': str(course_id)})
                
                # Internal helper for parallel question fetching
                semaphore = asyncio.Semaphore(10) # Limit concurrency to 10 requests

                async def fetch_and_process_submission(sub):
                    nonlocal total_synced
                    async with semaphore:
                        student_id = sub.get('user_id', 'unknown')
                        
                        # Fetch detailed submission data with questions if missing
                        if 'questions' not in sub:
                            submission_id = sub.get('id')
                            if submission_id:
                                questions_url = f"{CANVAS_API_URL}/quiz_submissions/{submission_id}/questions"
                                headers = {'Authorization': f'Bearer {canvas_token}'}
                                try:
                                    async with session.get(questions_url, headers=headers) as q_response:
                                        await check_rate_limit(q_response)
                                        if q_response.status == 200:
                                            questions_data = await q_response.json()
                                            sub['questions'] = questions_data.get('quiz_submission_questions', [])
                                        else:
                                            logger.warning(f"Could not fetch questions for submission {submission_id} (student {student_id}): status {q_response.status}")
                                except Exception as e:
                                    logger.error(f"Error fetching questions for submission {submission_id}: {str(e)}")
                        
                        processed = await process_submission_data(sub)
                        if processed:
                            processed['course_id'] = str(course_id)
                            # Update mastery tracking
                            await update_student_mastery(processed)
                            # Store raw submission
                            success = await store_submission_data(course_id, processed)
                            if success:
                                total_synced += 1

                # Execute all submissions for this quiz in parallel
                await asyncio.gather(*(fetch_and_process_submission(s) for s in submissions))
        
        # Check how many mastery docs exist after sync
        mastery_count = await mastery_collection.count_documents({'course_id': str(course_id)})
        
        # === Sync Progress collection from freshly-updated Mastery data ===
        # This ensures student charts/graphs reflect the latest skill assignments.
        # No extra Canvas API calls — we just read what mastery_service already wrote.
        progress_synced = 0
        try:
            progress_collection = db.get_collection('AchieveUp_Progress')

            # Read all mastery docs for this course (just written above)
            mastery_docs = await mastery_collection.find(
                {'course_id': str(course_id)}
            ).to_list(length=None)

            # Group by student_id
            student_mastery = {}
            for doc in mastery_docs:
                sid = doc.get('student_id')
                if not sid:
                    continue
                if sid not in student_mastery:
                    student_mastery[sid] = {}

                skill_id = doc.get('skill_id', 'Unknown')
                total_correct = doc.get('total_correct', 0)
                total_attempted = doc.get('total_attempted', 0)
                percentage = doc.get('mastery_percentage', 0)

                if percentage >= 80:
                    level = 'advanced'
                elif percentage >= 60:
                    level = 'intermediate'
                else:
                    level = 'beginner'

                student_mastery[sid][skill_id] = {
                    'score': round(percentage, 1),
                    'level': level,
                    'total_questions': total_attempted,
                    'correct_answers': total_correct,
                    'notes': ''
                }

            # Upsert one Progress document per student (overwrites, no bloat)
            for sid, skill_progress in student_mastery.items():
                await progress_collection.update_one(
                    {'student_id': sid, 'course_id': str(course_id)},
                    {'$set': {
                        'student_id': sid,
                        'course_id': str(course_id),
                        'skill_progress': skill_progress,
                        'last_updated': datetime.utcnow()
                    }},
                    upsert=True
                )
                progress_synced += 1

            logger.info(f"Progress collection updated for {progress_synced} students in course {course_id}")
        except Exception as progress_error:
            logger.error(f"Error updating Progress collection: {str(progress_error)}")

        return {
            'message': 'Sync completed (Direct)',
            'course_id': course_id,
            'total_quizzes': len(quizzes),
            'total_synced': total_synced,
            'total_errors': total_errors,
            'progress_synced': progress_synced,
            'synced_at': datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Sync course submissions direct error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

