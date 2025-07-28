# routes/instructor_routes.py

from quart import Blueprint, request, jsonify
from services.achieveup_auth_service import achieveup_verify_token, require_instructor_role
from services.achieveup_service import (
    get_instructor_dashboard,
    get_instructor_course_students,
    get_instructor_student_analytics,
    suggest_course_skills_ai,
    analyze_questions_with_ai_instructor,
    bulk_assign_skills_with_ai_instructor,
    create_skill_matrix,
    get_skill_matrix,
    update_skill_matrix
)
from services.achieveup_canvas_service import (
    get_instructor_courses,
    get_instructor_course_quizzes,
    get_instructor_quiz_questions,
    get_course_detailed_info,
    get_quiz_detailed_questions
)
from services.analytics_service import (
    get_course_students_analytics,
    get_course_risk_assessment,
    export_course_analytics,
    get_individual_graphs
)

instructor_bp = Blueprint('instructor', __name__)

# Dashboard and Overview
@instructor_bp.route('/instructor/dashboard', methods=['GET'])
async def instructor_dashboard_route():
    """Get instructor dashboard with course overview and analytics."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Verify instructor role
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({
                'error': user_result['error'],
                'message': user_result['error'],
                'statusCode': user_result['statusCode']
            }), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        # Get dashboard data
        result = await get_instructor_dashboard(token)
        
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

# Course Management
@instructor_bp.route('/instructor/courses', methods=['GET'])
async def instructor_courses_route():
    """Get all courses taught by the instructor."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # Verify instructor role
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        # Get Canvas API token
        from services.achieveup_auth_service import get_user_canvas_token
        canvas_token = await get_user_canvas_token(user['id'])
        if not canvas_token:
            return jsonify({
                'error': 'No Canvas token',
                'message': 'No Canvas API token found for user',
                'statusCode': 400
            }), 400
        
        # Get instructor courses
        result = await get_instructor_courses(canvas_token)
        
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

@instructor_bp.route('/instructor/courses/<course_id>/details', methods=['GET'])
async def instructor_course_details_route(course_id):
    """Get detailed information about a specific course."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        from services.achieveup_auth_service import get_user_canvas_token
        canvas_token = await get_user_canvas_token(user['id'])
        if not canvas_token:
            return jsonify({
                'error': 'No Canvas token',
                'message': 'No Canvas API token found for user',
                'statusCode': 400
            }), 400
        
        result = await get_course_detailed_info(canvas_token, course_id)
        
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

@instructor_bp.route('/instructor/courses/<course_id>/quizzes', methods=['GET'])
async def instructor_course_quizzes_route(course_id):
    """Get all quizzes in a course for instructor."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        from services.achieveup_auth_service import get_user_canvas_token
        canvas_token = await get_user_canvas_token(user['id'])
        if not canvas_token:
            return jsonify({
                'error': 'No Canvas token',
                'message': 'No Canvas API token found for user',
                'statusCode': 400
            }), 400
        
        result = await get_instructor_course_quizzes(canvas_token, course_id)
        
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

@instructor_bp.route('/instructor/quizzes/<quiz_id>/questions', methods=['GET'])
async def instructor_quiz_questions_route(quiz_id):
    """Get all questions in a quiz for instructor."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        from services.achieveup_auth_service import get_user_canvas_token
        canvas_token = await get_user_canvas_token(user['id'])
        if not canvas_token:
            return jsonify({
                'error': 'No Canvas token',
                'message': 'No Canvas API token found for user',
                'statusCode': 400
            }), 400
        
        result = await get_quiz_detailed_questions(canvas_token, quiz_id)
        
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

# Student Management and Analytics
@instructor_bp.route('/instructor/students/<course_id>', methods=['GET'])
async def instructor_students_route(course_id):
    """Get list of students in instructor's course."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        result = await get_instructor_course_students(token, course_id)
        
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

@instructor_bp.route('/instructor/courses/<course_id>/analytics', methods=['GET'])
async def instructor_course_analytics_route(course_id):
    """Get detailed analytics for instructor's course."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        # Get query parameters
        time_range = request.args.get('time_range', '30d')
        skill_id = request.args.get('skill_id')
        
        result = await get_course_students_analytics(token, course_id, time_range, skill_id)
        
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

@instructor_bp.route('/instructor/course/<course_id>/student-analytics', methods=['GET'])
async def instructor_student_analytics_route(course_id):
    """Get student analytics for instructor's course."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        result = await get_instructor_student_analytics(token, course_id)
        
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

