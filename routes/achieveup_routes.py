from quart import Blueprint, request, jsonify
from quart_rate_limiter import rate_limit
import asyncio
from services.achieveup_service import (
    create_skill_matrix,
    update_skill_matrix,
    assign_skills_to_questions,
    get_student_progress,
    get_all_skill_matrices_by_course,
    get_assigned_skills,
    delete_skill_matrix,  # Add new import
    get_course_description,
    upsert_course_description,
    get_course_channels,
    update_course_channels
)
import logging
from utils.rate_limits import PAID_API_LIMITS

# The rate limit counts requests, but analysis makes one OpenAI call per 20
# questions, so an uncapped list would let one request make hundreds of
# calls. Far above any real quiz.
MAX_QUESTIONS_PER_ANALYSIS = 500

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
        matrix_name = data.get('matrix_name')

        # Call service
        result = await update_skill_matrix(token, matrix_id, skills, matrix_name)
        
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


@achieveup_bp.route('/achieveup/matrix/course/<course_id>', methods=['GET'])
async def get_course_skill_matrices_route(course_id):
    """Get ALL skill matrices for a specific course. (AchieveUp only)"""
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
        
        # ADD DETAILED LOGGING FOR DEBUGGING
        logger.info(f"Get course matrices request: course_id={course_id}")
        
        # Call service to get all matrices for this course
        result = await get_all_skill_matrices_by_course(token, course_id)
        
        if 'error' in result:
            logger.error(f"Get course matrices error: {result}")
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result.get('statusCode', 500)
            }), result.get('statusCode', 500)
        
        # Return the matrices array (frontend expects array, not object)
        matrices = result.get('matrices', [])
        logger.info(f"Get course matrices success: {len(matrices)} matrices found for course {course_id}")
        
        return jsonify(matrices), 200
        
    except Exception as e:
        logger.error(f"Get Course Matrices Route Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/course-description/<course_id>', methods=['GET'])
async def get_course_description_route(course_id):
    """Get persisted instructor course description for a course."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401

        token = auth_header.split(' ')[1]
        result = await get_course_description(token, course_id)

        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result.get('statusCode', 500)
            }), result.get('statusCode', 500)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Get course description route error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/course-description/<course_id>', methods=['PUT'])
async def upsert_course_description_route(course_id):
    """Persist instructor course description for a course."""
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

        if not isinstance(data, dict):
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body must be a JSON object',
                'statusCode': 400
            }), 400

        description = data.get('description', '')
        result = await upsert_course_description(token, course_id, description)

        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result.get('statusCode', 500)
            }), result.get('statusCode', 500)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Upsert course description route error: {str(e)}")
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
    
@achieveup_bp.route('/achieveup/skills/assignments', methods=['GET'])
async def get_assigned_skills_route():
    """Get assigned skills. (AchieveUp only)"""
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

        # Read query params
        course_id = request.args.get('course_id')
        question_ids = request.args.getlist('question_id')

        if not course_id or not question_ids:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'course_id and question_id are required',
                'statusCode': 400
            }), 400

        # Call service
        result = await get_assigned_skills(token, course_id, question_ids)

        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result['statusCode']
            }), result['statusCode']

        return jsonify(result), 200

    except Exception:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500


@achieveup_bp.route('/achieveup/badges/student/<student_id>/earned', methods=['GET'])
async def get_student_earned_badges_route(student_id):
    """Get a student's earned badges with course information: all of them for the
    student themself, or one course's (?course_id=) for an instructor of it. (AchieveUp only)"""
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
        course_id = request.args.get('course_id')

        # Call badge service
        from services.badge_service import get_student_earned_badges
        result = await get_student_earned_badges(token, student_id, course_id)

        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result['statusCode']
            }), result['statusCode']
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/public/badges/share/<share_id>/earned', methods=['GET'])
async def get_public_badges_by_share_route(share_id):
    """Get all earned badges for a student's publicly shared badge profile. (AchieveUp only)"""
    try:
        from services.badge_service import get_public_badges_by_share
        # Public by design: access is gated by the unguessable share_id itself,
        # not a token — the student must have explicitly opted in to sharing.
        result = await get_public_badges_by_share(share_id)

        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result.get('statusCode', 500)
            }), result.get('statusCode', 500)
        
        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/badges/share-profile', methods=['POST'])
