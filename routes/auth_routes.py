from quart import Blueprint, request, jsonify
from quart_rate_limiter import rate_limit
from pydantic import BaseModel, StrictStr, ValidationError
import logging
from services.achieveup_auth_service import (
    achieveup_signup,
    achieveup_login,
    achieveup_verify_token,
    achieveup_update_profile,
    achieveup_change_password
)
from utils.request_utils import not_text_response
from utils.rate_limits import CREDENTIAL_CHECK_LIMITS, LOGIN_LIMITS, SIGNUP_LIMITS

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)


# Each field must be text or missing. The email goes into a database lookup,
# where a JSON object such as {"$regex": "^a"} would act as a filter instead
# of a value. Missing fields are left to each route's own required check, and
# fields not listed here are ignored.
class SignupRequest(BaseModel):
    name: StrictStr | None = None
    email: StrictStr | None = None
    password: StrictStr | None = None
    canvasApiToken: StrictStr | None = None
    canvasTokenType: StrictStr | None = None


class LoginRequest(BaseModel):
    email: StrictStr | None = None
    password: StrictStr | None = None


class ProfileUpdateRequest(BaseModel):
    name: StrictStr | None = None
    email: StrictStr | None = None
    canvasApiToken: StrictStr | None = None
    canvasTokenType: StrictStr | None = None


class CanvasTokenCheckRequest(BaseModel):
    canvasApiToken: StrictStr | None = None
    canvasTokenType: StrictStr | None = None


def _parse_text_fields(model, data):
    """Return the body as `model`, or None if it isn't an object of text fields."""
    try:
        return model.model_validate(data)
    except ValidationError:
        return None

@auth_bp.route('/auth/signup', methods=['POST'])
@rate_limit(limits=SIGNUP_LIMITS)
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
        
        body = _parse_text_fields(SignupRequest, data)
        if body is None:
            return not_text_response()

        name = body.name
        email = body.email
        password = body.password
        canvas_api_token = body.canvasApiToken
        canvas_token_type = body.canvasTokenType

        if not name or not email or not password or not canvas_api_token:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Name, email, password, and canvas API token are required.',
                'statusCode': 400
            }), 400
        
        # Call authentication service
        result = await achieveup_signup(name, email, password, canvas_api_token, canvas_token_type)
        
        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result['message'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Signup route error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@auth_bp.route('/auth/login', methods=['POST'])
@rate_limit(limits=LOGIN_LIMITS)
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
        
        body = _parse_text_fields(LoginRequest, data)
        if body is None:
            return not_text_response()

        email = body.email
        password = body.password

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
        logger.error(f"Login route error: {str(e)}")
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
        logger.error(f"Get current user route error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@auth_bp.route('/auth/profile', methods=['PUT'])
@rate_limit(limits=CREDENTIAL_CHECK_LIMITS)
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
        
        body = _parse_text_fields(ProfileUpdateRequest, data)
        if body is None:
            return not_text_response()

        name = body.name
        email = body.email
        canvas_api_token = body.canvasApiToken
        canvas_token_type = body.canvasTokenType

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
        logger.error(f"Update profile route error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@auth_bp.route('/auth/validate-canvas-token', methods=['POST'])
@rate_limit(limits=CREDENTIAL_CHECK_LIMITS)
async def validate_canvas_token_route():
    """Check a Canvas API token before saving it in Settings. Needs a login,
    and each user's checks are rate limited. (AchieveUp only)"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401

        verify_result = await achieveup_verify_token(auth_header.split(' ')[1])
        if 'error' in verify_result:
            return jsonify({
                'error': verify_result['error'],
                'message': verify_result['error'],
                'statusCode': verify_result['statusCode']
            }), verify_result['statusCode']

        data = await request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        body = _parse_text_fields(CanvasTokenCheckRequest, data)
        if body is None:
            return not_text_response()

        canvas_api_token = body.canvasApiToken
        canvas_token_type = body.canvasTokenType or 'student'
        
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

        # Only the verdict: the token owner's Canvas name, email and ID stay
        # on the server.
        return jsonify({
            'valid': validation_result.get('valid', False),
            'message': validation_result.get('message')
        }), 200
        
    except Exception as e:
        logger.error(f"Validate Canvas token route error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@auth_bp.route('/auth/password', methods=['PUT'])
@rate_limit(limits=CREDENTIAL_CHECK_LIMITS)
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
                'message': result['message'],
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify({'message': 'Password updated successfully'}), 200
        
    except Exception as e:
        logger.error(f"Change password route error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500 
