from quart import Blueprint, request, jsonify
from services.achieveup_service import (
    create_skill_matrix,
    update_skill_matrix,
    get_skill_matrix,
    assign_skills_to_questions,
    suggest_skills_for_question,
    generate_badges_for_student,
    get_student_badges,
    get_student_progress,
    update_student_progress,
    get_individual_analytics,
    export_course_data,
    import_course_data,
    analyze_questions,
    get_question_suggestions
)
import logging

achieveup_bp = Blueprint('achieveup', __name__)
logger = logging.getLogger(__name__)

@achieveup_bp.route('/achieveup/matrix/create', methods=['POST'])
async def create_skill_matrix_route():
    """Create skill matrix for a course. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        course_id = data.get('course_id')
        matrix_name = data.get('matrix_name')
        skills = data.get('skills', [])
        
        if not course_id or not matrix_name:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Course ID and matrix name are required',
                'statusCode': 400
            }), 400
        
        # Call service
        result = await create_skill_matrix(token, course_id, matrix_name, skills)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 201
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/matrix/<matrix_id>', methods=['PUT'])
async def update_skill_matrix_route(matrix_id):
    """Update skill matrix. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        skills = data.get('skills', [])
        
        # Call service
        result = await update_skill_matrix(token, matrix_id, skills)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/matrix/<course_id>', methods=['GET'])
async def get_skill_matrix_route(course_id):
    """Get skill matrix for a course. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Call service
        result = await get_skill_matrix(token, course_id)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/skills/assign', methods=['POST'])
async def assign_skills_to_questions_route():
    """Assign skills to quiz questions. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        course_id = data.get('course_id')
        question_skills = data.get('question_skills', {})
        
        if not course_id or not question_skills:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Course ID and question skills are required',
                'statusCode': 400
            }), 400
        
        # Call service
        result = await assign_skills_to_questions(token, course_id, question_skills)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify({'message': 'Skills assigned successfully'}), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/skills/suggest', methods=['POST'])
async def suggest_skills_for_question_route():
    """Suggest skills for a quiz question using AI. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        question_text = data.get('question_text')
        course_context = data.get('course_context')
        
        if not question_text:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Question text is required',
                'statusCode': 400
            }), 400
        
        # Call service
        result = await suggest_skills_for_question(token, question_text, course_context)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/badges/generate', methods=['POST'])
async def generate_badges_for_student_route():
    """Generate badges for a student. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        student_id = data.get('student_id')
        course_id = data.get('course_id')
        skill_levels = data.get('skill_levels', {})
        
        if not student_id or not course_id:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Student ID and course ID are required',
                'statusCode': 400
            }), 400
        
        # Call service
        result = await generate_badges_for_student(token, student_id, course_id, skill_levels)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/badges/<student_id>', methods=['GET'])
async def get_student_badges_route(student_id):
    """Get badges for a student. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Call service
        result = await get_student_badges(token, student_id)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/progress/<student_id>/<course_id>', methods=['GET'])
async def get_student_progress_route(student_id, course_id):
    """Get skill progress for a student in a course. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Call service
        result = await get_student_progress(token, student_id, course_id)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/progress/<student_id>/<course_id>', methods=['PUT'])
