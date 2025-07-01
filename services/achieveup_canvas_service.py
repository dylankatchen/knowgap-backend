# services/achieveup_canvas_service.py

import aiohttp
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from services.achieveup_auth_service import achieveup_verify_token, get_user_canvas_token
from config import Config

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup for AchieveUp Canvas data (separate from KnowGap)
client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
db = client[Config.DATABASE]
achieveup_canvas_courses_collection = db["AchieveUp_Canvas_Courses"]
achieveup_canvas_quizzes_collection = db["AchieveUp_Canvas_Quizzes"]
achieveup_canvas_questions_collection = db["AchieveUp_Canvas_Questions"]

# Canvas API configuration
CANVAS_API_URL = getattr(Config, 'CANVAS_API_URL', 'https://webcourses.ucf.edu/api/v1')

async def validate_canvas_token(canvas_token: str, canvas_token_type: str = 'student') -> dict:
    """Validate Canvas API token by testing it with Canvas API. Supports student and instructor tokens."""
    try:
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }
        
        # Test token by calling Canvas API /users/self endpoint
        url = f"{CANVAS_API_URL}/users/self"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    if response.status == 401:
                        return {
                            'valid': False,
                            'message': 'Invalid Canvas API token. Please check your token and try again.'
                        }
                    error_text = await response.text()
                    logger.error(f"Canvas API validation error: {response.status} - {error_text}")
                    return {
                        'valid': False,
                        'message': f'Canvas API returned error {response.status}. Please try again later.'
                    }
                user_data = await response.json()
        # If instructor, check /courses endpoint for instructor permissions
        permissions = {}
        if canvas_token_type == 'instructor':
            courses_url = f"{CANVAS_API_URL}/courses"
            async with aiohttp.ClientSession() as session:
                async with session.get(courses_url, headers=headers) as courses_response:
                    if courses_response.status != 200:
                        return {
                            'valid': False,
                            'message': 'Token does not have instructor permissions. Please provide an instructor token.'
                        }
                    courses_data = await courses_response.json()
                    # Check if any course has "enrollment_type" as "teacher" or "instructor"
                    is_instructor = any(
                        any(enr.get('type') in ['TeacherEnrollment', 'instructor'] for enr in course.get('enrollments', []))
                        for course in courses_data if 'enrollments' in course
                    )
                    if not is_instructor:
                        return {
                            'valid': False,
                            'message': 'Token is valid but does not have instructor access to any courses.'
                        }
                    permissions['instructor'] = True
        return {
            'valid': True,
            'message': 'Token is valid',
            'user_info': {
                'id': user_data.get('id'),
                'name': user_data.get('name'),
                'email': user_data.get('email')
            },
            'permissions': permissions
        }
    except aiohttp.ClientError as e:
        logger.error(f"Canvas API connection error: {str(e)}")
        return {
            'valid': False,
            'message': 'Unable to connect to Canvas API. Please check your internet connection and try again.'
        }
    except Exception as e:
        logger.error(f"Canvas token validation error: {str(e)}")
        return {
            'valid': False,
            'message': 'An unexpected error occurred while validating the token.'
        }

