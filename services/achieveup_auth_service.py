# services/achieveup_auth_service.py

import jwt
import bcrypt
import logging
import uuid
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup for AchieveUp users (separate from KnowGap)
client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
db = client[Config.DATABASE]
achieveup_users_collection = db["AchieveUp_Users"]

# JWT configuration
JWT_SECRET = getattr(Config, 'ACHIEVEUP_JWT_SECRET', 'achieveup-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

async def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

async def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_jwt_token(user_id: str, email: str, role: str) -> str:
    """Create a JWT token for a user."""
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

async def verify_jwt_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

async def achieveup_signup(name: str, email: str, password: str, canvas_api_token: str = None) -> dict:
    """User registration with email/password and optional Canvas API token."""
    try:
        # Check if user already exists
        existing_user = await achieveup_users_collection.find_one({'email': email})
        if existing_user:
            return {
                'error': 'User already exists',
                'message': 'A user with this email already exists',
                'statusCode': 409
            }
        
        # Hash password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        # Create user document
        user_id = str(uuid.uuid4())
        user_doc = {
            'user_id': user_id,
            'name': name,
            'email': email,
            'password': hashed_password.decode('utf-8'),
            'role': 'student',  # Default role
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Handle Canvas API token if provided
        if canvas_api_token:
            # Validate token format
            if len(canvas_api_token) < 64:
                return {
                    'error': 'Invalid token format',
                    'message': 'Canvas API tokens are typically 64+ characters long.',
                    'statusCode': 400
                }
            
            # Validate token with Canvas API
            from services.achieveup_canvas_service import validate_canvas_token
            validation_result = await validate_canvas_token(canvas_api_token)
            
            if not validation_result['valid']:
                return {
                    'error': 'Invalid Canvas token',
                    'message': validation_result['message'],
                    'statusCode': 400
                }
            
            # Store the validated token
            user_doc['canvas_api_token'] = canvas_api_token
            user_doc['canvas_token_created_at'] = datetime.utcnow()
            user_doc['canvas_token_last_validated'] = datetime.utcnow()
        
        # Insert user into database
        await achieveup_users_collection.insert_one(user_doc)
        
        # Generate JWT token
        token = create_jwt_token(user_id, email, user_doc['role'])
        
        # Return user info (without password and Canvas token)
        user_info = {
            'id': user_id,
            'name': name,
            'email': email,
            'role': user_doc['role'],
            'hasCanvasToken': bool(canvas_api_token)
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
        
        # Generate JWT token
        token = create_jwt_token(user['user_id'], user['email'], user['role'])
        
        # Return user info (without password and Canvas token)
        user_info = {
            'id': user['user_id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'hasCanvasToken': bool(user.get('canvas_api_token'))
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
        
        # Return user info (without password and Canvas token)
        user_info = {
            'id': user['user_id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'hasCanvasToken': bool(user.get('canvas_api_token'))
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

async def achieveup_get_user_info(token: str) -> dict:
    """Get user information from token."""
    return await achieveup_verify_token(token)

async def achieveup_update_profile(token: str, name: str, email: str, canvas_api_token: str = None) -> dict:
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
            'updated_at': datetime.utcnow()
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
            
            # Validate token with Canvas API
            from services.achieveup_canvas_service import validate_canvas_token
            validation_result = await validate_canvas_token(canvas_api_token)
            
            if not validation_result['valid']:
                return {
                    'error': 'Invalid Canvas token',
                    'message': validation_result['message'],
                    'statusCode': 400
                }
            
            # Store the validated token
            update_data['canvas_api_token'] = canvas_api_token
            update_data['canvas_token_created_at'] = datetime.utcnow()
            update_data['canvas_token_last_validated'] = datetime.utcnow()
        
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
            'hasCanvasToken': bool(updated_user.get('canvas_api_token'))
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
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        return {'message': 'Password updated successfully'}
        
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_user_canvas_token(user_id: str) -> str:
    """Get user's Canvas API token (for internal use only)."""
    try:
        user = await achieveup_users_collection.find_one({'user_id': user_id})
        if user and user.get('canvas_api_token'):
            return user['canvas_api_token']
        return None
    except Exception as e:
        logger.error(f"Get Canvas token error: {str(e)}")
        return None 