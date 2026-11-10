# services/canvas_submissions_service.py

"""
Canvas Quiz Submissions Service
================================

Fetches and processes student quiz submissions from Canvas API.
Provides real student performance data for badge generation and analytics.
"""

import asyncio
import logging
import aiohttp
from datetime import datetime, timezone
from pymongo import UpdateOne
from services.achieveup_canvas_service import (
    create_canvas_session, CANVAS_API_URL, is_new_quiz, get_instructor_course_quizzes, get_canvas_course_name
)
from services.skill_tiers import tier_for_score
from config import Config
import csv
import io

from mongodb import get_db
from utils import text_utils
from utils.course_utils import course_id_filter

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup
db = get_db()

submissions_collection = db.get_collection('AchieveUp_Quiz_Submissions')
achieveup_skill_matrices_collection = db[Config.ACHIEVEUP_SKILL_MATRICES_COLLECTION]

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


# Canvas answers worth trying again: rate limiting and brief server trouble.
# Anything else (401, 403, 404...) won't change on a retry, except Canvas's
# own rate limit, which comes back as a 403 (see is_rate_limited).
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
# Two retries (three tries) covers a brief Canvas hiccup without dragging out
# a sync when Canvas is really down: at most about 3s extra per request.
CANVAS_RETRIES = 2
RETRY_BASE_DELAY = 1  # seconds, doubled after each failed try


def is_rate_limited(status: int, body: str) -> bool:
    """Canvas answers a throttled request with 403 "Rate Limit Exceeded", not 429."""
    return status == 403 and 'Rate Limit Exceeded' in body


async def canvas_request(session, method: str, url: str, headers: dict, params: dict = None,
                         data: dict = None, ok_statuses=(200,), as_text: bool = False):
    """
    Send a Canvas request, retrying brief failures.

    Returns (status, body, headers): the parsed JSON (or text, with as_text)
    when the status is in ok_statuses, the response text otherwise. A
    connection error on the last try is raised.
    """
    send = getattr(session, method.lower())
    for attempt in range(CANVAS_RETRIES + 1):
        last_try = attempt == CANVAS_RETRIES
        try:
            async with send(url, headers=headers, params=params, data=data) as response:
                await check_rate_limit(response)
                if response.status in ok_statuses:
                    body = await response.text(encoding='utf-8') if as_text else await response.json()
                    return response.status, body, response.headers
                body = await response.text()
                retryable = response.status in RETRYABLE_STATUSES or is_rate_limited(response.status, body)
                if last_try or not retryable:
                    return response.status, body, response.headers
                logger.warning(f"Canvas returned {response.status} for {url}; retrying")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if last_try:
                raise
            logger.warning(f"Canvas request to {url} failed ({e}); retrying")
        await asyncio.sleep(RETRY_BASE_DELAY * 2 ** attempt)


