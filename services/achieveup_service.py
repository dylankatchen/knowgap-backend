# services/achieveup_service.py

import logging
import uuid
from datetime import datetime, timezone
from services.achieveup_auth_service import achieveup_verify_token
from config import Config
from utils import text_utils
from utils.ai_utils import client, AI_MODEL
import re
from html import unescape

from mongodb import get_db


# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup for AchieveUp data (separate from KnowGap)
db = get_db()

# Collections
achieveup_skill_matrices_collection = db[Config.ACHIEVEUP_SKILL_MATRICES_COLLECTION]
achieveup_question_skills_collection = db[Config.ACHIEVEUP_QUESTION_SKILLS_COLLECTION]
achieveup_progress_collection = db[Config.ACHIEVEUP_PROGRESS_COLLECTION]
achieveup_course_descriptions_collection = db[Config.ACHIEVEUP_COURSE_DESCRIPTIONS_COLLECTION]
achieveup_import_status_collection = db[Config.ACHIEVEUP_IMPORT_STATUS_COLLECTION]

MAX_COURSE_DESCRIPTION_LENGTH = 12000

async def create_skill_matrix(token: str, course_id: str, matrix_name: str, skills: list) -> dict:
    """Create skill matrix for a course."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get user info and verify instructor access
        user = user_result['user']
        user_role = user['role']
        canvas_token_type = user.get('canvasTokenType', 'student')
        
        # Verify instructor access (consistent with other endpoints)
        if user_role != 'instructor' or canvas_token_type != 'instructor':
            return {
                'error': 'Access denied',
                'message': 'Instructor access required',
                'statusCode': 403
            }
        # Check if matrix name already exists for this course (allow multiple matrices per course)
        existing_matrix = await achieveup_skill_matrices_collection.find_one({
            'course_id': course_id, 
            'matrix_name': matrix_name
        })
        if existing_matrix:
            return {
                'error': 'Matrix name already exists',
                'message': f'A skill matrix with the name \'{matrix_name}\' already exists for this course',
                'statusCode': 409
            }
        
        # Create matrix document
        matrix_id = str(uuid.uuid4())
        matrix_doc = {
            '_id': matrix_id,
            'course_id': course_id,
            'matrix_name': matrix_name,
            'skills': skills,
            'created_at': datetime.now(timezone.utc).replace(tzinfo=None),
            'updated_at': datetime.now(timezone.utc).replace(tzinfo=None),
            'created_by': user['id']
        }
        
        # Insert into database
        await achieveup_skill_matrices_collection.insert_one(matrix_doc)
        
        return matrix_doc
        
    except Exception as e:
        logger.error(f"Create skill matrix error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def update_skill_matrix(token: str, matrix_id: str, skills: list, matrix_name: str) -> dict:
    """Update skill matrix."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Update matrix
        result = await achieveup_skill_matrices_collection.update_one(
            {'_id': matrix_id},
            {
                '$set': {
                    'skills': skills,
                    'matrix_name': matrix_name,
                    'updated_at': datetime.now(timezone.utc).replace(tzinfo=None)

                }
            }
        )
        
        if result.matched_count == 0:
            return {
                'error': 'Matrix not found',
                'message': 'Skill matrix not found',
                'statusCode': 404
            }
        
        # Get updated matrix
        updated_matrix = await achieveup_skill_matrices_collection.find_one({'_id': matrix_id})
        return updated_matrix
        
    except Exception as e:
        logger.error(f"Update skill matrix error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}


async def get_all_skill_matrices_by_course(token: str, course_id: str) -> dict:
    """Get ALL skill matrices for a course (for frontend matrix selection)."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get user info from the correct structure
        user = user_result['user']
        user_id = user['id']
        user_role = user['role']
        canvas_token_type = user.get('canvasTokenType', 'student')
        
        # Verify instructor access (consistent with other endpoints)
        if user_role != 'instructor' or canvas_token_type != 'instructor':
            return {
                'error': 'Access denied',
                'message': 'Instructor access required',
                'statusCode': 403
            }
        
        # ENHANCED DEBUG LOGGING FOR MATRIX RETRIEVAL
        logger.info(f"DEBUG: Searching for matrices with course_id='{course_id}' (type: {type(course_id)})")
        
        # Try both string and exact matches to debug data type issues
        query_string = {'course_id': str(course_id)}
        query_exact = {'course_id': course_id}
        
        logger.info(f"DEBUG: Query 1 (string): {query_string}")
        matrices_string = await achieveup_skill_matrices_collection.find(query_string).to_list(length=None)
        logger.info(f"DEBUG: Found {len(matrices_string)} matrices with string course_id")
        
        logger.info(f"DEBUG: Query 2 (exact): {query_exact}")
        matrices_exact = await achieveup_skill_matrices_collection.find(query_exact).to_list(length=None)
        logger.info(f"DEBUG: Found {len(matrices_exact)} matrices with exact course_id")
        
        # Use string query as primary (most consistent)
        matrices = matrices_string
        
        # Log what we found
        for i, matrix in enumerate(matrices):
            logger.info(f"DEBUG: Matrix {i+1}: name='{matrix.get('matrix_name')}', course_id='{matrix.get('course_id')}' (type: {type(matrix.get('course_id'))})")
        
        # If no matrices found, check what matrices exist in database
        if len(matrices) == 0:
            logger.warning(f"DEBUG: No matrices found for course_id='{course_id}'. Checking all matrices...")
            all_matrices = await achieveup_skill_matrices_collection.find({}).to_list(length=None)
            logger.info(f"DEBUG: Total matrices in database: {len(all_matrices)}")
            for matrix in all_matrices:
                logger.info(f"DEBUG: Existing matrix: course_id='{matrix.get('course_id')}' (type: {type(matrix.get('course_id'))}), name='{matrix.get('matrix_name')}'")
        
        # Convert ObjectId to string for JSON serialization
        for matrix in matrices:
            if '_id' in matrix:
                matrix['_id'] = str(matrix['_id'])
        
        logger.info(f"DEBUG: Returning {len(matrices)} matrices for course {course_id}")
        
        return {
            'matrices': matrices,
            'count': len(matrices)
        }
        
    except Exception as e:
        logger.error(f"Get all skill matrices by course error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_course_description(token: str, course_id: str) -> dict:
    """Get persisted instructor course description used as AI context."""
    try:
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result

        user = user_result['user']
        user_role = user.get('role')
        canvas_token_type = user.get('canvasTokenType', 'student')

        if user_role != 'instructor' or canvas_token_type != 'instructor':
            return {
                'error': 'Access denied',
                'message': 'Instructor access required',
                'statusCode': 403
            }

        doc = await achieveup_course_descriptions_collection.find_one(
            {
                'course_id': str(course_id),
                'instructor_id': user['id']
            },
            {
                '_id': 0
            }
        )

        if not doc:
            return {
                'course_id': str(course_id),
                'description': '',
                'updated_at': None
            }

        return {
            'course_id': doc.get('course_id', str(course_id)),
            'description': doc.get('description', ''),
            'updated_at': doc.get('updated_at').isoformat() if doc.get('updated_at') else None
        }

    except Exception as e:
        logger.error(f"Get course description error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def upsert_course_description(token: str, course_id: str, description: str) -> dict:
    """Create or update persisted instructor course description used as AI context."""
    try:
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result

        user = user_result['user']
        user_role = user.get('role')
        canvas_token_type = user.get('canvasTokenType', 'student')

        if user_role != 'instructor' or canvas_token_type != 'instructor':
            return {
                'error': 'Access denied',
                'message': 'Instructor access required',
                'statusCode': 403
            }

        if not isinstance(description, str):
            return {
                'error': 'Invalid request',
                'message': 'description must be a string',
                'statusCode': 400
            }

        if len(description) > MAX_COURSE_DESCRIPTION_LENGTH:
            return {
                'error': 'Validation failed',
                'message': f'description cannot exceed {MAX_COURSE_DESCRIPTION_LENGTH} characters',
                'statusCode': 400
            }

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        query = {
            'course_id': str(course_id),
            'instructor_id': user['id']
        }

        await achieveup_course_descriptions_collection.update_one(
            query,
            {
                '$set': {
                    'course_id': str(course_id),
                    'instructor_id': user['id'],
                    'description': description,
                    'updated_at': now
                },
                '$setOnInsert': {
                    'created_at': now
                }
            },
            upsert=True
        )

        return {
            'course_id': str(course_id),
            'description': description,
            'updated_at': now.isoformat()
        }

    except Exception as e:
        logger.error(f"Upsert course description error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def assign_skills_to_questions(token: str, course_id: str, question_skills: dict) -> dict:
    """Assign skills to quiz questions."""
    try:
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result

        # Retrieve user id to assign ownership to skill assignments
        user_id = user_result['user']['id']

        for question_text, skills in question_skills.items():
            question_hash = text_utils.hash_text(question_text)

            assignment_doc = {
                'question_id': question_hash,
                'owner_id': user_id,
                'skills': skills,
                'assigned_at': datetime.now(timezone.utc).replace(tzinfo=None)
            }

            await achieveup_question_skills_collection.update_one(
                {'question_id': question_hash, 'owner_id': user_id},
                {'$set': assignment_doc, '$addToSet': {'course_ids': course_id}},
                upsert=True
            )

        return {'message': 'Skills assigned successfully'}

    except Exception as e:
        logger.error(f"Assign skills error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}
    
async def get_assigned_skills(token: str, course_id: str, question_ids:list[str]) -> dict:
    """Get skill assigned for a quiz."""
    try:
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result

        user_id = user_result['user']['id']

        if not question_ids:
            return {
                'error': 'Missing required fields',
                'message': 'question_ids are required',
                'statusCode': 400
            }

        # Build hash to original text map for translating results back
        hash_to_text = {}
        for text in question_ids:
            h = text_utils.hash_text(text)
            hash_to_text[h] = text

        hashes = list(hash_to_text.keys())

        # Single lookup by owner_id and hash
        cursor = achieveup_question_skills_collection.find(
            {'owner_id': user_id, 'question_id': {'$in': hashes}},
            {'_id': 0}
        )
        docs = await cursor.to_list(length=None)

        # Translate hashes back to original question text for the frontend
        question_skills = {}
        for d in docs:
            original_text = hash_to_text.get(d['question_id'])
            if original_text:
                question_skills[original_text] = d.get('skills', [])

        return {
            'course_id': course_id,
            'question_skills': question_skills
        }

    except Exception as e:
        logger.error(f"Get assigned skills error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}


async def get_student_progress(token: str, student_id: str, course_id: str) -> dict:
    """Get skill progress for a student in a course."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Find progress
        progress = await achieveup_progress_collection.find_one({
            'student_id': student_id,
            'course_id': course_id
        })
        
        if not progress:
            return {
                'student_id': student_id,
                'course_id': course_id,
                'skill_progress': {},
                'last_updated': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
            }

        return {
            'student_id': progress.get('student_id', student_id),
            'course_id': progress.get('course_id', course_id),
            'skill_progress': progress.get('skill_progress', {}),
            'last_updated': progress['last_updated'].isoformat()
            if isinstance(progress.get('last_updated'), datetime)
            else progress.get('last_updated')
        }
        
    except Exception as e:
        logger.error(f"Get student progress error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}


async def get_instructor_dashboard(token: str) -> dict:
    """Get instructor dashboard data with course overview and analytics."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result['user']['id']
        
        # Get instructor's Canvas courses
        from services.achieveup_canvas_service import get_instructor_courses
        from services.achieveup_auth_service import get_user_canvas_token
        from services.achieveup_canvas_service import get_course_students
        
        canvas_token = await get_user_canvas_token(user_id)
        if not canvas_token:
            return {
                'error': 'No Canvas token',
                'message': 'No Canvas API token found for user',
                'statusCode': 400
            }
        
        courses_result = await get_instructor_courses(canvas_token, active_only=True)
        if 'error' in courses_result:
            return courses_result

        courses = courses_result if isinstance(courses_result, list) else []

        # Count each student once, even if they're in several of these courses.
        # If any roster can't be loaded, the count is reported as unknown (None)
        # rather than as a partial number.
        student_ids = set()
        roster_failed = False
        for course in courses:
            students_result = await get_course_students(canvas_token, course['id'])
            if not isinstance(students_result, list):
                logger.warning(f"Dashboard student count unavailable, roster for course {course['id']} failed: {students_result.get('error')}")
                roster_failed = True
                break
            student_ids.update(student['id'] for student in students_result)

        # Get skill matrices count
        matrices_count = await achieveup_skill_matrices_collection.count_documents({})
        
        # Get recent activity
        recent_matrices = await achieveup_skill_matrices_collection.find({}).sort([('created_at', -1)]).limit(5).to_list(length=5)
        
        dashboard_data = {
            'courses': courses,
            'students': None if roster_failed else len(student_ids),
            'totalCourses': len(courses),
            'totalSkillMatrices': matrices_count,
            'recentMatrices': recent_matrices,
            'lastUpdated': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Get instructor dashboard error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_instructor_course_students(token: str, course_id: str) -> dict:
    """Get list of students in instructor's course."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result['user']['id']
        
        # Get Canvas API token
        from services.achieveup_auth_service import get_user_canvas_token
        canvas_token = await get_user_canvas_token(user_id)
        if not canvas_token:
            return {
                'error': 'No Canvas token',
                'message': 'No Canvas API token found for user',
                'statusCode': 400
            }
        
        # Get students from Canvas
        from services.achieveup_canvas_service import get_course_students
        students_result = await get_course_students(canvas_token, course_id)
        
        return students_result
        
    except Exception as e:
        logger.error(f"Get instructor course students error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def suggest_course_skills_ai(token: str, course_data: dict) -> dict:
    """Generate AI-powered skill suggestions for a course."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result

        user = user_result['user']
        
        import json

        course_name = course_data.get('courseName', '')
        course_code = course_data.get('courseCode', '')
        course_id = str(course_data.get('courseId', ''))

        stored_description = ''
        if course_id:
            stored_doc = await achieveup_course_descriptions_collection.find_one(
                {
                    'course_id': course_id,
                    'instructor_id': user['id']
                },
                {
                    'description': 1,
                    '_id': 0
                }
            )
            if stored_doc and isinstance(stored_doc.get('description'), str):
                stored_description = stored_doc['description'].strip()

        request_description = (course_data.get('courseDescription') or '').strip()
        course_description = stored_description or request_description or 'N/A'
        logger.info(
            "AI skill suggestion course description source for course %s: %s",
            course_id,
            'stored' if stored_description else 'request'
        )
        
        prompt = f"""
        Generate 8-12 specific, measurable skills for this course. They should be about 3-5 words.
        
        Course: {course_name}
        Code: {course_code}
        Description: {course_description}
        
        Return ONLY valid JSON array:
        [{{"skill": "Skill Name", "description": "Brief description"}}, ...]
        
        Make skills specific to the course subject matter.
        """
        
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert curriculum designer. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            #temperature=0.7,
            max_tokens=10000
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Parse JSON response
        import re
        json_match = re.search(r'\[.*\]', ai_response, re.DOTALL)
        if json_match:
            skills = json.loads(json_match.group())
        else:
            skills = json.loads(ai_response)
        
        return {
            'courseId': course_data.get('courseId'),
            'courseName': course_name,
            'skills': skills,  # Changed from 'suggestedSkills' to match frontend expectation
            'generatedAt': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'method': 'ai',
            'courseDescriptionSource': 'stored' if stored_description else 'request'
        }
        
    except Exception as e:
        logger.error(f"AI skill suggestion error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': 'Internal server error', 'message': str(e), 'statusCode': 500}


async def analyze_questions_with_ai(token: str, questions: list, course_id: str, matrix_id: str = None) -> dict:
    """Analyze questions using AI for complexity and skill mapping."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        course_skills = []
        matrix_used = None
        
        # Priority 1: Use the specified matrix_id if provided
        if matrix_id:
            logger.info(f"Using specified matrix_id: {matrix_id}")
            matrix = await achieveup_skill_matrices_collection.find_one({'_id': matrix_id})
            if matrix and 'skills' in matrix:
                course_skills = matrix['skills']
                matrix_used = matrix.get('matrix_name', matrix_id)
                logger.info(f"Found matrix '{matrix_used}' with {len(course_skills)} skills")
            else:
                logger.warning(f"Matrix {matrix_id} not found")
        
        # Priority 2: If no matrix_id or matrix not found, try getting the FIRST matrix for the course
        # (This is better than getting ALL skills from ALL matrices)
        if not course_skills and course_id:
            logger.info(f"No matrix_id provided or found, getting first matrix for course: {course_id}")
            matrix = await achieveup_skill_matrices_collection.find_one({'course_id': str(course_id)})
            if matrix and 'skills' in matrix:
                course_skills = matrix['skills']
                matrix_used = matrix.get('matrix_name', 'default')
                logger.info(f"Using first matrix '{matrix_used}' with {len(course_skills)} skills")
        
        # If still no skills found, return error
        if not course_skills:
            logger.error(f"No skill matrix found for course_id={course_id}, matrix_id={matrix_id}")
            return {
                'error': 'No skill matrix found',
                'message': f'Please create a skill matrix for course {course_id} or provide a valid matrix_id',
                'statusCode': 404
            }
        
        logger.info(f"Analyzing {len(questions)} questions with {len(course_skills)} skills from matrix '{matrix_used}'")
        
        # Import AI service
        from services.achieveup_ai_service import analyze_questions
        
        # Analyze questions with course skills context
        analysis_results = await analyze_questions(questions, course_skills)
        
        return {
            'totalQuestions': len(questions),
            'analyses': analysis_results,
            'generatedAt': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'course_id': course_id,
            'matrix_id': matrix_id,
            'matrix_used': matrix_used,
            'course_skills_used': course_skills,
            'skill_count': len(course_skills)
        }
        
    except Exception as e:
        logger.error(f"AI question analysis error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': 'Internal server error', 'statusCode': 500}

async def delete_skill_matrix(token: str, matrix_id: str) -> dict:
    """Delete a skill matrix by ID."""
    try:
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result

        user = user_result['user']
        if user['role'] != 'instructor' or user.get('canvasTokenType') != 'instructor':
            return {
                'error': 'Access denied',
                'message': 'Instructor access required',
                'statusCode': 403
            }

        result = await achieveup_skill_matrices_collection.delete_one({
            '_id': matrix_id
        })

        if result.deleted_count == 0:
            return {
                'error': 'Matrix not found',
                'message': 'Skill matrix does not exist',
                'statusCode': 404
            }

        return {'success': True}

    except Exception as e:
        logger.error(f"Delete skill matrix error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def import_matrices_from_course(source_course_id: str, target_course_id: str, user_id: str, token: str):
    
    source_matrices = await get_all_skill_matrices_by_course(token,source_course_id)
    
    if not source_matrices:
        return {
            'error': 'No matrices found',
            'message': f'No skill matrices found for source course {source_course_id}',
            'statusCode': 404
        }

    imported = []
    matrices = source_matrices.get('matrices', [])
    for matrix in matrices:
        matrix_name = matrix.get('matrix_name') + ' (Imported Skills Matrix)'
        skills = matrix.get('skills', []) or []
        created = await create_skill_matrix(token, target_course_id,matrix_name, skills)
        imported.append(created)

    await achieveup_import_status_collection.update_one(
        {'target_course_id': target_course_id},
        {
            '$set': {
                'source_course_id': source_course_id,
                'target_course_id': target_course_id,
                'matrices_imported': True,
                'updated_at': datetime.now(timezone.utc).replace(tzinfo=None)
            },
            '$setOnInsert': {
                'assignments_imported': False,
                'created_at': datetime.now(timezone.utc).replace(tzinfo=None)
            }
        },
        upsert=True
    )    

    return imported


def strip_html(text: str) -> str:
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', ' ', text)
    return unescape(text)

def normalize_text(text: str) -> str:
    text = strip_html(text).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

async def import_skill_setting_from_course(source_course_id: str, target_course_id: str, user_id: str, token: str):
    """Import question skill assignments from source course to target course by matching quiz names and question text."""
    try:
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result

        user = user_result['user']
        if user['role'] != 'instructor' or user.get('canvasTokenType') != 'instructor':
            return {
                'error': 'Access denied',
                'message': 'Instructor access required',
                'statusCode': 403
            }

        from services.achieveup_auth_service import get_user_canvas_token
        from services.achieveup_canvas_service import get_instructor_quiz_questions, get_instructor_course_quizzes

        canvas_token = await get_user_canvas_token(user_id)
        if not canvas_token:
            return {
                'error': 'No Canvas token',
                'message': 'No Canvas API token found for user',
                'statusCode': 400
            }

        source_quizzes = await get_instructor_course_quizzes(canvas_token, source_course_id)
        target_quizzes = await get_instructor_course_quizzes(canvas_token, target_course_id)

        if isinstance(source_quizzes, dict) and 'error' in source_quizzes:
            return source_quizzes
        if isinstance(target_quizzes, dict) and 'error' in target_quizzes:
            return target_quizzes

        # map target quizzes by normalized title
        target_quiz_map = {
            normalize_text(q.get('title', '')): q
            for q in target_quizzes
        }

        imported_count = 0
        matched_quizzes = 0
        matched_questions = 0
        details = []

        for source_quiz in source_quizzes:
            source_quiz_title = source_quiz.get('title', '')
            source_quiz_key = normalize_text(source_quiz_title)

            target_quiz = target_quiz_map.get(source_quiz_key)
            if not target_quiz:
                details.append({
                    'quiz_title': source_quiz_title,
                    'status': 'skipped',
                    'reason': 'No matching target quiz found'
                })
                continue

            matched_quizzes += 1

            source_quiz_id = str(source_quiz.get('id'))
            target_quiz_id = str(target_quiz.get('id'))

            source_questions = await get_instructor_quiz_questions(canvas_token, source_quiz_id, source_course_id)
            target_questions = await get_instructor_quiz_questions(canvas_token, target_quiz_id, target_course_id)


            if isinstance(source_questions, dict) and 'error' in source_questions:
                details.append({
                    'quiz_title': source_quiz_title,
                    'status': 'skipped',
                    'reason': 'Failed to load source questions'
                })
                continue

            if isinstance(target_questions, dict) and 'error' in target_questions:
                details.append({
                    'quiz_title': source_quiz_title,
                    'status': 'skipped',
                    'reason': 'Failed to load target questions'
                })
                continue

            source_question_ids = [str(q.get('id')) for q in source_questions if q.get('id')]
            source_assignments_result = await get_assigned_skills(token, source_course_id, source_question_ids)

            if 'error' in source_assignments_result:
                details.append({
                    'quiz_title': source_quiz_title,
                    'status': 'skipped',
                    'reason': 'Failed to load source assignments'
                })
                continue

            source_assignments = source_assignments_result.get('question_skills', {})

            # target questions by normalized question text
            target_question_map = {}
            for tq in target_questions:
                key = normalize_text(tq.get('question_text', ''))
                if key and key not in target_question_map:
                    target_question_map[key] = tq

            target_question_skills = {}
            quiz_imported_count = 0

            for sq in source_questions:
                source_qid = str(sq.get('id'))
                source_skills = source_assignments.get(source_qid, [])
                if not source_skills:
                    continue

                source_qtext_key = normalize_text(sq.get('question_text', ''))
                if not source_qtext_key:
                    continue

                matched_target_question = target_question_map.get(source_qtext_key)
                if not matched_target_question:
                    continue

                target_qid = str(matched_target_question.get('id'))
                target_question_skills[target_qid] = source_skills
                quiz_imported_count += 1

            if target_question_skills:
                save_result = await assign_skills_to_questions(token, target_course_id, target_question_skills)
                if 'error' in save_result:
                    details.append({
                        'quiz_title': source_quiz_title,
                        'status': 'failed',
                        'reason': save_result.get('message', save_result.get('error'))
                    })
                    continue

                imported_count += len(target_question_skills)
                matched_questions += quiz_imported_count

                details.append({
                    'quiz_title': source_quiz_title,
                    'status': 'imported',
                    'matched_questions': quiz_imported_count
                })
            else:
                details.append({
                    'quiz_title': source_quiz_title,
                    'status': 'skipped',
                    'reason': 'No matching assigned questions found'
                })

        await achieveup_import_status_collection.update_one(
            {'target_course_id': target_course_id},
            {
                '$set': {
                'source_course_id': source_course_id,
                'target_course_id': target_course_id,
                'assignments_imported': True,
                'updated_at': datetime.now(timezone.utc).replace(tzinfo=None)
                },
                '$setOnInsert': {
                'matrices_imported': False,
                'created_at': datetime.now(timezone.utc).replace(tzinfo=None)
                }
            },
            upsert=True
        )  

        return {
            'message': 'Skill assignments imported successfully',
            'source_course_id': source_course_id,
            'target_course_id': target_course_id,
            'matched_quizzes': matched_quizzes,
            'matched_questions': matched_questions,
            'imported_count': imported_count,
            'details': details
        }

          

    except Exception as e:
        logger.error(f"Import skill assignment error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'error': 'Internal server error',
            'message': str(e),
            'statusCode': 500
        }
    
async def get_import_status(token: str, course_id: str) -> dict:
    try:
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result

        status = await achieveup_import_status_collection.find_one(
            {'target_course_id': course_id},
            {'_id': 0}
        )

        if not status:
            return {
                'target_course_id': course_id,
                'matrices_imported': False,
                'assignments_imported': False
            }

        return status

    except Exception as e:
        logger.error(f"Get import status error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}
    
