# services/canvas_submissions_service.py

"""
Canvas Quiz Submissions Service
================================

Fetches and processes student quiz submissions from Canvas API.
Provides real student performance data for badge generation and analytics.
"""

import aiohttp
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
        
        # Get all quizzes in the course
        from services.achieveup_canvas_service import get_instructor_course_quizzes
        quizzes_result = await get_instructor_course_quizzes(canvas_token, course_id)
        
        if 'error' in quizzes_result:
            return quizzes_result
        
        quizzes = quizzes_result if isinstance(quizzes_result, list) else []
        
        total_synced = 0
        total_errors = 0
        
        # Sync submissions for each quiz
        for quiz in quizzes:
            quiz_id = quiz.get('id')
            
            # Get all submissions for this quiz
            submissions_result = await get_all_course_submissions(canvas_token, course_id, quiz_id)
            
            if 'error' in submissions_result:
                total_errors += 1
                logger.error(f"Failed to sync quiz {quiz_id}: {submissions_result.get('error')}")
                continue
            
            submissions = submissions_result.get('submissions', [])
            
            # Process and store each submission
            for submission in submissions:
                processed = await process_submission_data(submission)
                if processed:
                    success = await store_submission_data(course_id, processed)
                    if success:
                        total_synced += 1
                    else:
                        total_errors += 1
        
        return {
            'message': 'Sync completed',
            'course_id': course_id,
            'total_quizzes': len(quizzes),
            'total_synced': total_synced,
            'total_errors': total_errors,
            'synced_at': datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Sync course submissions error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}
