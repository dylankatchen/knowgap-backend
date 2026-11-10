# services/achieveup_canvas_service.py

import asyncio
import aiohttp
import ssl
import logging
import re
from services.achieveup_auth_service import achieveup_verify_token, get_user_canvas_token
from config import Config
from utils import text_utils
from datetime import datetime, timezone

from mongodb import get_db

# Set up logging
logger = logging.getLogger(__name__)

# Create SSL context based on environment
# DEVELOPMENT: Bypass SSL verification (for local development issues)
# PRODUCTION: Use proper SSL verification (secure)
def get_ssl_context():
    """Get SSL context based on environment."""
    if Config.ENV == 'development':
        try:
            # Try to use certifi certificates first for security
            import certifi
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            return ssl_context
        except Exception as e:
            # Fallback to disabled verification only if certifi fails
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context
    else:
        # Production: Use default SSL verification (secure)
        logger.info("✅ SSL certificate verification is ENABLED (production mode)")
        return True  # aiohttp uses True for default SSL verification

def create_canvas_session():
    """Create aiohttp ClientSession with appropriate SSL settings."""
    ssl_setting = get_ssl_context()
    if ssl_setting is True:
        # Production: use default SSL verification
        return aiohttp.ClientSession()
    else:
        # Development: use custom SSL context
        return aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_setting))


def _extract_next_canvas_link(link_header: str) -> str:
    """Extract the Canvas pagination next URL from an RFC 5988 Link header."""
    if not link_header:
        return None

    for part in link_header.split(','):
        if 'rel="next"' not in part:
            continue
        match = re.search(r'<([^>]+)>', part)
        if match:
            return match.group(1)

    return None


async def _fetch_all_canvas_pages(session, url: str, headers: dict, params: dict = None, resource: str = 'instructor courses'):
    """Fetch all pages from a Canvas endpoint and return a combined list payload."""
    all_items = []
    next_url = url
    request_params = params or {}
    page_count = 0

    while next_url:
        page_count += 1
        async with session.get(next_url, headers=headers, params=request_params) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Canvas pagination request failed: {response.status} - {error_text}")
                return None, {
                    'error': f'Failed to fetch {resource}: {response.status}',
                    'statusCode': response.status
                }

            payload = await response.json()
            if isinstance(payload, list):
                all_items.extend(payload)
            elif payload:
                all_items.append(payload)

            next_url = _extract_next_canvas_link(response.headers.get('Link', ''))
            request_params = None

    logger.info(f"Fetched {len(all_items)} Canvas items across {page_count} page(s)")
    return all_items, None

# MongoDB setup for AchieveUp Canvas data (separate from KnowGap)
# Only bypass SSL verification in development
db = get_db()


# Canvas API configuration
CANVAS_API_URL = getattr(Config, 'CANVAS_API_URL', 'https://webcourses.ucf.edu/api/v1')
CANVAS_GRAPHQL_API_URL = getattr(Config, "CANVAS_GRAPHQL_API_URL")

async def validate_canvas_token(canvas_token: str, canvas_token_type: str = 'student') -> dict:
    """Validate Canvas API token by testing it with Canvas API. Supports student and instructor tokens."""
    try:
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }
        
        # Test token by calling Canvas API /users/self endpoint
        url = f"{CANVAS_API_URL}/users/self"
        async with create_canvas_session() as session:
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
            # Request courses with enrollment information included
            courses_url = f"{CANVAS_API_URL}/courses"
            params = {
                'enrollment_type': 'teacher',  # Only get courses where user is a teacher
                'per_page': 100,
                'include[]': 'total_students'
            }
            async with create_canvas_session() as session:
                async with session.get(courses_url, headers=headers, params=params) as courses_response:
                    if courses_response.status != 200:
                        error_text = await courses_response.text()
                        logger.error(f"Canvas instructor validation error: {courses_response.status} - {error_text}")
                        return {
                            'valid': False,
                            'message': 'Token does not have instructor permissions. Please provide an instructor token.'
                        }
                    courses_data = await courses_response.json()
                    # If we get any courses with enrollment_type=teacher, user is an instructor
                    if not courses_data or len(courses_data) == 0:
                        return {
                            'valid': False,
                            'message': 'Token is valid but does not have instructor access to any courses.'
                        }
                    permissions['instructor'] = True
                    logger.info(f"User has instructor access to {len(courses_data)} course(s)")
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

