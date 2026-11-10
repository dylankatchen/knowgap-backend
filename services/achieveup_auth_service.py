# services/achieveup_auth_service.py

import jwt
import bcrypt
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pymongo.errors import DuplicateKeyError
from config import Config
import re

from mongodb import get_db

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup for AchieveUp users (separate from KnowGap)
db = get_db()

achieveup_users_collection = db[Config.ACHIEVEUP_USERS_COLLECTION]

# JWT configuration
JWT_SECRET = Config.ACHIEVEUP_JWT_SECRET
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24


def create_jwt_token(user_id: str, email: str, role: str, canvas_token_type: str = 'student') -> str:
    """Create a JWT token for a user with Canvas token type."""
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'canvas_token_type': canvas_token_type,
        'exp': datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.now(timezone.utc).replace(tzinfo=None)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def password_meets_requirements(password: str) -> str | None:
    """Function to validate a password is at least 8 characters and contains a number, lowercase and capital letter."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r'[A-Z]', password):
        return "Password must contain at least one capital letter."
    if not re.search(r'[a-z]', password):
        return "Password must contain at least one lowercase letter."
    if not re.search(r'\d', password):
        return "Password must contain at least one number."
    return None

async def achieveup_signup(name: str, email: str, password: str, canvas_api_token: str = None, canvas_token_type: str = None) -> dict:
    """User registration with email/password and mandatory Canvas API token."""
    try:
        # Check if user already exists
        existing_user = await achieveup_users_collection.find_one({'email': email})
        if existing_user:
            return {
                'error': 'User already exists',
                'message': 'A user with this email already exists',
                'statusCode': 409
            }
        
        # Validate the password meets the expected password requirements.
        password_check: str | None = password_meets_requirements(password)
        if password_check:
            return {
                "error": "Password does not meet requirements.",
                "message": password_check,
                "statusCode": 400
            }
        
        # Hash password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        # A Canvas API token is mandatory — no account without one.
        if not canvas_api_token:
            return {
                'error': 'Canvas API token required',
                'message': 'A Canvas API token is required to create an account.',
                'statusCode': 400
            }

        if len(canvas_api_token) < 64:
            return {
                'error': 'Invalid token format',
                'message': 'Canvas API tokens are typically 64+ characters long.',
                'statusCode': 400
            }

        # role/canvas_token_type are never trusted from client input — only ever
        # set below, as a direct result of what Canvas itself confirms. Always
        # try instructor first; a real teaching-enrolled token should grant
        # instructor access automatically, no hint needed. Fall back to
        # confirming it's at least a valid student token; reject otherwise.
        from services.achieveup_canvas_service import validate_canvas_token, get_token_expiration

        instructor_check = await validate_canvas_token(canvas_api_token, 'instructor')
        if instructor_check['valid']:
            role = canvas_token_type = 'instructor'
            validated_check = instructor_check
            # Same account may also carry a real student enrollment somewhere
            # (Canvas roles are per-course, not per-user). Check informationally
            # so a dual-enrolled instructor can later toggle to a student view.
            student_check = await validate_canvas_token(canvas_api_token, 'student')
            has_student_access = bool(student_check['valid'])
        else:
            student_check = await validate_canvas_token(canvas_api_token, 'student')
            if not student_check['valid']:
                return {
                    'error': 'Invalid Canvas token',
                    'message': student_check['message'],
                    'statusCode': 400
                }
            role = canvas_token_type = 'student'
            validated_check = student_check
            has_student_access = False

        # Create user document
        user_id = str(uuid.uuid4())
        user_doc = {
            'user_id': user_id,
            'name': name,
            'email': email,
            'password': hashed_password.decode('utf-8'),
            'role': role,
            'canvas_token_type': canvas_token_type,
            'canvas_student_id': validated_check.get('user_info', {}).get('id'),
            'has_student_access': has_student_access,
            'created_at': datetime.now(timezone.utc).replace(tzinfo=None),
            'updated_at': datetime.now(timezone.utc).replace(tzinfo=None)
        }

        # Store the validated token (encrypted)
        from utils.encryption_utils import encrypt_token
        encrypted_token = encrypt_token(bytes.fromhex(Config.HEX_ENCRYPTION_KEY), canvas_api_token)
        user_doc['canvas_api_token'] = encrypted_token
        user_doc['canvas_token_created_at'] = datetime.now(timezone.utc).replace(tzinfo=None)
        user_doc['canvas_token_last_validated'] = datetime.now(timezone.utc).replace(tzinfo=None)

        # Get the expiration date for the token.
        expiration_status, expiration_date = await get_token_expiration(canvas_api_token)
        if expiration_status == 200:
            user_doc["canvas_token_expiration"] = expiration_date

        # Insert user into database. A DuplicateKeyError here means another
        # request won the race between the find_one check above and this
        # insert (both requests passed the check before either wrote) - the
        # unique index on email is the real guarantee, this just turns that
        # into a clean 409 instead of an unhandled 500.
        try:
            await achieveup_users_collection.insert_one(user_doc)
        except DuplicateKeyError:
            return {
                'error': 'User already exists',
                'message': 'A user with this email already exists',
                'statusCode': 409
            }

        # Generate JWT token
        token = create_jwt_token(user_id, email, role, canvas_token_type)

        # Return user info (without password and Canvas token)
        user_info = {
            'id': user_id,
            'name': name,
            'email': email,
            'role': role,
            'hasCanvasToken': True,
            'canvasTokenType': canvas_token_type,
            'canvas_student_id': user_doc['canvas_student_id'],
            'has_student_access': has_student_access
        }

        return {
            'token': token,
            'user': user_info
        }

    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def achieveup_login(email: str, password: str) -> dict:
    """User login with email/password."""
    try:
        # Find user by email
        user = await achieveup_users_collection.find_one({'email': email})
        if not user:
            return {
                'error': 'Invalid credentials',
                'message': 'Invalid email or password',
                'statusCode': 401
            }
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return {
                'error': 'Invalid credentials',
                'message': 'Invalid email or password',
                'statusCode': 401
            }
        
        # Generate JWT token with Canvas token type
        token = create_jwt_token(
            user['user_id'], 
            user['email'], 
            user['role'], 
            user.get('canvas_token_type', 'student')
        )
        
        # Return user info (without password and Canvas token)
        user_info = {
            'id': user['user_id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'hasCanvasToken': bool(user.get('canvas_api_token')),
            'canvasTokenType': user.get('canvas_token_type', 'student'),
            'canvas_student_id': user.get('canvas_student_id'),
            'has_student_access': user.get('has_student_access', False)
        }

        return {
            'token': token,
            'user': user_info
        }

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def achieveup_verify_token(token: str) -> dict:
    """Verify JWT token and return user information."""
    try:
        # Decode JWT token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        user_id = payload.get('user_id')
        email = payload.get('email')
        role = payload.get('role')
        
        if not user_id or not email or not role:
            return {
                'error': 'Invalid token',
                'message': 'Token is invalid or expired',
                'statusCode': 401
            }
        
        # Find user in database
        user = await achieveup_users_collection.find_one({'user_id': user_id})
        if not user:
            return {
                'error': 'User not found',
                'message': 'User not found',
                'statusCode': 404
            }
        
        token_expiration = user.get("canvas_token_expiration")
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if token_expiration is None:
            token_status = 'Valid'
        elif token_expiration <= now:
            token_status = 'Expired'
        elif token_expiration <= now + timedelta(days=7):
            token_status = 'Expiring Soon'
        else:
            token_status = 'Valid'

        # Return user info (without password and Canvas token)
        user_info = {
            'id': user['user_id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'hasCanvasToken': bool(user.get('canvas_api_token')),
            'canvasTokenType': user.get('canvas_token_type', 'student'),
            'canvas_student_id': user.get('canvas_student_id'),
            'has_student_access': user.get('has_student_access', False),
            "canvasTokenExpiresAt": token_expiration.isoformat() if token_expiration else None,
            "canvasTokenStatus": token_status
        }

        return {'user': user_info}

    except jwt.ExpiredSignatureError:
        return {
            'error': 'Token expired',
            'message': 'Token has expired',
            'statusCode': 401
        }
    except jwt.InvalidTokenError:
        return {
            'error': 'Invalid token',
            'message': 'Token is invalid',
            'statusCode': 401
        }
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}


async def achieveup_update_profile(token: str, name: str, email: str, canvas_api_token: str = None, canvas_token_type: str = None) -> dict:
    """Update user profile information including Canvas API token."""
    try:
        # Verify token and get user info
        verify_result = await achieveup_verify_token(token)
        if 'error' in verify_result:
            return verify_result
        
        user_id = verify_result['user']['id']
        
        # Check if email is already taken by another user
        if email != verify_result['user']['email']:
            existing_user = await achieveup_users_collection.find_one({'email': email})
            if existing_user and existing_user['user_id'] != user_id:
                return {
                    'error': 'Email already taken',
                    'message': 'This email is already registered by another user',
                    'statusCode': 409
                }
        
        # Prepare update data
        update_data = {
            'name': name,
            'email': email,
            'updated_at': datetime.now(timezone.utc).replace(tzinfo=None)
        }
        
        # Only update Canvas API token if provided
        if canvas_api_token is not None:
            # Validate token format (Canvas tokens are typically 64+ characters)
            if len(canvas_api_token) < 64:
                return {
                    'error': 'Invalid token format',
                    'message': 'Canvas API tokens are typically 64+ characters long.',
                    'statusCode': 400
                }

            # role/canvas_token_type are never trusted from client input here either -
            # same instructor-first-then-student-fallback pattern as signup, so a
            # student can't hand-craft a request claiming canvasTokenType=instructor
            # to get promoted on a token that was never actually verified as one.
            from services.achieveup_canvas_service import validate_canvas_token, get_token_expiration

            instructor_check = await validate_canvas_token(canvas_api_token, 'instructor')
            if instructor_check['valid']:
                token_type = 'instructor'
                validated_check = instructor_check
                student_check = await validate_canvas_token(canvas_api_token, 'student')
                has_student_access = bool(student_check['valid'])
            else:
                student_check = await validate_canvas_token(canvas_api_token, 'student')
                if not student_check['valid']:
                    return {
                        'error': 'Invalid Canvas token',
                        'message': student_check['message'],
                        'statusCode': 400
                    }
                token_type = 'student'
                validated_check = student_check
                has_student_access = False

            # Store the validated token (encrypted)
            from utils.encryption_utils import encrypt_token
            encrypted_token = encrypt_token(bytes.fromhex(Config.HEX_ENCRYPTION_KEY), canvas_api_token)
            update_data['canvas_api_token'] = encrypted_token
            update_data['canvas_token_created_at'] = datetime.now(timezone.utc).replace(tzinfo=None)
            update_data['canvas_token_last_validated'] = datetime.now(timezone.utc).replace(tzinfo=None)
            update_data['canvas_token_type'] = token_type
            update_data['role'] = token_type
            update_data['canvas_student_id'] = validated_check.get('user_info', {}).get('id')
            update_data['has_student_access'] = has_student_access

            expiration_status, expiration_date = await get_token_expiration(canvas_api_token)
            if expiration_status == 200:
                update_data["canvas_token_expiration"] = expiration_date
            else:
                await achieveup_users_collection.update_one({'user_id': user_id}, {'$unset': {'canvas_token_expiration': ''}})


        # Update user in database
        await achieveup_users_collection.update_one(
            {'user_id': user_id},
            {'$set': update_data}
        )
        
        # Get updated user info
        updated_user = await achieveup_users_collection.find_one({'user_id': user_id})
        
        # Return updated user info (without password and Canvas token)
        user_info = {
            'id': updated_user['user_id'],
            'name': updated_user['name'],
            'email': updated_user['email'],
            'role': updated_user['role'],
            'hasCanvasToken': bool(updated_user.get('canvas_api_token')),
            'canvasTokenType': updated_user.get('canvas_token_type', 'student'),
            'canvas_student_id': updated_user.get('canvas_student_id'),
            'has_student_access': updated_user.get('has_student_access', False)
        }

        return {'user': user_info}

    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def achieveup_change_password(token: str, current_password: str, new_password: str) -> dict:
    """Change user password."""
    try:
        # Verify token and get user info
        verify_result = await achieveup_verify_token(token)
        if 'error' in verify_result:
            return verify_result
        
        user_id = verify_result['user']['id']
        
        # Get user from database
        user = await achieveup_users_collection.find_one({'user_id': user_id})
        if not user:
            return {
                'error': 'User not found',
                'message': 'User not found',
                'statusCode': 404
            }

        # Validate the password meets the expected password requirements.
        password_check: str | None = password_meets_requirements(new_password)
        if password_check:
            return {
                "error": "Password does not meet requirements.",
                "message": password_check,
                "statusCode": 400
            }
        
        # Verify current password
        if not bcrypt.checkpw(current_password.encode('utf-8'), user['password'].encode('utf-8')):
            return {
                'error': 'Invalid current password',
                'message': 'Current password is incorrect',
                'statusCode': 400
            }
        
        # Hash new password
        salt = bcrypt.gensalt()
        hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), salt)
        
        # Update password in database
        await achieveup_users_collection.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'password': hashed_new_password.decode('utf-8'),
                    'updated_at': datetime.now(timezone.utc).replace(tzinfo=None)
                }
            }
        )
        
        return {'message': 'Password updated successfully'}
        
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_user_canvas_token(user_id: str) -> str:
    """Get decrypted Canvas API token for a user."""
    try:
        user = await achieveup_users_collection.find_one({'user_id': user_id})
        if user and user.get('canvas_api_token'):
            from utils.encryption_utils import decrypt_token
            return decrypt_token(bytes.fromhex(Config.HEX_ENCRYPTION_KEY), user['canvas_api_token'])
        return None
    except Exception as e:
        logger.error(f"Error getting Canvas token: {str(e)}")
        return None

async def require_instructor(token: str):
    """Verify token and require instructor access. Returns (user, None) or (None, error_dict)."""
    user_result = await achieveup_verify_token(token)
    if 'error' in user_result:
        return None, user_result

    user = user_result['user']
    if user.get('role') != 'instructor' or user.get('canvasTokenType') != 'instructor':
        return None, {
            'error': 'Access denied',
            'message': 'Instructor access required',
            'statusCode': 403
        }
    return user, None