async def update_student_progress_route(student_id, course_id):
    """Update skill progress for a student in a course. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        skill_updates = data.get('skill_updates', {})
        
        # Call service
        result = await update_student_progress(token, student_id, course_id, skill_updates)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/progress/update', methods=['POST'])
async def update_progress_route():
    """Update skill progress (frontend-compatible endpoint). (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        skill_updates = data.get('skill_updates', {})
        
        # For this endpoint, we'll need to get student_id and course_id from the token
        # or from the request data. For now, we'll use a default approach
        # This can be enhanced based on the actual frontend requirements
        
        # Call service with default values (can be enhanced)
        result = await update_student_progress(token, "default_student", "default_course", skill_updates)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/graphs/individual/<student_id>', methods=['GET'])
async def get_individual_analytics_route(student_id):
    """Get analytics data for a student. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Call service
        result = await get_individual_analytics(token, student_id)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/export/<course_id>', methods=['GET'])
async def export_course_data_route(course_id):
    """Export course data (CSV). (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Call service
        result = await export_course_data(token, course_id)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/import', methods=['POST'])
async def import_course_data_route():
    """Import course data. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        course_id = data.get('course_id')
        import_data = data.get('data', {})
        
        if not course_id:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Course ID is required',
                'statusCode': 400
            }), 400
        
        # Call service
        result = await import_course_data(token, course_id, import_data)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify({'message': 'Course data imported successfully'}), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/instructor/skill-matrix/create', methods=['POST'])
async def instructor_skill_matrix_create_route():
    """Create skill matrix with quiz question mapping (instructor only)."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing token', 'message': 'Authorization header with Bearer token is required', 'statusCode': 401}), 401
        token = auth_header.split(' ')[1]
        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({'error': user_result['error'], 'message': user_result['error'], 'statusCode': user_result['statusCode']}), user_result['statusCode']
        user_id = user_result['user']['id']
        from motor.motor_asyncio import AsyncIOMotorClient
        from config import Config
        client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
        db = client[Config.DATABASE]
        user_doc = await db['AchieveUp_Users'].find_one({'user_id': user_id})
        if not user_doc or user_doc.get('canvas_token_type', 'student') != 'instructor':
            return jsonify({'error': 'Forbidden', 'message': 'Instructor token required', 'statusCode': 403}), 403
        data = await request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request', 'message': 'Request body is required', 'statusCode': 400}), 400
        course_id = data.get('course_id')
        matrix_name = data.get('matrix_name')
        skills = data.get('skills', [])
        quiz_questions = data.get('quiz_questions', {})
        if not course_id or not matrix_name or not skills:
            return jsonify({'error': 'Missing required fields', 'message': 'Course ID, matrix name, and skills are required', 'statusCode': 400}), 400
        from services.achieveup_service import create_instructor_skill_matrix
        result = await create_instructor_skill_matrix(token, course_id, matrix_name, skills, quiz_questions)
        return jsonify(result), 201
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500

@achieveup_bp.route('/achieveup/instructor/courses/<course_id>/analytics', methods=['GET'])
async def instructor_course_analytics_route(course_id):
    """Get detailed analytics for instructor's course (instructor only)."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing token', 'message': 'Authorization header with Bearer token is required', 'statusCode': 401}), 401
        token = auth_header.split(' ')[1]
        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({'error': user_result['error'], 'message': user_result['error'], 'statusCode': user_result['statusCode']}), user_result['statusCode']
        user_id = user_result['user']['id']
        from motor.motor_asyncio import AsyncIOMotorClient
        from config import Config
        client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
        db = client[Config.DATABASE]
        user_doc = await db['AchieveUp_Users'].find_one({'user_id': user_id})
        if not user_doc or user_doc.get('canvas_token_type', 'student') != 'instructor':
            return jsonify({'error': 'Forbidden', 'message': 'Instructor token required', 'statusCode': 403}), 403
        from services.achieveup_service import get_instructor_course_analytics
        result = await get_instructor_course_analytics(token, course_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500

@achieveup_bp.route('/achieveup/questions/analyze', methods=['POST'])
async def analyze_questions_route():
    """Analyze question complexity and suggest skills. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        questions = data.get('questions', [])
        
        if not questions:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Questions array is required',
                'statusCode': 400
            }), 400
        
        # Call service
        result = await analyze_questions(token, questions)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/questions/<question_id>/suggestions', methods=['GET'])
async def get_question_suggestions_route(question_id):
    """Get AI-powered skill suggestions for specific question. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Call service
        result = await get_question_suggestions(token, question_id)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/instructor/dashboard', methods=['GET'])
async def instructor_dashboard_route():
    """Get instructor dashboard data (instructor only)."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing token', 'message': 'Authorization header with Bearer token is required', 'statusCode': 401}), 401
        token = auth_header.split(' ')[1]
        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({'error': user_result['error'], 'message': user_result['error'], 'statusCode': user_result['statusCode']}), user_result['statusCode']
        user_id = user_result['user']['id']
        from motor.motor_asyncio import AsyncIOMotorClient
        from config import Config
        client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
        db = client[Config.DATABASE]
        user_doc = await db['AchieveUp_Users'].find_one({'user_id': user_id})
        if not user_doc or user_doc.get('canvas_token_type', 'student') != 'instructor':
            return jsonify({'error': 'Forbidden', 'message': 'Instructor token required', 'statusCode': 403}), 403
        from services.achieveup_service import get_instructor_dashboard
        result = await get_instructor_dashboard(token)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500