async def generate_badge_share_link_route():
    """Get or create a badge share link, for the caller's own profile or
    (if the caller is an instructor who teaches them) another student's. (AchieveUp only)"""
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
        data = await request.get_json(silent=True) or {}
        student_id = data.get('student_id')
        course_id = data.get('course_id')

        # Call badge service
        from services.badge_service import generate_badge_share_link
        result = await generate_badge_share_link(token, student_id, course_id)

        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result.get('statusCode', 500)
            }), result.get('statusCode', 500)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/badges/opt-out', methods=['POST'])
async def opt_out_badge_sharing_route():
    """Turn off badge sharing for the caller's own profile (Settings page). (AchieveUp only)"""
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
        from services.badge_service import set_badge_sharing_opt_out
        result = await set_badge_sharing_opt_out(token, True)

        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result.get('statusCode', 500)
            }), result.get('statusCode', 500)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/badges/opt-in', methods=['POST'])
async def opt_in_badge_sharing_route():
    """Turn badge sharing back on for the caller's own profile (Settings page). (AchieveUp only)"""
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
        from services.badge_service import set_badge_sharing_opt_out
        result = await set_badge_sharing_opt_out(token, False)

        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result.get('statusCode', 500)
            }), result.get('statusCode', 500)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/badges/share-status', methods=['GET'])
async def get_badge_share_status_route():
    """Check the caller's own current badge-sharing link and opt-out preference. (AchieveUp only)"""
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
        from services.badge_service import get_badge_share_status
        result = await get_badge_share_status(token)

        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result.get('statusCode', 500)
            }), result.get('statusCode', 500)

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