# AI-Powered Features
@instructor_bp.route('/instructor/ai/suggest-skills', methods=['POST'])
async def instructor_ai_suggest_skills_route():
    """Generate AI-powered skill suggestions for a course."""
    try:
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
        
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        result = await suggest_course_skills_ai(token, data)
        
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

@instructor_bp.route('/instructor/analyze-questions-with-ai', methods=['POST'])
async def instructor_analyze_questions_with_ai_route():
    """Analyze questions with AI for instructors."""
    try:
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
        
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        questions = data.get('questions', [])
        if not questions:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Questions array is required',
                'statusCode': 400
            }), 400
        
        result = await analyze_questions_with_ai_instructor(token, questions)
        
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

@instructor_bp.route('/instructor/bulk-assign-skills-with-ai', methods=['POST'])
async def instructor_bulk_assign_skills_with_ai_route():
    """Bulk assign skills with AI for instructors."""
    try:
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
        
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        course_id = data.get('course_id')
        questions = data.get('questions', [])
        
        if not course_id or not questions:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Course ID and questions array are required',
                'statusCode': 400
            }), 400
        
        result = await bulk_assign_skills_with_ai_instructor(token, course_id, questions)
        
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

# Skill Matrix Management
@instructor_bp.route('/instructor/skill-matrix/create', methods=['POST'])
async def instructor_create_skill_matrix_route():
    """Create skill matrix for a course."""
    try:
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
        
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        course_id = data.get('course_id')
        matrix_name = data.get('matrix_name')
        skills = data.get('skills', [])
        
        if not course_id or not matrix_name:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Course ID and matrix name are required',
                'statusCode': 400
            }), 400
        
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

@instructor_bp.route('/instructor/skill-matrix/<course_id>', methods=['GET'])
async def instructor_get_skill_matrix_route(course_id):
    """Get skill matrix for a course."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
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

@instructor_bp.route('/instructor/skill-matrix/<matrix_id>', methods=['PUT'])
async def instructor_update_skill_matrix_route(matrix_id):
    """Update skill matrix."""
    try:
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
        
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        skills = data.get('skills', [])
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

# Advanced Analytics
@instructor_bp.route('/instructor/analytics/risk-assessment/<course_id>', methods=['GET'])
async def instructor_risk_assessment_route(course_id):
    """Get risk assessment analytics for a course."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        # Get query parameters
        time_range = request.args.get('time_range', '30d')
        risk_threshold = request.args.get('risk_threshold', '0.7')
        
        result = await get_course_risk_assessment(token, course_id, time_range, risk_threshold)
        
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

@instructor_bp.route('/instructor/analytics/export/<course_id>', methods=['GET'])
async def instructor_export_analytics_route(course_id):
    """Export analytics data for a course."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        # Get query parameters
        format_type = request.args.get('format', 'json')
        analytics_type = request.args.get('type', 'course')
        time_range = request.args.get('time_range', '30d')
        
        result = await export_course_analytics(token, course_id, format_type, analytics_type, time_range)
        
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

@instructor_bp.route('/instructor/analytics/individual-graphs/<student_id>', methods=['GET'])
async def instructor_individual_graphs_route(student_id):
    """Get individual student graphs and analytics."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401
        
        token = auth_header.split(' ')[1]
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify(user_result), user_result['statusCode']
        
        user = user_result['user']
        if user['role'] != 'instructor' or user['canvasTokenType'] != 'instructor':
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'Instructor access required',
                'statusCode': 403
            }), 403
        
        # Get query parameters
        course_id = request.args.get('course_id')
        graph_type = request.args.get('type', 'progress')
        time_range = request.args.get('time_range', '30d')
        
        if not course_id:
            return jsonify({
                'error': 'Missing required parameters',
                'message': 'Course ID is required',
                'statusCode': 400
            }), 400
        
        result = await get_individual_graphs(token, course_id, student_id, graph_type, time_range)
        
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