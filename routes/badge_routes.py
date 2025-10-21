from quart import Blueprint, request, jsonify
from services.badge_service import (
    generate_badges_for_user,
    get_user_badges,
    get_badge_details,
    share_badge,
    get_badge_progress
)

badge_bp = Blueprint('badge', __name__)

@badge_bp.route('/badges/generate', methods=['POST'])
async def generate_badges_route():
    """Generate badges for a user based on their progress. (AchieveUp only)"""
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
        
        # Call badge service
        result = await generate_badges_for_user(token, data)
        
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

@badge_bp.route('/badges/user', methods=['GET'])
async def get_user_badges_route():
    """Get all badges for the current user. (AchieveUp only)"""
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
        
        # Get query parameters
        course_id = request.args.get('course_id')
        skill_id = request.args.get('skill_id')
        
        # Call badge service
        result = await get_user_badges(token, course_id, skill_id)
        
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

@badge_bp.route('/badges/<badge_id>', methods=['GET'])
async def get_badge_details_route(badge_id):
    """Get detailed information about a specific badge. (AchieveUp only)"""
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
        
        # Call badge service
        result = await get_badge_details(token, badge_id)
        
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

@badge_bp.route('/badges/<badge_id>/share', methods=['POST'])
async def share_badge_route(badge_id):
    """Share a badge (generate shareable link). (AchieveUp only)"""
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
        data = await request.get_json() or {}
        
        # Call badge service
        result = await share_badge(token, badge_id, data)
        
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

@badge_bp.route('/badges/progress/<skill_id>', methods=['GET'])
async def get_badge_progress_route(skill_id):
    """Get progress toward earning a badge for a specific skill. (AchieveUp only)"""
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
        
        # Get query parameters
        course_id = request.args.get('course_id')
        
        if not course_id:
            return jsonify({
                'error': 'Missing course_id',
                'message': 'Course ID is required',
                'statusCode': 400
            }), 400
        
        # Call badge service
        result = await get_badge_progress(token, skill_id, course_id)
        
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

@badge_bp.route('/badges/web-linked', methods=['POST'])
async def create_web_linked_badge_route():
    """Create a web-linked badge with shareable URL. (AchieveUp only)"""
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
        
        # Call badge service
        from services.badge_service import create_web_linked_badge
        result = await create_web_linked_badge(token, data)
        
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

@badge_bp.route('/badges/<badge_id>/verify', methods=['GET'])
async def verify_badge_route(badge_id):
    """Verify a badge's authenticity. (AchieveUp only)"""
    try:
        # Get verification code from query parameters
        verification_code = request.args.get('code')
        
        if not verification_code:
            return jsonify({
                'error': 'Missing verification code',
                'message': 'Verification code is required',
                'statusCode': 400
            }), 400
        
        # Call badge service
        from services.badge_service import verify_badge
        result = await verify_badge(badge_id, verification_code)
        
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

@badge_bp.route('/instructor/badges/web-linked', methods=['POST'])
async def instructor_web_linked_badge_route():
    """Create a web-linked badge for instructors. (AchieveUp only)"""
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
        
        # Verify instructor permissions
        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({
                'error': user_result['error'],
                'message': user_result['error'],
                'statusCode': user_result['statusCode']
            }), user_result['statusCode']
        
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
            return jsonify({
                'error': 'Forbidden',
                'message': 'Instructor token required',
                'statusCode': 403
            }), 403
        
        data = await request.get_json()
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        # Call badge service
        from services.badge_service import create_instructor_web_linked_badge
        result = await create_instructor_web_linked_badge(token, data)
        
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