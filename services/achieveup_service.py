# services/achieveup_service.py

import logging
import uuid
from datetime import datetime, timezone
from services.achieveup_auth_service import (
    achieveup_verify_token,
    get_user_canvas_token,
    require_instructor,
)
from config import Config
from utils import text_utils
import re

from mongodb import get_db
from utils.youtube_utils import resolve_channel
from services.achieveup_canvas_service import (
    validate_canvas_instructor_for_course,
)


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
achieveup_course_channels_collection = db[Config.ACHIEVEUP_COURSE_CHANNELS_COLLECTION]

MAX_COURSE_DESCRIPTION_LENGTH = 12000

async def create_skill_matrix(token: str, course_id: str, matrix_name: str, skills: list) -> dict:
    """Create skill matrix for a course."""
    try:
        user, error = await require_course_instructor(token, course_id)
        if error:
            return error

        return await _insert_skill_matrix(course_id, matrix_name, skills, user['id'])

    except Exception as e:
        logger.error(f"Create skill matrix error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def _insert_skill_matrix(course_id: str, matrix_name: str, skills: list, created_by: str) -> dict:
    """Save a new matrix. No auth or Canvas checks, so callers do their own."""
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
        'created_by': created_by
    }

    # Insert into database
    await achieveup_skill_matrices_collection.insert_one(matrix_doc)

    return matrix_doc

async def update_skill_matrix(token: str, matrix_id: str, skills: list, matrix_name: str) -> dict:
    """Update skill matrix."""
    try:
        user, error = await require_instructor(token)
        if error:
            return error

        matrix = await achieveup_skill_matrices_collection.find_one({'_id': matrix_id})
        if not matrix:
            return {
                'error': 'Matrix not found',
                'message': 'Skill matrix not found',
                'statusCode': 404
            }

        error = await check_course_instructor(user, matrix['course_id'])
        if error:
            return error

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
        # Read-only, so a past course the instructor taught is allowed
        # (viewing old matrices and importing them into a new term).
        _, error = await require_course_instructor(token, course_id, include_concluded=True)
        if error:
            return error
        
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
        user, error = await require_course_instructor(token, course_id)
        if error:
            return error

        # Each question maps to a list of skill names. Mastery uses every
        # skill as a lookup key and database value, so anything that isn't a
        # string (an object, number or null) would break or alter it.
        if not isinstance(question_skills, dict) or not all(
                isinstance(skills, list) and all(isinstance(skill, str) for skill in skills)
                for skills in question_skills.values()):
            return {
                'error': 'Invalid skill mappings',
                'message': 'Each question must map to a list of skill names.',
                'statusCode': 400
            }

        await _save_question_skills(user['id'], course_id, question_skills)
        return {'message': 'Skills assigned successfully'}

    except Exception as e:
        logger.error(f"Assign skills error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def _save_question_skills(user_id: str, course_id: str, question_skills: dict) -> None:
    """Save question-to-skill mappings. No auth or Canvas checks, so callers do their own."""
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
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result

        # Students may read their own progress. Anyone else must be an
        # instructor who teaches (or taught) the course. An account with no
        # Canvas id saved is never treated as the student being asked about.
        own_id = user_result['user'].get('canvas_student_id')
        if own_id is None or str(own_id) != str(student_id):
            _, error = await require_course_instructor(token, course_id, include_concluded=True)
            if error:
                return error

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

        dashboard_data = {
            'courses': courses,
            'students': None if roster_failed else len(student_ids),
            'totalCourses': len(courses),
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
        # OpenAI calls cost money, so only an instructor of the course may
        # make them. A past course they taught is allowed: nothing is saved,
        # and the matrix creator lists past courses too.
        user, error = await require_course_instructor(
            token, course_data.get('courseId'), include_concluded=True)
        if error:
            return error

        # Use OpenAI directly with proper async syntax
        from openai import AsyncOpenAI
        import json
        
        client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        
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
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert curriculum designer. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            #temperature=0.7,
            max_completion_tokens=10000
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
        return {'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}


async def analyze_questions_with_ai(token: str, questions: list, course_id: str, matrix_id: str = None) -> dict:
    """Analyze questions using AI for complexity and skill mapping."""
    try:
        _, error = await require_course_instructor(token, course_id)
        if error:
            return error

        course_skills = []
        matrix_used = None

        # Priority 1: Use the specified matrix_id if provided
        if matrix_id:
            logger.info(f"Using specified matrix_id: {matrix_id}")
            matrix = await achieveup_skill_matrices_collection.find_one({'_id': matrix_id})
            # A matrix from another course is treated as not found, so it
            # can't be read through a course the caller does teach.
            if matrix and str(matrix.get('course_id')) != str(course_id):
                matrix = None
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
        user, error = await require_instructor(token)
        if error:
            return error

        matrix = await achieveup_skill_matrices_collection.find_one({'_id': matrix_id})
        if not matrix:
            return {
                'error': 'Matrix not found',
                'message': 'Skill matrix does not exist',
                'statusCode': 404
            }

        error = await check_course_instructor(user, matrix['course_id'])
        if error:
            return error

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
    # The target is written to, so the user must teach it now. The source
    # is only read; get_all_skill_matrices_by_course checks it and allows
    # a past course they taught. Both checks run before anything is saved.
    user, error = await require_course_instructor(token, target_course_id)
    if error:
        return error

    source_matrices = await get_all_skill_matrices_by_course(token,source_course_id)
    if 'error' in source_matrices:
        return source_matrices

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
        created = await _insert_skill_matrix(target_course_id, matrix_name, skills, user['id'])
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
                'created_at': datetime.now(timezone.utc).replace(tzinfo=None)
            }
        },
        upsert=True
    )    

    return imported