async def validate_canvas_instructor_for_course(canvas_token: str, course_id: str, include_concluded: bool = False) -> dict:
    """Validate Instructor of a specific course. Canvas marks a teacher's
    enrollment 'completed' once the term ends, so include_concluded also
    accepts courses they taught in a past term (for read-only checks)."""
    try:
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }

        # Test token by calling Canvas API /users/self endpoint
        url = f"{CANVAS_API_URL}/users/self"
        async with create_canvas_session() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    if response.status == 401:
                        return {
                            'valid': False,
                            'statusCode': 400,
                            'message': 'Invalid Canvas API token. Please check your token and try again.'
                        }
                    error_text = await response.text()
                    logger.error(f"Canvas API validation error: {response.status} - {error_text}")
                    return {
                        'valid': False,
                        'statusCode': 502,
                        'message': f'Canvas API returned error {response.status}. Please try again later.'
                    }
                user_data = await response.json()

        # Check if user is instructor for the specified course
        user_id = user_data.get('id')
        enrollments_url = f"{CANVAS_API_URL}/courses/{course_id}/enrollments"
        params = {
            'user_id': user_id,
            'type[]': ['TeacherEnrollment', 'TaEnrollment', 'DesignerEnrollment'],
            'state[]': 'current_and_concluded' if include_concluded else 'active',
            'per_page': 10
        }
        async with create_canvas_session() as session:
            async with session.get(enrollments_url, headers=headers, params=params) as enrollments_response:
                if enrollments_response.status == 401:
                    return {
                        'valid': False,
                        'statusCode': 403,
                        'message': 'Failed to retrieve enrollment information.'
                    }
                if enrollments_response.status == 404:
                    return {
                        'valid': False,
                        'statusCode': 403,
                        'message': f'Course {course_id} was not found in Canvas.'
                    }
                if enrollments_response.status != 200:
                    error_text = await enrollments_response.text()
                    logger.error(f"Canvas enrollments validation error: {enrollments_response.status} - {error_text}")
                    return {
                        'valid': False,
                        'statusCode': 502,
                        'message': f'Canvas API returned error {enrollments_response.status}. Please try again later.'
                    }
                enrollments_data = await enrollments_response.json()

            #check if instructor level enrollment is active
            if not enrollments_data or len(enrollments_data) == 0:
                return {
                    'valid': False,
                    'statusCode': 403,
                    'message': f'Token is valid but user does not have instructor access to course {course_id}.'
                }
            enrollment_type = enrollments_data[0].get('type', '')
            logger.info(f"User {user_id} has '{enrollment_type}' enrollemt in course {course_id}")

            return {
                'valid': True,
                'message': f'Token is valid and user has instructor access to course {course_id}',
                'user_info': {
                    'id': user_data.get('id'),
                    'name': user_data.get('name'),
                    'email': user_data.get('email')
                },
                'permissions': {
                    'instructor': True,
                    'course_id': course_id,
                    'enrollment_type': enrollment_type
                }
            }

    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(f"Canvas API connection error: {e!r}")
        return {
            'valid': False,
            'statusCode': 503,
            'message': 'Unable to connect to Canvas API. Please check your internet connection and try again.'
        }
    except Exception as e:
        logger.error(f"Canvas course instructor validation error: {str(e)}")
        return {
            'valid': False,
            'statusCode': 500,
            'message': 'An unexpected error occurred while validating instructor access to the course.'
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
            'enrollment_type': 'student',
            'per_page': 100
        }
        
        async with create_canvas_session() as session:
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

        json_payload: dict = {
            "query": "query get_course_quizzes ($course_id: ID!) {" \
                        "course(id: $course_id) {" \
                            "quizzesConnection(first: 100) {" \
                            "nodes {" \
                                "title," \
                                "_id" \
                            "}" \
                            "}" \
                        "}" \
                        "}",
            "variables": {"course_id": course_id}
        }

        
        async with create_canvas_session() as session:
            async with session.post(CANVAS_GRAPHQL_API_URL, headers=headers, json=json_payload) as response:
                if response.status == 200:
                    quizzes_data = await response.json()

                    if "errors" in quizzes_data:
                        logger.error(f"Canvas' GraphQL API call returned an error: {quizzes_data['errors']}")
                        return {
                            "error": "Canvas API call error.",
                            "message": "An error occured when attempting to communicate with Canvas' API.",
                            "statusCode": 400
                        }

                    quizzes = []
                    for quiz in quizzes_data.get("data").get("course", {}).get("quizzesConnection", {}).get("nodes"):
                        quizzes.append({
                            'id': str(quiz.get('_id')),
                            'title': quiz.get('title', ''),
                            'course_id': str(course_id)
                        })

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
        

        async with create_canvas_session() as session:
            
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