@achieveup_bp.route('/achieveup/instructor/students/<course_id>', methods=['GET'])
async def instructor_students_route(course_id):
    """Get list of students in instructor's course (instructor only)."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing token', 'message': 'Authorization header with Bearer token is required', 'statusCode': 401}), 401
        token = auth_header.split(' ')[1]
        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({'error': user_result['error'], 'message': user_result['error'], 'statusCode': user_result['statusCode']}), user_result['statusCode']
        user_id = user_result['user']['id']
        from motor.motor_asyncio import AsyncIOMotorClient
        from config import Config
        client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
        db = client[Config.DATABASE]
        user_doc = await db['AchieveUp_Users'].find_one({'user_id': user_id})
        if not user_doc or user_doc.get('canvas_token_type', 'student') != 'instructor':
            return jsonify({'error': 'Forbidden', 'message': 'Instructor token required', 'statusCode': 403}), 403
        from services.achieveup_service import get_instructor_course_students
        result = await get_instructor_course_students(token, course_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500

@achieveup_bp.route('/achieveup/instructor/course/<course_id>/student-analytics', methods=['GET'])
async def instructor_student_analytics_route(course_id):
    """Get student analytics for instructor's course (instructor only)."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing token', 'message': 'Authorization header with Bearer token is required', 'statusCode': 401}), 401
        token = auth_header.split(' ')[1]
        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({'error': user_result['error'], 'message': user_result['error'], 'statusCode': user_result['statusCode']}), user_result['statusCode']
        user_id = user_result['user']['id']
        from motor.motor_asyncio import AsyncIOMotorClient
        from config import Config
        client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
        db = client[Config.DATABASE]
        user_doc = await db['AchieveUp_Users'].find_one({'user_id': user_id})
        if not user_doc or user_doc.get('canvas_token_type', 'student') != 'instructor':
            return jsonify({'error': 'Forbidden', 'message': 'Instructor token required', 'statusCode': 403}), 403
        from services.achieveup_service import get_instructor_student_analytics
        result = await get_instructor_student_analytics(token, course_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500
 
@achieveup_bp.route('/ai/analyze-questions', methods=['POST'])
async def ai_analyze_questions_route():
    """Analyze question complexity and suggest skills using AI. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        questions = data.get('questions', [])
        
        if not questions:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Questions array is required',
                'statusCode': 400
            }), 400
        
        # Call service
        result = await analyze_questions(token, questions)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/ai/suggest-skills', methods=['POST'])
async def ai_suggest_skills_route():
    """Suggest skills for questions using AI. (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        question_text = data.get('question_text')
        course_context = data.get('course_context')
        
        if not question_text:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Question text is required',
                'statusCode': 400
            }), 400
        
        # Call service
        result = await suggest_skills_for_question(token, question_text, course_context)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/ai/suggest-skills', methods=['POST'])