@achieveup_bp.route('/achieveup/instructor/courses/<course_id>/channels', methods=['GET'])
async def get_channels_endpoint(course_id):
    """
    Retrieve configured YouTube channels for a course.
    """
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
        channels = await get_course_channels(token, course_id)
        if isinstance(channels, dict) and 'error' in channels:
            return jsonify({
                'error': channels['error'],
                'message': channels.get('message', channels['error']),
                'statusCode': channels.get('statusCode', 500)
            }), channels.get('statusCode', 500)

        return jsonify({
            "success": True,
            "course_id": str(course_id),
            "channels": channels
        }), 200
    except Exception as e:
        logger.error(f"Get course channels route error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500


@achieveup_bp.route('/achieveup/instructor/courses/<course_id>/channels', methods=['PUT'])
@rate_limit(limits=PAID_API_LIMITS)
async def update_channels_endpoint(course_id):
    """
    Save or update preferred YouTube channels for a course.
    Expected JSON Body: { "channels": ["@3Blue1Brown", "@freecodecamp"] }
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing token', 'message': 'Authorization header with Bearer token is required', 'statusCode': 401}), 401
        token = auth_header.split(' ')[1]
        data = await request.get_json(silent=True)

        if data is None:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body must be valid JSON.',
                'statusCode': 400
            }), 400

        if not isinstance(data, dict) or "channels" not in data:
            return jsonify({
                'error': 'Invalid request',
                'message': "Missing 'channels' array in request body.",
                'statusCode': 400
            }), 400

        channels_list = data.get("channels", [])
        if not isinstance(channels_list, list):
            return jsonify({
                'error': 'Invalid request',
                'message': ("'channels' must be a list of channel handles "
                            "or IDs."),
                'statusCode': 400
            }), 400

        result = await update_course_channels(token, course_id, channels_list)

        if isinstance(result, dict) and 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result.get('statusCode', 500)
            }), result.get('statusCode', 500)

        return jsonify({
            "success": True,
            "message": "Course channels updated successfully.",
            "course_id": str(course_id),
            "channels": result['channels']
        }), 200

    except Exception as e:
        logger.error(f"Update course channels route error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/instructor/course/<course_id>/force-sync', methods=['POST'])
@rate_limit(limits=PAID_API_LIMITS)
async def instructor_force_sync_route(course_id):
    """Force a data sync for a specific course (instructor only).
    Triggers Canvas submission fetch → mastery update → progress update immediately."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401

        token = auth_header.split(' ')[1]

        # The sync rebuilds the whole course's mastery from what the caller's
        # Canvas token can see, so they must teach (or have taught) the course.
        from services.achieveup_auth_service import get_user_canvas_token
        from services.achieveup_service import require_course_instructor
        user, error = await require_course_instructor(token, course_id, include_concluded=True)
        if error:
            return jsonify(error), error['statusCode']

        # Get the instructor's Canvas token
        canvas_token = await get_user_canvas_token(user['id'])
        if not canvas_token:
            return jsonify({
                'error': 'Canvas token not found',
                'message': 'Please connect your Canvas account in Settings',
                'statusCode': 400
            }), 400

        # Run the sync in the background to avoid Heroku/Netlify timeouts
        # The frontend will be notified that sync has started
        from services.canvas_submissions_service import sync_course_submissions_direct
        asyncio.create_task(sync_course_submissions_direct(canvas_token, course_id))

        return jsonify({
            'message': f'Sync started in background for course {course_id}. This may take a minute.',
            'status': 'processing',
            'details': {
                'total_quizzes': 0,
                'total_synced': 0,
                'progress_synced': 0,
                'total_errors': 0,
                'is_background': True
            }
        }), 202

    except Exception as e:
        logger.error(f"Force sync error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred during sync',
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
        client = AsyncIOMotorClient(
            Config.DB_CONNECTION_STRING,
            tlsAllowInvalidCertificates=(Config.ENV == 'development')
        )
        db = client[Config.DATABASE]
        user_doc = await db[Config.ACHIEVEUP_USERS_COLLECTION].find_one({'user_id': user_id})
        if not user_doc or user_doc.get('canvas_token_type', 'student') != 'instructor':
            return jsonify({'error': 'Forbidden', 'message': 'Instructor token required', 'statusCode': 403}), 403
        from services.achieveup_service import get_instructor_dashboard
        result = await get_instructor_dashboard(token)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500


@achieveup_bp.route('/achieveup/ai/suggest-skills', methods=['POST'])
@rate_limit(limits=PAID_API_LIMITS)
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
@rate_limit(limits=PAID_API_LIMITS)
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
        
        if not data:
            logger.error("No request body received")
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        course_id = data.get('courseId')
        quiz_id = data.get('quizId')
        matrix_id = data.get('matrixId') or data.get('matrix_id')
        questions = data.get('questions', [])
        
        # LOG PARSED DATA
        logger.info(f"Parsed: courseId={course_id}, quizId={quiz_id}, matrixId={matrix_id}, questions_count={len(questions)}")
        
        # RELAXED VALIDATION - Only questions array is truly required
        validation_errors = []
        
        if not questions:
            validation_errors.append("questions array is required")
        elif len(questions) == 0:
            validation_errors.append("questions array cannot be empty")
        elif len(questions) > MAX_QUESTIONS_PER_ANALYSIS:
            validation_errors.append(
                f"questions array cannot have more than {MAX_QUESTIONS_PER_ANALYSIS} questions")
        
        # courseId is checked by the service, which needs it to confirm the
        # caller teaches the course. quizId is optional.
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
                    'matrixId': matrix_id,
                    'questions_count': len(questions) if questions else 0,
                    'questions_sample': questions[:2] if questions else []  # Show first 2 questions for debugging
                },
                'statusCode': 400
            }), 400
        
        # Call the AI service with matrix_id
        from services.achieveup_service import analyze_questions_with_ai
        result = await analyze_questions_with_ai(token, questions, course_id, matrix_id)
        
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
    