async def canvas_get_json(session, url: str, headers: dict, params: dict = None):
    """GET a Canvas URL with canvas_request's retries."""
    return await canvas_request(session, 'GET', url, headers, params=params)


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
        new_quiz_url: str = f"{CANVAS_API_URL}/courses/{course_id}/assignments/{quiz_id}/submissions"

        all_submissions: list = []
        
        async with create_canvas_session() as session:
            is_canvas_new_quiz: bool | None = None

            match await is_new_quiz(canvas_token, course_id, quiz_id):
                case True:
                    is_canvas_new_quiz = True
                    cont: bool = True
                    params = {
                        'per_page': 100
                    }

                    # While loop to ensure response pages are also parsed.
                    while cont:
                        status, data, response_headers = await canvas_get_json(
                            session, new_quiz_url, headers, params)
                        if status != 200:
                            logger.error(f"Canvas submissions fetch error: {status} - {data}")
                            return {
                                'error': f'Failed to fetch submissions: {status}',
                                'statusCode': status
                            }

                        if "errors" in data:
                            logger.error(f"Canvas' REST API call returned an error: {data['errors']}")
                            return {
                                "error": "Canvas API call error.",
                                "message": "An error occured when attempting to communicate with Canvas' API.",
                                "statusCode": 400
                            }

                        # Mapping new quiz fields to the same fields classic quizzes returns.
                        all_submissions.extend([
                            {
                                'attempt': submission.get('attempt'),
                                'attempts_left': None,
                                'end_at': submission.get('cached_due_date'),
                                'excused?': submission.get('excused'),
                                'extra_attempts': submission.get('extra_attempts'),
                                'extra_time': None,
                                'finished_at': submission.get('submitted_at'),
                                'fudge_points': None,
                                'has_seen_results': None,
                                'html_url': submission.get('preview_url') or submission.get('url'),
                                'id': submission.get('id'),
                                'kept_score': submission.get('score') if submission.get('score') is not None else submission.get('entered_score'),
                                'manually_unlocked': None,
                                'overdue_and_needs_submission': submission.get('missing'),
                                'quiz_id': submission.get('assignment_id', quiz_id),
                                'quiz_points_possible': None,
                                'quiz_version': None,
                                'result_url': submission.get('preview_url'),
                                'score': submission.get('score'),
                                'score_before_regrade': None,
                                'started_at': None,
                                'submission_id': submission.get('id'),
                                'time_spent': None,
                                'user_id': submission.get('user_id'),
                                'validation_token': None,
                                'workflow_state': submission.get('workflow_state'),
                            }
                            for submission in data
                            if submission.get("attempt")
                        ])

                        # Check for next page
                        link_header = response_headers.get('Link', '')
                        if 'rel="next"' in link_header:
                            # Parse next URL from Link header
                            for link in link_header.split(','):
                                if 'rel="next"' in link:
                                    new_quiz_url = link.split(';')[0].strip('<> ')
                                    break
                        else:
                            cont = False
                        
                        params = {}

                case False:
                    is_canvas_new_quiz = False
                    params = {
                        'per_page': 100,
                        'include[]': ['submission', 'user']
                    }

                    cont: bool = True
                    while cont:
                        status, data, response_headers = await canvas_get_json(session, url, headers, params)
                        if status != 200:
                            logger.error(f"Canvas submissions fetch error: {status} - {data}")
                            return {
                                'error': f'Failed to fetch submissions: {status}',
                                'statusCode': status
                            }

                        submissions = data.get('quiz_submissions', [])
                        all_submissions.extend(submissions)

                        # Check for next page
                        link_header = response_headers.get('Link', '')
                        if 'rel="next"' in link_header:
                            # Parse next URL from Link header
                            for link in link_header.split(','):
                                if 'rel="next"' in link:
                                    url = link.split(';')[0].strip('<> ')
                                    break
                        else:
                            cont = False
                        
                        params = {}  # Clear params for subsequent requests (URL has them)


                case None:
                    logger.error(f"Failed to determine quiz type: {course_id}, quiz_id: {quiz_id}")
                    return {'error': f'Failed to determine instructor quiz type.', 'statusCode': 404}
        
        return {
            'submissions': all_submissions,
            'count': len(all_submissions),
            "is_new_quiz": is_canvas_new_quiz
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
            'student_name': submission.get('user', {}).get('name') or submission.get('user', {}).get('display_name'),
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
            answer_texts = [a.get('text') or '' for a in question.get('answers', [])]
            question_key = text_utils.build_question_key(
                question.get('question_text', ''), answer_texts, fallback_id=question.get('id')
            )

            question_data = {
                'question_id': text_utils.hash_text(question_key),
                'canvas_question_id': str(question.get('id')),
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
        submission_data['cached_at'] = datetime.now(timezone.utc).replace(tzinfo=None)
        
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


# Quizzes synced at the same time, and Canvas requests for submission answers
# in flight at once across all of them. The request limit is what the sync
# used per quiz before quizzes ran in parallel, so Canvas sees the same load.
QUIZ_CONCURRENCY = 4
SUBMISSION_REQUEST_CONCURRENCY = 10


async def sync_course_submissions_direct(canvas_token: str, course_id: str, course_name: str = None,
                                         on_progress=None) -> dict:
    """
    Sync all submissions for a course using a raw Canvas token.
    Intended for background tasks (app.py) or internal calls.

    course_name: the Canvas course name if the caller already has it; fetched otherwise.
    on_progress: optional async callback(quizzes_done, quizzes_total), called
        once before the first quiz and as each quiz finishes.
    """
    try:
        # Keep every matrix for this course on the current Canvas name (overwrites, so
        # renames in Canvas propagate), and hand it to badges awarded during this sync.
        if not course_name:
            course_name = await get_canvas_course_name(canvas_token, course_id)
        if course_name:
            try:
                await achieveup_skill_matrices_collection.update_many(
                    {**course_id_filter(course_id), 'course_name': {'$ne': course_name}},
                    {'$set': {'course_name': course_name}}
                )
            except Exception as e:
                logger.error(f"Error saving course name to matrices for course {course_id}: {str(e)}")

        # Get all quizzes in the course
        from services.mastery_service import CourseMasteryTally, replace_course_mastery, mastery_collection
        quizzes_result = await get_instructor_course_quizzes(canvas_token, course_id)
        
        if 'error' in quizzes_result:
            return quizzes_result
        
        quizzes = quizzes_result if isinstance(quizzes_result, list) else []
        
        if not quizzes:
            logger.info(f"No quizzes found for course {course_id}")
            return {
                'message': 'No quizzes found (Direct)',
                'course_id': course_id,
                'total_quizzes': 0,
                'total_synced': 0,
                'total_errors': 0,
                'progress_synced': 0,
                'synced_at': datetime.now(timezone.utc).replace(tzinfo=None)
            }

        total_synced = 0
        total_errors = 0
        # Submissions whose answers couldn't be read. Any of these, or any
        # quiz error, means the tally is missing scores and must not be used.
        failed_submissions = 0
        # New scores are built here and swapped in after the last quiz, so
        # the live data is never half-rebuilt.
        tally = CourseMasteryTally()

        quizzes_done = 0

        async def report_quiz_progress():
            if on_progress:
                await on_progress(quizzes_done, len(quizzes))

        await report_quiz_progress()

        # Canvas requests for answers, shared by every quiz in flight so the
        # load on Canvas stays the same however many quizzes run at once.
        request_slots = asyncio.Semaphore(SUBMISSION_REQUEST_CONCURRENCY)
        quiz_slots = asyncio.Semaphore(QUIZ_CONCURRENCY)

        async with create_canvas_session() as session:

            async def fetch_and_process_submission(sub):
                nonlocal total_synced, failed_submissions
                student_id = sub.get('user_id', 'unknown')

                # Fetch detailed submission data with questions if missing
                if 'questions' not in sub:
                    submission_id = sub.get('id')
                    if submission_id:
                        questions_url = f"{CANVAS_API_URL}/quiz_submissions/{submission_id}/questions"
                        headers = {'Authorization': f'Bearer {canvas_token}'}
                        try:
                            async with request_slots:
                                status, questions_data, _ = await canvas_get_json(session, questions_url, headers)
                            if status == 200:
                                sub['questions'] = questions_data.get('quiz_submission_questions', [])
                            else:
                                failed_submissions += 1
                                logger.warning(f"Could not fetch questions for submission {submission_id} (student {student_id}): status {status}")
                                return
                        except Exception as e:
                            failed_submissions += 1
                            logger.error(f"Error fetching questions for submission {submission_id}: {str(e)}")
                            return

                processed = await process_submission_data(sub)
                if not processed:
                    failed_submissions += 1
                    return
                processed['course_id'] = str(course_id)
                processed['course_name'] = course_name
                # Add to the new mastery totals
                await tally.add_submission(processed)
                # Store raw submission
                success = await store_submission_data(course_id, processed)
                if success:
                    total_synced += 1

            async def sync_quiz(quiz):
                nonlocal total_errors
                quiz_id = quiz.get('id')
                quiz_title = quiz.get('title', 'Unknown')

                # Get all submissions for this quiz
                submissions_result = await get_all_course_submissions(canvas_token, course_id, quiz_id)

                if 'error' in submissions_result:
                    total_errors += 1
                    logger.error(f"Failed to sync quiz {quiz_id} ({quiz_title}): {submissions_result.get('error')}")
                    return

                submissions = submissions_result.get('submissions', [])

                # Check if quiz is a new quiz. If it is, get the new quizzes data.
                if submissions_result.get("is_new_quiz") and submissions:
                    new_quiz_data = await get_new_quiz_data(canvas_token, course_id, quiz_id)

                    # Check for errors.
                    if "error" in new_quiz_data:
                        total_errors += 1
                        logger.error(f"Failed to get New Quiz results for quiz {quiz_id} ({quiz_title}): {new_quiz_data['error']}")
                        return

                    new_quiz_submission_results = new_quiz_data.get("results")
                    for submission in submissions:
                        submission["questions"] = new_quiz_submission_results.get(str(submission.get("user_id")), [])

                await asyncio.gather(*(fetch_and_process_submission(s) for s in submissions))

            async def sync_quiz_in_slot(quiz):
                nonlocal quizzes_done
                nonlocal total_errors
                async with quiz_slots:
                    try:
                        await sync_quiz(quiz)
                    except Exception as e:
                        # One quiz failing shouldn't abandon the others mid-flight.
                        total_errors += 1
                        logger.error(f"Error syncing quiz {quiz.get('id')}: {str(e)}", exc_info=True)
                    finally:
                        quizzes_done += 1
                        await report_quiz_progress()

            # Several quizzes at once: most of each quiz's time is waiting on
            # Canvas (New Quiz reports especially), which overlaps well.
            await asyncio.gather(*(sync_quiz_in_slot(q) for q in quizzes))

        # Swap the new totals in only if every quiz and submission was read.
        # A partial tally would replace each student's totals with fewer
        # quizzes' worth and delete rows for skills only the missing quizzes
        # cover, so on any Canvas failure keep the previous sync's data.
        if total_errors or failed_submissions:
            logger.warning(f"Sync of course {course_id} incomplete ({total_errors} quiz errors, "
                           f"{failed_submissions} unreadable submissions); keeping previous mastery data")
            return {
                'error': 'Sync incomplete',
                'message': 'Some quiz results could not be read from Canvas, so scores were left '
                           'as they were. Please try again.',
                'statusCode': 502,
                'course_id': course_id,
                'total_quizzes': len(quizzes),
                'total_errors': total_errors,
                'failed_submissions': failed_submissions,
            }

        await replace_course_mastery(course_id, course_name, tally)

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

                level = tier_for_score(percentage)

                student_mastery[sid][skill_id] = {
                    'score': round(percentage, 1),
                    'level': level,
                    'total_questions': total_attempted,
                    'correct_answers': total_correct,
                    'notes': ''
                }

            # Upsert one Progress document per student (overwrites, no bloat),
            # all in one bulk write so every student flips to the new data together.
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            operations = [
                UpdateOne(
                    {'student_id': sid, 'course_id': str(course_id)},
                    {'$set': {
                        'student_id': sid,
                        'course_id': str(course_id),
                        'skill_progress': skill_progress,
                        'last_updated': now
                    }},
                    upsert=True
                )
                for sid, skill_progress in student_mastery.items()
            ]
            if operations:
                await progress_collection.bulk_write(operations, ordered=False)
            progress_synced = len(operations)

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
            'synced_at': datetime.now(timezone.utc).replace(tzinfo=None)
        }
        
    except Exception as e:
        logger.error(f"Sync course submissions direct error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_new_quiz_data(canvas_token: str, course_id: str, quiz_id: str) -> dict:
    "Get equivalent data of classic quiz for a new quiz."

    try:
        headers: dict = {"Authorization": f"Bearer {canvas_token}"}

        url: str = f"{getattr(Config, 'CANVAS_NEW_QUIZ_API_URL')}/courses/{course_id}/quizzes/{quiz_id}"

        # Get quiz questions for a new quiz.
        async with create_canvas_session() as session:
            status, quiz_data, _ = await canvas_get_json(session, f"{url}/items", headers, {"per_page": 100})
            if status != 200:
                return {"error": f"Failed to get new quiz items: {status}", "statusCode": status}

            items: list = [item for item in quiz_data if item.get("entry_type") != "Stimulus"]

            # Sort question items to align with report questions later.
            items_by_position: dict = {item.get("position"): item for item in items}
            items = [items_by_position[position] for position in sorted(items_by_position)]

            # Request body to get new quiz report.
            canvas_quiz_report_request: dict = {
                "quiz_report[report_type]": "student_analysis",
                "quiz_report[format]": "csv"
            }


            status, progress, _ = await canvas_request(
                session, 'POST', f"{url}/reports", headers,
                data=canvas_quiz_report_request, ok_statuses=(200, 201))
            if status not in (200, 201):
                return {"error": f"Failed to request new quiz report: {status}", "statusCode": status}

            report_progress: dict = progress.get("progress", {})

            # Repeatedly check report status.
            for i in range(120):

                # Check if report is still generating.
                if report_progress.get("workflow_state") not in ["completed", "failed"]:
                    await asyncio.sleep(3)
                    status, progress_data, _ = await canvas_get_json(session, report_progress.get("url"), headers)
                    # A failed check keeps the last known state and tries again next time.
                    if status == 200:
                        report_progress = progress_data

            report_file_url: str = (report_progress.get("results") or {}).get("url", "")

            if report_progress.get("workflow_state", "") != "completed" or not report_file_url:
                return {"error": "New quiz report did not finish.", "statusCode": 502}

            # Download new quiz report.
            status, report_data, _ = await canvas_request(session, 'GET', report_file_url, headers, as_text=True)
            report_data = report_data.lstrip("\ufeff")

            if status != 200 or report_data.startswith('{"errors"'):
                logger.error(f"Failed to download new quiz report for quiz {quiz_id}: {report_data[:300]}")
                return {"error": "Failed to download new quiz report.", "statusCode": 502}

        # Use CSV to read the report.
        report_file = io.StringIO(report_data)
        file_rows: list = list(csv.reader(report_file))

        report_headers: list = file_rows[0]

        question_columns: list = [i for i, name in enumerate(report_headers) if name == "ItemID"]

        if len(question_columns) != len(items):
            return {"error": "New quiz report does not match the quiz's questions.", "statusCode": 502}

        question_results: dict = {}
        latest_attempts: dict = {}

        # Parse every question row in the CSV.
        for row in file_rows[1:]:
            student_id: str = row[report_headers.index("ID")]
            attempt: int = int(row[report_headers.index("Attempt")] or 0)

            # Check if the attempt is the latest attempt.
            if attempt < latest_attempts.get(student_id, 0):
                continue

            latest_attempts[student_id] = attempt

            questions: list = []

            # Parse all question columns.
            for item, column in zip(items, question_columns):
                earned_points: float = float(row[column + 3] or 0)
                points_possible: float = float(item.get("points_possible") or 0)
                status: str = row[column + 4]

                # Skip answers that are still waiting on manual grading.
                if status != "Graded":
                    continue

                questions.append({
                    "id": str(item.get("id")),
                    "question_text": (item.get("entry") or {}).get("item_body"),
                    "correct": points_possible > 0 and earned_points >= points_possible,
                })

            question_results[student_id] = questions

        return {"results": question_results}

    except Exception as error:
        logger.error(f"Error trying to retrieve new quiz data: {str(error)}")
        return {"error": "Internal server error.", "statusCode": 500}