async def achieveup_ai_suggest_skills_route():
    """AI-powered skill suggestions for course (frontend-requested endpoint). (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        # ADD DETAILED LOGGING FOR DEBUGGING
        logger.info(f"Skill Suggestions Request Received: {data}")
        logger.info(f"Request Headers: {dict(request.headers)}")
        
        if not data:
            logger.error("No request body received")
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        course_id = data.get('courseId')
        course_name = data.get('courseName')
        course_code = data.get('courseCode')
        course_description = data.get('courseDescription', '')
        
        # LOG PARSED DATA
        logger.info(f"Parsed: courseId={course_id}, courseName={course_name}, courseCode={course_code}, courseDescription={bool(course_description)}")
        
        # ENHANCED VALIDATION with detailed error messages
        validation_errors = []
        
        if not course_id:
            validation_errors.append("courseId is required")
        if not course_name:
            validation_errors.append("courseName is required")
        if not course_code:
            validation_errors.append("courseCode is required")
        
        if validation_errors:
            logger.error(f"Skill suggestions validation failed: {validation_errors}")
            return jsonify({
                'error': 'Validation failed',
                'message': '; '.join(validation_errors),
                'received_data': {
                    'courseId': course_id,
                    'courseName': course_name,
                    'courseCode': course_code,
                    'courseDescription': bool(course_description),
                    'description_length': len(course_description) if course_description else 0
                },
                'statusCode': 400
            }), 400
        
        # Call the AI service
        from services.achieveup_service import suggest_course_skills_ai
        result = await suggest_course_skills_ai(token, {
            'courseId': course_id,
            'courseName': course_name,
            'courseCode': course_code,
            'courseDescription': course_description
        })
        
        if 'error' in result:
            logger.error(f"Skill suggestions AI service error: {result}")
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result.get('statusCode', 500)
            }), result.get('statusCode', 500)
        
        # Format response to match frontend expectations
        if 'skills' in result:
            skills = result['skills']
            logger.info(f"Skill suggestions completed successfully: {len(skills)} skills suggested")
            return jsonify(skills), 200
        else:
            logger.info(f"Skill suggestions completed: {result}")
            return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Skill Suggestions Route Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/ai/analyze-questions', methods=['POST'])
async def achieveup_ai_analyze_questions_route():
    """AI-powered question analysis (frontend-requested endpoint). (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        # ADD DETAILED LOGGING FOR DEBUGGING
        logger.info(f"AI Analysis Request Received: {data}")
        logger.info(f"Request Headers: {dict(request.headers)}")
        
        if not data:
            logger.error("No request body received")
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        course_id = data.get('courseId')
        quiz_id = data.get('quizId')
        questions = data.get('questions', [])
        
        # LOG PARSED DATA
        logger.info(f"Parsed: courseId={course_id}, quizId={quiz_id}, questions_count={len(questions)}")
        
        # RELAXED VALIDATION - Only questions array is truly required
        validation_errors = []
        
        if not questions:
            validation_errors.append("questions array is required")
        elif len(questions) == 0:
            validation_errors.append("questions array cannot be empty")
        
        # Make courseId and quizId optional with intelligent defaults
        if not course_id:
            logger.info("courseId not provided, will auto-detect from questions")
            course_id = "unknown_course"  # Will be detected in service
            
        if not quiz_id:
            logger.info("quizId not provided, using generic quiz ID")
            quiz_id = "generic_quiz"
        
        if validation_errors:
            logger.error(f"Validation failed: {validation_errors}")
            return jsonify({
                'error': 'Validation failed',
                'message': '; '.join(validation_errors),
                'received_data': {
                    'courseId': course_id,
                    'quizId': quiz_id,
                    'questions_count': len(questions) if questions else 0,
                    'questions_sample': questions[:2] if questions else []  # Show first 2 questions for debugging
                },
                'statusCode': 400
            }), 400
        
        # Call the AI service
        from services.achieveup_service import analyze_questions_with_ai
        result = await analyze_questions_with_ai(token, questions)
        
        if 'error' in result:
            logger.error(f"AI service error: {result}")
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result.get('statusCode', 500)
            }), result.get('statusCode', 500)
        
        # Return successful result
        analyses = result.get('analyses', [])
        logger.info(f"AI Analysis completed successfully: {len(analyses)} questions processed")
        
        return jsonify(analyses), 200
        
    except Exception as e:
        logger.error(f"AI Analysis Route Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/ai/bulk-assign', methods=['POST'])
async def achieveup_ai_bulk_assign_route():
    """AI-powered bulk skill assignment (frontend-requested endpoint). (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        course_id = data.get('courseId')
        quiz_id = data.get('quizId')
        
        if not course_id or not quiz_id:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'courseId and quizId are required',
                'statusCode': 400
            }), 400
        
        # Call the AI service for bulk assignment
        from services.achieveup_service import bulk_assign_skills_with_ai
        result = await bulk_assign_skills_with_ai(token, course_id, quiz_id)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        # Return the assignments in the format expected by frontend
        if 'assignments' in result:
            return jsonify(result['assignments']), 200
        else:
            return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/instructor/analyze-questions-with-ai', methods=['POST'])
async def instructor_analyze_questions_with_ai_route():
    """Analyze questions with AI for instructors. (AchieveUp only)"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing token', 'message': 'Authorization header with Bearer token is required', 'statusCode': 401}), 401
        token = auth_header.split(' ')[1]
        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({'error': user_result['error'], 'message': user_result['error'], 'statusCode': user_result['statusCode']}), user_result['statusCode']
        user_id = user_result['user']['id']
        from motor.motor_asyncio import AsyncIOMotorClient
        from config import Config
        client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
        db = client[Config.DATABASE]
        user_doc = await db['AchieveUp_Users'].find_one({'user_id': user_id})
        if not user_doc or user_doc.get('canvas_token_type', 'student') != 'instructor':
            return jsonify({'error': 'Forbidden', 'message': 'Instructor token required', 'statusCode': 403}), 403
        data = await request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request', 'message': 'Request body is required', 'statusCode': 400}), 400
        questions = data.get('questions', [])
        if not questions:
            return jsonify({'error': 'Missing required fields', 'message': 'Questions array is required', 'statusCode': 400}), 400
        from services.achieveup_service import analyze_questions_with_ai_instructor
        result = await analyze_questions_with_ai_instructor(token, questions)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500

@achieveup_bp.route('/instructor/bulk-assign-skills-with-ai', methods=['POST'])
async def instructor_bulk_assign_skills_with_ai_route():
    """Bulk assign skills with AI for instructors. (AchieveUp only)"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing token', 'message': 'Authorization header with Bearer token is required', 'statusCode': 401}), 401
        token = auth_header.split(' ')[1]
        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({'error': user_result['error'], 'message': user_result['error'], 'statusCode': user_result['statusCode']}), user_result['statusCode']
        user_id = user_result['user']['id']
        from motor.motor_asyncio import AsyncIOMotorClient
        from config import Config
        client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
        db = client[Config.DATABASE]
        user_doc = await db['AchieveUp_Users'].find_one({'user_id': user_id})
        if not user_doc or user_doc.get('canvas_token_type', 'student') != 'instructor':
            return jsonify({'error': 'Forbidden', 'message': 'Instructor token required', 'statusCode': 403}), 403
        data = await request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request', 'message': 'Request body is required', 'statusCode': 400}), 400
        course_id = data.get('course_id')
        questions = data.get('questions', [])
        if not course_id or not questions:
            return jsonify({'error': 'Missing required fields', 'message': 'Course ID and questions array are required', 'statusCode': 400}), 400
        from services.achieveup_service import bulk_assign_skills_with_ai_instructor
        result = await bulk_assign_skills_with_ai_instructor(token, course_id, questions)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500
 
@achieveup_bp.route('/achieveup/progress/<student_id>', methods=['GET'])
async def get_student_progress_simple_route(student_id):
    """Get student progress (frontend-requested endpoint). (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Get course_id from query parameters or use default
        course_id = request.args.get('course_id', 'default_course')
        
        # Call service
        result = await get_student_progress(token, student_id, course_id)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/instructor/courses/<course_id>/student-analytics', methods=['GET'])
async def get_course_student_analytics_route(course_id):
    """Get student analytics for a course (frontend-requested endpoint). (AchieveUp only)"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Call analytics service
        from services.analytics_service import get_course_students_analytics
        result = await get_course_students_analytics(token, course_id)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        # Format for frontend expectations
        if 'analytics' in result:
            # Return the analytics data directly - it's already properly formatted
            return jsonify(result['analytics']), 200
        else:
            # Fallback formatting for backward compatibility
            formatted_result = {
                'students': [],
                'skillDistribution': {},
                'averageScores': {}
            }
            
            if 'analytics' in result and 'students' in result['analytics']:
                for student in result['analytics']['students']:
                    formatted_student = {
                        'id': student.get('studentId', student.get('id', '')),
                        'name': student.get('name', ''),
                        'progress': student.get('progress', student.get('overallProgress', 0)),
                        'skillsMastered': student.get('skillsMastered', len([score for score in student.get('skillScores', {}).values() if score >= 80])),
                        'badgesEarned': student.get('badgesEarned', 0),
                        'riskLevel': student.get('riskLevel', 'high'),
                        'skillBreakdown': student.get('skillBreakdown', {})  # Include skillBreakdown!
                    }
                    formatted_result['students'].append(formatted_student)
                    
                    # Add to skill distribution and averages
                    skill_scores = student.get('skillScores', {})
                    if not skill_scores and 'skillBreakdown' in student:
                        # Extract scores from skillBreakdown if skillScores not available
                        skill_scores = {skill: data.get('score', 0) for skill, data in student['skillBreakdown'].items()}
                    
                    for skill, score in skill_scores.items():
                        if skill not in formatted_result['skillDistribution']:
                            formatted_result['skillDistribution'][skill] = 0
                            formatted_result['averageScores'][skill] = []
                        formatted_result['skillDistribution'][skill] += 1
                        formatted_result['averageScores'][skill].append(score)
                        
                # Use data from analytics service if available
                if 'skillDistribution' in result['analytics']:
                    formatted_result['skillDistribution'] = result['analytics']['skillDistribution']
                if 'averageScores' in result['analytics']:
                    formatted_result['averageScores'] = result['analytics']['averageScores']
            
            # Calculate averages for any remaining skills
            for skill, scores in formatted_result['averageScores'].items():
                if isinstance(scores, list) and scores:
                    formatted_result['averageScores'][skill] = round(sum(scores) / len(scores), 1)
                elif not isinstance(scores, (int, float)):
                    formatted_result['averageScores'][skill] = 0
            
            return jsonify(formatted_result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500
 