async def get_instructor_courses(canvas_token: str, active_only: bool = False) -> dict:
    """Get all courses taught by the instructor using their Canvas token.
    By default this includes past-term courses; active_only drops them."""
    try:
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }
        url = f"{CANVAS_API_URL}/courses"
        params = {'enrollment_type': 'teacher', 'per_page': 100}
        if active_only:
            params['enrollment_state'] = 'active'
        async with create_canvas_session() as session:
            courses_data, error = await _fetch_all_canvas_pages(session, url, headers, params)
            if error:
                return error

            courses = []
            for course in courses_data:
                courses.append({
                    'id': str(course.get('id')),
                    'name': course.get('name', ''),
                    'original_name': course.get('original_name'),
                    'code': course.get('course_code', ''),
                    'term': course.get('enrollment_term_id','')
                    #add code here 'description': course.get('public_description', '')
                })
            return courses
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

        json_payload: dict = {
            "query": "query get_course_quizzes ($course_id: ID!) {" \
                        "course(id: $course_id) {" \
                            "quizzesConnection(first: 100) {" \
                            "nodes {" \
                                "title," \
                                "_id" \
                            "}" \
                            "}" \
                        "}" \
                        "}",
            "variables": {"course_id": course_id}
        }

        async with create_canvas_session() as session:
            async with session.post(CANVAS_GRAPHQL_API_URL, headers=headers, json=json_payload) as response:
                if response.status == 200:
                    quizzes_data = await response.json()

                    if "errors" in quizzes_data:
                        logger.error(f"Canvas' GraphQL API call returned an error: {quizzes_data['errors']}")
                        return {
                            "error": "Canvas API call error.",
                            "message": "An error occured when attempting to communicate with Canvas' API.",
                            "statusCode": 400
                        }

                    quizzes = []
                    for quiz in quizzes_data.get("data").get("course", {}).get("quizzesConnection", {}).get("nodes"):
                        quizzes.append({
                            'id': str(quiz.get('_id')),
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

async def get_instructor_quiz_questions(canvas_token: str, quiz_id: str, course_id: str) -> dict:
    """Get all questions in a quiz for instructor."""
    try:

        #for deubuggin
        logger.info(f"Getting questions for quiz_id = {quiz_id}, course_id={course_id}")
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }

        url = f"{CANVAS_API_URL}/courses/{course_id}/quizzes/{quiz_id}/questions"
        new_quizzes_url: str = f"{getattr(Config, 'CANVAS_NEW_QUIZ_API_URL')}/courses/{course_id}/quizzes/{quiz_id}/items"
        params = {'per_page': 100}
        async with create_canvas_session() as session:

            match await is_new_quiz(canvas_token, course_id, quiz_id):

                # Classic quiz logic.
                case False:
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            questions_data = await response.json()
                            questions = []
                            for question in questions_data:
                                if question.get('question_type') == 'text_only_question': continue
                                question_text = question.get('question_text', '')

                                # Extract Canvas file IDs from any embedded images
                                _, attachment_ids, attachment_urls = text_utils.parse_html(question_text)

                                answers = question.get('answers', [])
                                raw_answer_texts = [a.get('text') or '' for a in answers]
                                answer_texts = [text_utils.normalize_text(t) for t in raw_answer_texts if t.strip()]
                                question_key = text_utils.build_question_key(
                                    question_text, raw_answer_texts, fallback_id=question.get('id')
                                )

                                questions.append({
                                    'id': str(question.get('id')),
                                    'question_text': question_text,
                                    'quiz_id': str(quiz_id),
                                    'attachment_ids': attachment_ids,
                                    'attachment_urls': attachment_urls,
                                    'answer_texts': answer_texts,
                                    'question_key': question_key
                                })
                            return questions
                        else:
                            error_text = await response.text()
                            logger.error(f"Canvas instructor quiz questions error: {response.status} - {error_text}")
                            return {'error': f'Failed to fetch instructor quiz questions: {response.status}', 'statusCode': response.status}
                
                # New quiz logic.
                case True:
                    async with session.get(new_quizzes_url, headers=headers, params=params) as res:
                        if res.status == 200:
                            questions_data = await res.json()

                            # Check for errors.
                            if "errors" in questions_data:
                                logger.error(f"Canvas instructor quiz questions error: {questions_data.get('errors')}")
                                return {'error': f'Failed to fetch instructor quiz questions.', 'statusCode': res.status}

                            # Return all question fields that are not stimulus.
                            questions = []
                            for question in questions_data:
                                if question.get("entry_type") == "Stimulus":
                                    continue
                                item_body = (question.get("entry") or {}).get("item_body")
                                questions.append({
                                    "id": str(question.get("id")),
                                    "question_text": item_body,
                                    "quiz_id": str(quiz_id),
                                    "question_key": text_utils.build_question_key(
                                        item_body, fallback_id=question.get('id')
                                    )
                                })
                            return questions
                        else:
                            logger.error(f"Canvas instructor quiz questions error: {res.status} - {await res.text()}")
                            return {'error': f'Failed to fetch instructor quiz questions: {res.status}', 'statusCode': res.status}
                        
                # Could not find quiz.
                case None:
                    logger.error(f"Failed to determine quiz type: {course_id}, quiz_id: {quiz_id}")
                    return {'error': f'Failed to determine instructor quiz type.', 'statusCode': 404}
    except Exception as e:
        logger.error(f"Get instructor quiz questions error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_course_students(canvas_token: str, course_id: str) -> dict:
    """Get students enrolled in a course."""
    try:
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{CANVAS_API_URL}/courses/{course_id}/enrollments"
        params = {
            'type[]': 'StudentEnrollment',
            'per_page': 100,
            'include[]': 'user'
        }
        
        async with create_canvas_session() as session:
            enrollments_data, error = await _fetch_all_canvas_pages(
                session, url, headers, params, resource='students'
            )
            if error:
                return error

            students = []
            for enrollment in enrollments_data:
                user = enrollment.get('user', {})
                students.append({
                    'id': str(user.get('id')),
                    'name': user.get('name', ''),
                    'email': user.get('email', ''),
                    'sortable_name': user.get('sortable_name', ''),
                    'enrollment_state': enrollment.get('enrollment_state', ''),
                    'course_id': str(course_id)
                })

            return students

    except Exception as e:
        logger.error(f"Get course students error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

def official_course_name(course: dict) -> str | None:
    """The course's real name. When the token's user has nicknamed the course, Canvas puts
    the nickname in `name` and the real name in `original_name`."""
    return course.get('original_name') or course.get('name') or None

async def get_canvas_course_name(canvas_token: str, course_id: str) -> str | None:
    """Fetch just a course's official name from Canvas (no syllabus or other includes)."""
    try:
        headers = {'Authorization': f'Bearer {canvas_token}'}
        async with create_canvas_session() as session:
            async with session.get(f"{CANVAS_API_URL}/courses/{course_id}", headers=headers) as response:
                if response.status == 200:
                    return official_course_name(await response.json())
                logger.error(f"Canvas course name error for {course_id}: {response.status} - {await response.text()}")
    except Exception as e:
        logger.error(f"Get course name error for {course_id}: {str(e)}")
    return None

async def get_course_detailed_info(canvas_token: str, course_id: str) -> dict:
    """Get detailed course information including syllabus and description."""
    try:
        headers = {
            'Authorization': f'Bearer {canvas_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{CANVAS_API_URL}/courses/{course_id}"
        params = {
            'include[]': ['syllabus_body', 'public_description', 'course_image']
        }
        
        async with create_canvas_session() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    course_data = await response.json()
                    
                    return {
                        'id': str(course_data.get('id')),
                        'name': course_data.get('name', ''),
                        'course_code': course_data.get('course_code', ''),
                        'sis_course_id': course_data.get('sis_course_id', ''),
                        'syllabus_body': course_data.get('syllabus_body', ''),
                        'public_description': course_data.get('public_description', ''),
                        'total_students': course_data.get('total_students', 0),
                        'enrollment_term_id': course_data.get('enrollment_term_id'),
                        'course_image': course_data.get('image_download_url', ''),
                        'start_at': course_data.get('start_at'),
                        'end_at': course_data.get('end_at')
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Canvas course details error: {response.status} - {error_text}")
                    return {
                        'error': f'Failed to fetch course details: {response.status}',
                        'statusCode': response.status
                    }
                    
    except Exception as e:
        logger.error(f"Get course detailed info error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}


async def is_new_quiz(canvas_api_token: str, course_id: str, quiz_id: str) -> bool | None:
    """Checks whether a quiz in a class is a new quiz or a classic quiz."""

    headers = {
        'Authorization': f'Bearer {canvas_api_token}',
        'Content-Type': 'application/json'
    }

    after: str | None = None

    json_query: str = "query get_quiz_types($course_id: ID!, $after: String) {" \
                    "course(id: $course_id) {" \
                        "assignmentsConnection(first: 100, after: $after) {" \
                            "nodes {" \
                                "_id," \
                                "submissionTypes," \
                                "quiz {" \
                                    "_id" \
                                "}," \
                                "isNewQuiz" \
                            "}," \
                            "pageInfo {" \
                                "hasNextPage," \
                                "endCursor" \
                            "}" \
                        "}" \
                    "}" \
                "}"

    async with create_canvas_session() as session:
        while True:
            json_payload: dict = {
                "query": json_query,
                "variables": {"course_id": course_id, "after": after}
            }

            async with session.post(CANVAS_GRAPHQL_API_URL, headers=headers, json=json_payload) as res:

                # Check for response errors.
                if res.status == 200:
                    quizzes_data = await res.json()

                    if "errors" in quizzes_data:
                        logger.error(f"Canvas' GraphQL API call returned an error: {quizzes_data['errors']}")
                        return

                    quizzes = (((quizzes_data.get("data") or {}).get("course") or {}).get("assignmentsConnection") or {})
                    
                    # Check every quiz to find the matching quiz.
                    for quiz in (quizzes.get("nodes") or []):
                        if (quiz.get("quiz") or {}).get("_id", "") == quiz_id or quiz.get("_id") == quiz_id:
                            if quiz.get("isNewQuiz", False) is True:
                                return True
                            else:
                                return False
                    
                    # If quiz not found and there is another results page, move to it.
                    current_page_info: dict = quizzes.get("pageInfo") or {}
                    if not (current_page_info.get("hasNextPage")):
                        return
                    
                    after = current_page_info.get("endCursor")
                else:
                    logger.error(f"Canvas' GraphQL API call returned an error.")
                    return

async def get_token_expiration(canvas_api_token: str) -> tuple[int, datetime | None]:
    """
    Checks whether a Canvas token has an expiration date, and if so returns the expiration date.
    HTTP status codes are used to convey whether the token is valid or not. If the returned status
    is 200 paired with a None value, the token has no expiration date set.
    """

    headers = {
            'Authorization': f'Bearer {canvas_api_token}',
            'Content-Type': 'application/json'
            }

    url = f"{CANVAS_API_URL}/users/self/tokens/{canvas_api_token[:10]}"

    try:
        async with create_canvas_session() as session:
            async with session.get(url, headers=headers) as res:
                
                # If statements to check the API status code
                # and return the correct HTTP code.
                if res.status in (401, 404):
                    return 401, None
                elif res.status != 200:
                    error_text = await res.text()
                    logger.error(f"Canvas API validation error: {res.status} - {error_text}")
                    return res.status, None
                
                token_information = await res.json()

                # Get token expiration data.
                expiration_information: str | None = token_information.get("expires_at")
                expiration_date: datetime | None = (
                                datetime.fromisoformat(expiration_information.replace("Z", "+00:00"))
                                .astimezone(timezone.utc)
                                .replace(tzinfo=None)
                                if expiration_information else None
                            )
                
                return 200, expiration_date

    except Exception as err:
        logger.error(f"Error checking token information: {str(err)}")
        return 500, None
