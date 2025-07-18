from quart import Blueprint, request, jsonify
from services.achieveup_auth_service import (
    achieveup_signup,
    achieveup_login,
    achieveup_verify_token,
    achieveup_get_user_info,
    achieveup_update_profile,
    achieveup_change_password
)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/auth/signup', methods=['POST'])
async def achieveup_signup_route():
    """User registration with email/password and optional Canvas API token. (AchieveUp only)"""
    try:
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        canvas_api_token = data.get('canvasApiToken')
        canvas_token_type = data.get('canvasTokenType')
        
        if not name or not email or not password:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Name, email, and password are required',
                'statusCode': 400
            }), 400
        
        # Call authentication service
        result = await achieveup_signup(name, email, password, canvas_api_token, canvas_token_type)
        
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

@auth_bp.route('/auth/login', methods=['POST'])
async def achieveup_login_route():
    """User login with email/password. Returns JWT token and user object. (AchieveUp only)"""
    try:
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'error': 'Missing credentials',
                'message': 'Email and password are required',
                'statusCode': 400
            }), 400
        
        # Call authentication service
        result = await achieveup_login(email, password)
        
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

@auth_bp.route('/auth/verify', methods=['GET'])
async def achieveup_verify_route():
    """Verify authentication token. Returns user object. (AchieveUp only)"""
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
        
        # Call token verification service
        result = await achieveup_verify_token(token)
        
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

@auth_bp.route('/auth/me', methods=['GET'])
async def achieveup_me_route():
    """Get current user info. (AchieveUp only)"""
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
        
        # First verify the token
        verify_result = await achieveup_verify_token(token)
        if 'error' in verify_result:
            return jsonify({
                'error': verify_result['error'],
                'message': verify_result['error'],
                'statusCode': verify_result['statusCode']
            }), verify_result['statusCode']
        
        # Return user info from verification result
        return jsonify(verify_result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@auth_bp.route('/auth/profile', methods=['PUT'])
async def achieveup_update_profile_route():
    """Update user profile information including Canvas API token. (AchieveUp only)"""
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
        
        name = data.get('name')
        email = data.get('email')
        canvas_api_token = data.get('canvasApiToken')
        canvas_token_type = data.get('canvasTokenType')
        
        if not name or not email:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Name and email are required',
                'statusCode': 400
            }), 400
        
        # Call authentication service
        result = await achieveup_update_profile(token, name, email, canvas_api_token, canvas_token_type)
        
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

@auth_bp.route('/auth/validate-canvas-token', methods=['POST'])
async def validate_canvas_token_route():
    """Validate Canvas API token with Canvas API before storing. (AchieveUp only)"""
    try:
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        canvas_api_token = data.get('canvasApiToken')
        canvas_token_type = data.get('canvasTokenType', 'student')
        
        if not canvas_api_token:
            return jsonify({
                'error': 'Missing token',
                'message': 'Canvas API token is required',
                'statusCode': 400
            }), 400
        
        # Validate token format (Canvas tokens are typically 64+ characters)
        if len(canvas_api_token) < 64:
            return jsonify({
                'valid': False,
                'message': 'Invalid token format. Canvas API tokens are typically 64+ characters long.'
            }), 200
        
        # Test token with Canvas API
        from services.achieveup_canvas_service import validate_canvas_token
        validation_result = await validate_canvas_token(canvas_api_token, canvas_token_type)
        
        return jsonify(validation_result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@auth_bp.route('/auth/password', methods=['PUT'])
async def achieveup_change_password_route():
    """Change user password. (AchieveUp only)"""
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
        
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        
        if not current_password or not new_password:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Current password and new password are required',
                'statusCode': 400
            }), 400
        
        # Call authentication service
        result = await achieveup_change_password(token, current_password, new_password)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify({'message': 'Password updated successfully'}), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500 

@auth_bp.route('/auth/token-status', methods=['GET'])
async def token_status_route():
    """Get current token status and validity. (AchieveUp only)"""
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
        
        # Verify the token
        result = await achieveup_verify_token(token)
        
        if 'error' in result:
            return jsonify({
                'valid': False,
                'message': result['error'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        # Token is valid, return status
        return jsonify({
            'valid': True,
            'message': 'Token is valid',
            'user': result['user'],
            'expires_at': result.get('expires_at'),
            'token_type': 'Bearer'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@auth_bp.route('/auth/refresh-token', methods=['POST'])
async def refresh_token_route():
    """Refresh the current authentication token. (AchieveUp only)"""
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
        
        # Verify the current token first
        verify_result = await achieveup_verify_token(token)
        if 'error' in verify_result:
            return jsonify({
                'error': verify_result['error'],
                'message': verify_result['error'],
                'statusCode': verify_result['statusCode']
            }), verify_result['statusCode']
        
        # Generate a new token for the user
        from services.achieveup_auth_service import generate_jwt_token
        user_id = verify_result['user']['id']
        new_token = generate_jwt_token(user_id)
        
        return jsonify({
            'token': new_token,
            'message': 'Token refreshed successfully',
            'user': verify_result['user']
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500 