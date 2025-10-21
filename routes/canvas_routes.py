from quart import Blueprint, request, jsonify
from services.achieveup_canvas_service import (
    get_canvas_courses,
    get_canvas_course_quizzes,
    get_canvas_quiz_questions
)

canvas_bp = Blueprint('canvas', __name__)

@canvas_bp.route('/canvas/courses', methods=['GET'])
async def achieveup_canvas_courses_route():
    """Get user's Canvas courses. (AchieveUp only)"""
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
        
        # Call Canvas service
        result = await get_canvas_courses(token)
        
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

@canvas_bp.route('/canvas/courses/<course_id>/quizzes', methods=['GET'])
async def achieveup_canvas_course_quizzes_route(course_id):
    """Get quizzes for a specific course. (AchieveUp only)"""
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
        
        # Call Canvas service
        result = await get_canvas_course_quizzes(token, course_id)
        
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

@canvas_bp.route('/canvas/quizzes/<quiz_id>/questions', methods=['GET'])
async def achieveup_canvas_quiz_questions_route(quiz_id):
    """Get questions for a specific quiz. (AchieveUp only)"""
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
        
        # Call Canvas service
        result = await get_canvas_quiz_questions(token, quiz_id)
        
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

@canvas_bp.route('/canvas/test-connection', methods=['GET'])
async def test_canvas_connection_route():
    """Test if stored Canvas API token is still valid. (AchieveUp only)"""
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
        
        # Get user's stored Canvas API token and test it
        from services.achieveup_auth_service import get_user_canvas_token
        from services.achieveup_canvas_service import validate_canvas_token
        
        # First verify the user's JWT token
        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({
                'error': user_result['error'],
                'message': user_result['error'],
                'statusCode': user_result['statusCode']
            }), user_result['statusCode']
        
        user_id = user_result['user']['id']
        
        # Get user's stored Canvas API token
        canvas_token = await get_user_canvas_token(user_id)
        if not canvas_token:
            return jsonify({
                'connected': False,
                'message': 'No Canvas API token found. Please add your Canvas API token in settings.'
            }), 200
        
        # Test the stored token
        validation_result = await validate_canvas_token(canvas_token)
        
        if validation_result['valid']:
            return jsonify({
                'connected': True,
                'message': 'Successfully connected to Canvas',
                'user_info': validation_result.get('user_info')
            }), 200
        else:
            return jsonify({
                'connected': False,
                'message': validation_result['message']
            }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@canvas_bp.route('/canvas/instructor/courses', methods=['GET'])
async def instructor_courses_route():
    """Get all courses taught by the instructor (instructor token required)."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing token', 'message': 'Authorization header with Bearer token is required', 'statusCode': 401}), 401
        token = auth_header.split(' ')[1]
        from services.achieveup_auth_service import achieveup_verify_token, get_user_canvas_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({'error': user_result['error'], 'message': user_result['error'], 'statusCode': user_result['statusCode']}), user_result['statusCode']
        user_id = user_result['user']['id']
        # Check instructor token type
        from motor.motor_asyncio import AsyncIOMotorClient
        from config import Config
        client = AsyncIOMotorClient(
            Config.DB_CONNECTION_STRING,
            tlsAllowInvalidCertificates=(Config.ENV == 'development')
        )
        db = client[Config.DATABASE]
        user_doc = await db[Config.ACHIEVEUP_USERS_COLLECTION].find_one({'user_id': user_id})
        if not user_doc or user_doc.get('canvas_token_type', 'student') != 'instructor':
            return jsonify({'error': 'Forbidden', 'message': 'Instructor token required', 'statusCode': 403}), 403
        canvas_token = await get_user_canvas_token(user_id)
        if not canvas_token:
            return jsonify({'error': 'No Canvas token', 'message': 'No Canvas API token found for user', 'statusCode': 400}), 400
        from services.achieveup_canvas_service import get_instructor_courses
        result = await get_instructor_courses(canvas_token)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500

@canvas_bp.route('/canvas/instructor/courses/<course_id>/quizzes', methods=['GET'])
async def instructor_course_quizzes_route(course_id):
    """Get all quizzes in a course (instructor token required)."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing token', 'message': 'Authorization header with Bearer token is required', 'statusCode': 401}), 401
        token = auth_header.split(' ')[1]
        from services.achieveup_auth_service import achieveup_verify_token, get_user_canvas_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({'error': user_result['error'], 'message': user_result['error'], 'statusCode': user_result['statusCode']}), user_result['statusCode']
        user_id = user_result['user']['id']
        from motor.motor_asyncio import AsyncIOMotorClient
        from config import Config
        client = AsyncIOMotorClient(
            Config.DB_CONNECTION_STRING,
            tlsAllowInvalidCertificates=(Config.ENV == 'development')
        )
        db = client[Config.DATABASE]
        user_doc = await db[Config.ACHIEVEUP_USERS_COLLECTION].find_one({'user_id': user_id})
        if not user_doc or user_doc.get('canvas_token_type', 'student') != 'instructor':
            return jsonify({'error': 'Forbidden', 'message': 'Instructor token required', 'statusCode': 403}), 403
        canvas_token = await get_user_canvas_token(user_id)
        if not canvas_token:
            return jsonify({'error': 'No Canvas token', 'message': 'No Canvas API token found for user', 'statusCode': 400}), 400
        from services.achieveup_canvas_service import get_instructor_course_quizzes
        result = await get_instructor_course_quizzes(canvas_token, course_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500

@canvas_bp.route('/canvas/instructor/quizzes/<quiz_id>/questions', methods=['GET'])
async def instructor_quiz_questions_route(quiz_id):
    """Get all questions in a quiz (instructor token required)."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing token', 'message': 'Authorization header with Bearer token is required', 'statusCode': 401}), 401
        token = auth_header.split(' ')[1]
        from services.achieveup_auth_service import achieveup_verify_token, get_user_canvas_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({'error': user_result['error'], 'message': user_result['error'], 'statusCode': user_result['statusCode']}), user_result['statusCode']
        user_id = user_result['user']['id']
        from motor.motor_asyncio import AsyncIOMotorClient
        from config import Config
        client = AsyncIOMotorClient(
            Config.DB_CONNECTION_STRING,
            tlsAllowInvalidCertificates=(Config.ENV == 'development')
        )
        db = client[Config.DATABASE]
        user_doc = await db[Config.ACHIEVEUP_USERS_COLLECTION].find_one({'user_id': user_id})
        if not user_doc or user_doc.get('canvas_token_type', 'student') != 'instructor':
            return jsonify({'error': 'Forbidden', 'message': 'Instructor token required', 'statusCode': 403}), 403
        canvas_token = await get_user_canvas_token(user_id)
        if not canvas_token:
            return jsonify({'error': 'No Canvas token', 'message': 'No Canvas API token found for user', 'statusCode': 400}), 400
        from services.achieveup_canvas_service import get_instructor_quiz_questions
        result = await get_instructor_quiz_questions(canvas_token, quiz_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500 