@achieveup_bp.route('/achieveup/matrix/delete/<matrix_id>', methods=['DELETE'])
async def delete_skill_matrix_route(matrix_id):
    """Delete a skill matrix. (AchieveUp only)"""
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
        result = await delete_skill_matrix(token, matrix_id)

        if 'error' in result:
            return jsonify({
                'error': result['error'],
                'message': result.get('message', result['error']),
                'statusCode': result.get('statusCode', 500)
            }), result.get('statusCode', 500)

        return jsonify({
            'message': 'Skill matrix deleted successfully',
            'matrix_id': matrix_id
        }), 200

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500

@achieveup_bp.route('/achieveup/matrix/import', methods=['POST'])
async def import_matrices_route():
    """Import all skill matrices from a source course into a target course."""
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

        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({
                'error': user_result['error'],
                'message': user_result['error'],
                'statusCode': user_result['statusCode']
            }), user_result['statusCode']

        # Parse request body
        data = await request.get_json()
        if not data:
            return jsonify({
                'error': 'Bad request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400

        source_course_id = data.get('source_course_id')
        target_course_id = data.get('target_course_id')
        
        if not source_course_id or not target_course_id:
            return jsonify({
                'error': 'Bad request',
                'message': 'source_course_id and target_course_id are required',
                'statusCode': 400
            }), 400

        if source_course_id == target_course_id:
            return jsonify({
                'error': 'Bad request',
                'message': 'Source and target course cannot be the same',
                'statusCode': 400
            }), 400

        from services.achieveup_service import import_matrices_from_course

        result = await import_matrices_from_course(
            source_course_id=source_course_id,
            target_course_id=target_course_id,
            user_id=user_result['user']['id'], token=token
        )

        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), result.get('statusCode', 500)

        return jsonify({
            'message': 'Matrices imported successfully',
            'imported_count': len(result),
            'matrices': result
        }), 200

    except Exception as e:
        logger.error(f"Import matrices route error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500
    
@achieveup_bp.route('/achieveup/skills/import', methods=['POST'])
async def import_skills_assignment_route():
    """Import skill assignments from a source course into a target course."""
    
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401

        token = auth_header.split(' ')[1]

        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return jsonify({
                'error': user_result['error'],
                'message': user_result['error'],
                'statusCode': user_result['statusCode']
            }), user_result['statusCode']

        data = await request.get_json()
        if not data:
            return jsonify({
                'error': 'Bad request',
                'message': 'Request body is required',
                'statusCode': 400
            }), 400
        
        source_course_id = data.get('source_course_id')
        target_course_id = data.get('target_course_id')
        
        if not source_course_id or not target_course_id:
            return jsonify({
                'error': 'Bad request',
                'message': 'source_course_id and target_course_id are required',
                'statusCode': 400
            }), 400

        if source_course_id == target_course_id:
            return jsonify({
                'error': 'Bad request',
                'message': 'Source and target course cannot be the same',
                'statusCode': 400
            }), 400

        from services.achieveup_service import import_skill_setting_from_course

        

        result = await import_skill_setting_from_course(
            source_course_id=source_course_id,
            target_course_id=target_course_id,
            user_id=user_result['user']['id'],
            token=token
        )

        if 'error' in result:
            return jsonify(result), result.get('statusCode', 500)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Import skills route error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500
    
@achieveup_bp.route('/achieveup/import-status/<course_id>', methods=['GET'])
async def get_import_status_route(course_id):
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing token',
                'message': 'Authorization header with Bearer token is required',
                'statusCode': 401
            }), 401

        token = auth_header.split(' ')[1]

        from services.achieveup_service import get_import_status
        result = await get_import_status(token, course_id)

        if 'error' in result:
            return jsonify(result), result.get('statusCode', 500)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Import status route error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'statusCode': 500
        }), 500