async def get_canvas_courses(token: str) -> dict:
    """Get user's Canvas courses for AchieveUp using stored Canvas API token."""
    try:
        # Verify user token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result['user']['id']
        
        # Get user's stored Canvas API token
        canvas_token = await get_user_canvas_token(user_id)
        if not canvas_token:
            return {
                'error': 'Canvas API token not found',
                'message': 'Please update your Canvas API token in your profile',
                'statusCode': 400
            }
        
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{CANVAS_API_URL}/courses"
        params = {
            'enrollment_state': 'active',
            'per_page': 100
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    courses_data = await response.json()
                    
                    # Transform to AchieveUp format
                    courses = []
                    for course in courses_data:
                        course_info = {
                            'id': str(course.get('id')),
                            'name': course.get('name', ''),
                            'code': course.get('course_code', '')
                        }
                        courses.append(course_info)
                    
                    return courses
                else:
                    error_text = await response.text()
                    logger.error(f"Canvas API error: {response.status} - {error_text}")
                    
                    if response.status == 401:
                        return {
                            'error': 'Invalid Canvas API token',
                            'message': 'Your Canvas API token is invalid. Please update it in your profile.',
                            'statusCode': 401
                        }
                    
                    return {
                        'error': f'Failed to fetch courses: {response.status}',
                        'message': f'Canvas API returned error {response.status}',
                        'statusCode': response.status
                    }
                    
    except Exception as e:
        logger.error(f"Get Canvas courses error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_canvas_course_quizzes(token: str, course_id: str) -> dict:
    """Get quizzes for a specific Canvas course for AchieveUp using stored Canvas API token."""
    try:
        # Verify user token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result['user']['id']
        
        # Get user's stored Canvas API token
        canvas_token = await get_user_canvas_token(user_id)
        if not canvas_token:
            return {
                'error': 'Canvas API token not found',
                'message': 'Please update your Canvas API token in your profile',
                'statusCode': 400
            }
        
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{CANVAS_API_URL}/courses/{course_id}/quizzes"
        params = {
            'per_page': 100
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    quizzes_data = await response.json()
                    
                    # Transform to AchieveUp format
                    quizzes = []
                    for quiz in quizzes_data:
                        quiz_info = {
                            'id': str(quiz.get('id')),
                            'title': quiz.get('title', ''),
                            'course_id': str(course_id)
                        }
                        quizzes.append(quiz_info)
                    
                    return quizzes
                else:
                    error_text = await response.text()
                    logger.error(f"Canvas API error: {response.status} - {error_text}")
                    
                    if response.status == 401:
                        return {
                            'error': 'Invalid Canvas API token',
                            'message': 'Your Canvas API token is invalid. Please update it in your profile.',
                            'statusCode': 401
                        }
                    
                    return {
                        'error': f'Failed to fetch quizzes: {response.status}',
                        'message': f'Canvas API returned error {response.status}',
                        'statusCode': response.status
                    }
                    
    except Exception as e:
        logger.error(f"Get Canvas quizzes error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_canvas_quiz_questions(token: str, quiz_id: str) -> dict:
    """Get questions for a specific Canvas quiz for AchieveUp using stored Canvas API token."""
    try:
        # Verify user token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result['user']['id']
        
        # Get user's stored Canvas API token
        canvas_token = await get_user_canvas_token(user_id)
        if not canvas_token:
            return {
                'error': 'Canvas API token not found',
                'message': 'Please update your Canvas API token in your profile',
                'statusCode': 400
            }
        
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{CANVAS_API_URL}/quizzes/{quiz_id}/questions"
        params = {
            'per_page': 100
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    questions_data = await response.json()
                    
                    # Transform to AchieveUp format
                    questions = []
                    for question in questions_data:
                        question_info = {
                            'id': str(question.get('id')),
                            'question_text': question.get('question_text', ''),
                            'quiz_id': str(quiz_id)
                        }
                        questions.append(question_info)
                    
                    return questions
                else:
                    error_text = await response.text()
                    logger.error(f"Canvas API error: {response.status} - {error_text}")
                    
                    if response.status == 401:
                        return {
                            'error': 'Invalid Canvas API token',
                            'message': 'Your Canvas API token is invalid. Please update it in your profile.',
                            'statusCode': 401
                        }
                    
                    return {
                        'error': f'Failed to fetch questions: {response.status}',
                        'message': f'Canvas API returned error {response.status}',
                        'statusCode': response.status
                    }
                    
    except Exception as e:
        logger.error(f"Get Canvas questions error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def cache_canvas_data(course_id: str, data_type: str, data: list) -> None:
    """Cache Canvas data for AchieveUp (optional performance optimization)."""
    try:
        cache_data = {
            'course_id': course_id,
            'data_type': data_type,
            'data': data,
            'cached_at': datetime.utcnow()
        }
        
        if data_type == 'courses':
            await achieveup_canvas_courses_collection.update_one(
                {'course_id': course_id},
                {'$set': cache_data},
                upsert=True
            )
        elif data_type == 'quizzes':
            await achieveup_canvas_quizzes_collection.update_one(
                {'course_id': course_id},
                {'$set': cache_data},
                upsert=True
            )
        elif data_type == 'questions':
            await achieveup_canvas_questions_collection.update_one(
                {'quiz_id': course_id},  # course_id is actually quiz_id here
                {'$set': cache_data},
                upsert=True
            )
            
    except Exception as e:
        logger.error(f"Cache Canvas data error: {str(e)}")

async def get_cached_canvas_data(course_id: str, data_type: str) -> dict:
    """Get cached Canvas data for AchieveUp (optional performance optimization)."""
    try:
        if data_type == 'courses':
            cached = await achieveup_canvas_courses_collection.find_one({'course_id': course_id})
        elif data_type == 'quizzes':
            cached = await achieveup_canvas_quizzes_collection.find_one({'course_id': course_id})
        elif data_type == 'questions':
            cached = await achieveup_canvas_questions_collection.find_one({'quiz_id': course_id})
        else:
            return None
            
        if cached:
            # Check if cache is still valid (e.g., less than 1 hour old)
            cache_age = datetime.utcnow() - cached['cached_at']
            if cache_age.total_seconds() < 3600:  # 1 hour
                return cached['data']
                
        return None
        
    except Exception as e:
        logger.error(f"Get cached Canvas data error: {str(e)}")
        return None

async def get_instructor_courses(canvas_token: str) -> dict:
    """Get all courses taught by the instructor using their Canvas token."""
    try:
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }
        url = f"{CANVAS_API_URL}/courses"
        params = {'enrollment_type': 'teacher', 'per_page': 100}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    courses_data = await response.json()
                    courses = []
                    for course in courses_data:
                        courses.append({
                            'id': str(course.get('id')),
                            'name': course.get('name', ''),
                            'code': course.get('course_code', '')
                        })
                    return courses
                else:
                    error_text = await response.text()
                    logger.error(f"Canvas instructor courses error: {response.status} - {error_text}")
                    return {'error': f'Failed to fetch instructor courses: {response.status}', 'statusCode': response.status}
    except Exception as e:
        logger.error(f"Get instructor courses error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_instructor_course_quizzes(canvas_token: str, course_id: str) -> dict:
    """Get all quizzes in a course for instructor."""
    try:
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }
        url = f"{CANVAS_API_URL}/courses/{course_id}/quizzes"
        params = {'per_page': 100}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    quizzes_data = await response.json()
                    quizzes = []
                    for quiz in quizzes_data:
                        quizzes.append({
                            'id': str(quiz.get('id')),
                            'title': quiz.get('title', ''),
                            'course_id': str(course_id)
                        })
                    return quizzes
                else:
                    error_text = await response.text()
                    logger.error(f"Canvas instructor quizzes error: {response.status} - {error_text}")
                    return {'error': f'Failed to fetch instructor quizzes: {response.status}', 'statusCode': response.status}
    except Exception as e:
        logger.error(f"Get instructor course quizzes error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_instructor_quiz_questions(canvas_token: str, quiz_id: str) -> dict:
    """Get all questions in a quiz for instructor."""
    try:
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }
        url = f"{CANVAS_API_URL}/quizzes/{quiz_id}/questions"
        params = {'per_page': 100}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    questions_data = await response.json()
                    questions = []
                    for question in questions_data:
                        questions.append({
                            'id': str(question.get('id')),
                            'question_text': question.get('question_text', ''),
                            'quiz_id': str(quiz_id)
                        })
                    return questions
                else:
                    error_text = await response.text()
                    logger.error(f"Canvas instructor quiz questions error: {response.status} - {error_text}")
                    return {'error': f'Failed to fetch instructor quiz questions: {response.status}', 'statusCode': response.status}
    except Exception as e:
        logger.error(f"Get instructor quiz questions error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500} 