async def get_import_status(token: str, course_id: str) -> dict:
    try:
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result

        # Older records also have an assignments_imported flag from the
        # removed skill assignment import, so it's left out here.
        status = await achieveup_import_status_collection.find_one(
            {'target_course_id': course_id},
            {'_id': 0, 'assignments_imported': 0}
        )

        if not status:
            return {
                'target_course_id': course_id,
                'matrices_imported': False
            }

        return status

    except Exception as e:
        logger.error(f"Get import status error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}
    

async def check_course_instructor(user: dict, course_id: str, include_concluded: bool = False):
    """Return None if Canvas confirms the (already verified) instructor
    teaches the course, otherwise an error dict. include_concluded also
    accepts a course they taught in a past term; use it only for reads."""
    if course_id is None or course_id == '':
        return {
            'error': 'Missing course ID',
            'message': 'Course ID is required.',
            'statusCode': 400
        }
    # Canvas course ids are plain digits. Anything else (e.g. '.?' or
    # '1/../2') would change which Canvas URL gets checked.
    if not re.fullmatch(r'[0-9]+', str(course_id)):
        return {
            'error': 'Invalid course ID',
            'message': 'Course ID must be a number.',
            'statusCode': 400
        }

    canvas_token = await get_user_canvas_token(user['id'])
    if not canvas_token:
        return {
            'error': 'Canvas not connected',
            'message': 'No Canvas API token is linked to your account.',
            'statusCode': 400
        }

    course_check = await validate_canvas_instructor_for_course(
        canvas_token, str(course_id), include_concluded)
    if not course_check.get('valid'):
        # Only a denial is a 403. Canvas outages (502/503) and token
        # problems (400) keep their own status.
        status = course_check.get('statusCode', 403)
        return {
            'error': 'Access denied' if status == 403 else 'Canvas error',
            'message': course_check.get('message'),
            'statusCode': status
        }
    return None


async def require_course_instructor(token: str, course_id: str, include_concluded: bool = False):
    """Return (user, None) if the user is an instructor Canvas confirms
    teaches the course, otherwise (None, error_dict). See
    check_course_instructor for include_concluded."""
    user, error = await require_instructor(token)
    if error:
        return None, error

    error = await check_course_instructor(user, course_id, include_concluded)
    if error:
        return None, error
    return user, None


async def get_saved_course_channels(course_id: str, instructor_id: str):
    """Return the channels an instructor saved for a course. A plain database
    read with no auth or Canvas checks, so callers do their own."""
    course_doc = await achieveup_course_channels_collection.find_one(
        {"course_id": str(course_id), "instructor_id": instructor_id})
    return (course_doc or {}).get("youtube_channels", [])


async def get_course_channels(token: str, course_id: str) -> list | dict:
    """
    Fetch configured YouTube channels for a given course ID.
    Returns a list of {'channel_id', 'name'} dicts (empty if none are
    saved), or an error dict if the user can't access the course.
    """
    try:
        # Read-only, so a past course the instructor taught is allowed.
        user, error = await require_course_instructor(token, course_id, include_concluded=True)
        if error:
            return error

        return await get_saved_course_channels(course_id, user['id'])
    except Exception as e:
        logger.error(f"Error fetching channels for course {course_id}: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}


async def update_course_channels(token: str, course_id: str, channels: list):
    """
    Update or insert configured YouTube channels for a given course ID.
    """
    try:
        user, error = await require_course_instructor(token, course_id)
        if error:
            return error

        user_id = user['id']

        if any(not isinstance(c, str) or not c.strip() for c in channels):
            return {
                'error': 'Invalid channels',
                'message': 'Each channel must be a non-empty YouTube handle or channel ID.',
                'statusCode': 400
            }

        # Resolve each channel to its YouTube ID and drop entries that point
        # at a channel already listed (e.g. '@Foo', '@foo' or Foo's own ID).
        # If the lookup itself fails (quota, bad key, outage), say so rather
        # than "channel not found".
        saved_channels = []
        not_found = []

        unique_channels: dict = {
            channel.strip().lstrip('@').lower(): channel.strip()
            for channel in channels}
        if len(unique_channels) > Config.MAX_COURSE_CHANNELS:
            return {
                'error': 'Too many channels',
                'message': f'Link up to {Config.MAX_COURSE_CHANNELS} channels',
                'statusCode': 400
            }

        try:
            for c in unique_channels.values():
                channel = await resolve_channel(c)
                if not channel:
                    not_found.append(c)
                elif channel not in saved_channels:
                    saved_channels.append(channel)
        except Exception:
            return {
                'error': 'YouTube unavailable',
                'message': ("Couldn't reach YouTube to check these "
                            "channels. Please try again later."),
                'statusCode': 502
            }
        if not_found:
            return {'error': 'Channel not found', 'message': f"Couldn't find these YouTube channels: {', '.join(not_found)}", 'statusCode': 400}



        await achieveup_course_channels_collection.update_one(
            {"course_id": str(course_id),
             "instructor_id": user_id},
            {"$set": {
                "course_id": str(course_id),
                "youtube_channels": saved_channels,
                "instructor_id": user_id,
                "updated_at": datetime.now(timezone.utc).replace(tzinfo=None)
            }},
            upsert=True
        )

        logger.info(f"Successfully saved channels for course {course_id}: {saved_channels}")
        return {'channels': saved_channels}

    except Exception as e:
        logger.error(f"MongoDB Error in update_course_channels for course {course_id}: {str(e)}", exc_info=True)
        return {'error': 'Internal server error', 'statusCode': 500}
