# routes/skill_video_routes.py
from quart import Blueprint, request, jsonify
import logging

from services.skill_video_service import (
    get_skill_videos,
    add_skill_video,
    remove_skill_video,
    generate_ai_video_recommendations,
    vote_skill_video,
    find_relevant_moment,
    verify_ai_video,
)
from utils.request_utils import not_text_response

skill_video_bp = Blueprint('skill_video', __name__)
logger = logging.getLogger(__name__)


def _extract_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    return auth_header.split(' ')[1]


def _missing_token_response():
    return jsonify({
        'error': 'Missing token',
        'message': 'Authorization header with Bearer token is required',
        'statusCode': 401
    }), 401


def _all_text(*values):
    """True if every value is a string or missing. These values go into
    database queries, where a JSON object such as {"$ne": null} would act as
    a filter instead of a value."""
    return all(value is None or isinstance(value, str) for value in values)


def _result_response(result, success_status=200):
    if 'error' in result:
        return jsonify({
            'error': result['error'],
            'message': result.get('message', result['error']),
            'statusCode': result.get('statusCode', 500)
        }), result.get('statusCode', 500)
    return jsonify(result), success_status


@skill_video_bp.route('/achieveup/skill-videos/get', methods=['POST'])
async def get_skill_videos_route():
    """Get the curated video list for a skill. (AchieveUp only)"""
    try:
        token = _extract_token()
        if not token:
            return _missing_token_response()

        data = await request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request', 'message': 'Request body is required', 'statusCode': 400}), 400

        course_id = data.get('course_id')
        skill_name = data.get('skill_name')
        matrix_id = data.get('matrix_id')

        if not course_id or not skill_name:
            return jsonify({'error': 'Missing required fields', 'message': 'course_id and skill_name are required', 'statusCode': 400}), 400
        if not _all_text(course_id, skill_name, matrix_id):
            return not_text_response()

        result = await get_skill_videos(token, course_id, skill_name, matrix_id)
        return _result_response(result)

    except Exception as e:
        logger.error(f"get_skill_videos_route error: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500


@skill_video_bp.route('/achieveup/skill-videos', methods=['POST'])
async def add_skill_video_route():
    """Instructor adds a video to a skill's curated list. (AchieveUp only)"""
    try:
        token = _extract_token()
        if not token:
            return _missing_token_response()

        data = await request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request', 'message': 'Request body is required', 'statusCode': 400}), 400

        course_id = data.get('course_id')
        skill_name = data.get('skill_name')
        link = data.get('link')

        if not course_id or not skill_name or not link:
            return jsonify({'error': 'Missing required fields', 'message': 'course_id, skill_name and link are required', 'statusCode': 400}), 400
        if not _all_text(course_id, skill_name, link, data.get('matrix_id'), data.get('title')):
            return not_text_response()

        result = await add_skill_video(
            token, course_id, skill_name, link,
            matrix_id=data.get('matrix_id'),
            title=data.get('title'),
        )
        return _result_response(result, success_status=201)

    except Exception as e:
        logger.error(f"add_skill_video_route error: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500


@skill_video_bp.route('/achieveup/skill-videos/<video_id>', methods=['DELETE'])
async def remove_skill_video_route(video_id):
    """Instructor removes a video from a skill's curated list. (AchieveUp only)"""
    try:
        token = _extract_token()
        if not token:
            return _missing_token_response()

        result = await remove_skill_video(token, video_id)
        return _result_response(result)

    except Exception as e:
        logger.error(f"remove_skill_video_route error: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500


@skill_video_bp.route('/achieveup/skill-videos/suggest', methods=['POST'])
async def suggest_candidate_videos_route():
    """Instructor requests AI-suggested candidate videos for a skill. (AchieveUp only)"""
    try:
        token = _extract_token()
        if not token:
            return _missing_token_response()

        data = await request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request', 'message': 'Request body is required', 'statusCode': 400}), 400

        course_id = data.get('course_id')
        skill_name = data.get('skill_name')

        if not course_id or not skill_name:
            return jsonify({'error': 'Missing required fields', 'message': 'course_id and skill_name are required', 'statusCode': 400}), 400
        if not _all_text(course_id, skill_name, data.get('matrix_id')):
            return not_text_response()

        result = await generate_ai_video_recommendations(
            token, course_id, skill_name,
            matrix_id=data.get('matrix_id')
        )
        return _result_response(result)

    except Exception as e:
        logger.error(f"suggest_candidate_videos_route error: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500


@skill_video_bp.route('/achieveup/skill-videos/<video_id>/find-moment', methods=['POST'])
async def find_relevant_moment_route(video_id):
    """Instructor opt-in: find the transcript moment most relevant to a
    video, manual or AI-suggested. (AchieveUp only)"""
    try:
        token = _extract_token()
        if not token:
            return _missing_token_response()

        result = await find_relevant_moment(token, video_id)
        return _result_response(result)

    except Exception as e:
        logger.error(f"find_relevant_moment_route error: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500


@skill_video_bp.route('/achieveup/skill-videos/<video_id>/verify', methods=['POST'])
async def verify_ai_video_route(video_id):
    """Instructor marks an AI-suggested video as reviewed/approved. (AchieveUp only)"""
    try:
        token = _extract_token()
        if not token:
            return _missing_token_response()

        result = await verify_ai_video(token, video_id)
        return _result_response(result)

    except Exception as e:
        logger.error(f"verify_ai_video_route error: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500


@skill_video_bp.route('/achieveup/skill-videos/vote', methods=['POST'])
async def vote_skill_video_route():
    """Student rates whether a video was helpful for a skill. (AchieveUp only)"""
    try:
        token = _extract_token()
        if not token:
            return _missing_token_response()

        data = await request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request', 'message': 'Request body is required', 'statusCode': 400}), 400

        video_id = data.get('video_id')
        vote_type = data.get('vote_type')

        if not video_id or not vote_type:
            return jsonify({'error': 'Missing required fields', 'message': 'video_id and vote_type are required', 'statusCode': 400}), 400
        if not _all_text(video_id, vote_type):
            return not_text_response()

        result = await vote_skill_video(token, video_id, vote_type)
        return _result_response(result)

    except Exception as e:
        logger.error(f"vote_skill_video_route error: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred', 'statusCode': 500}), 500
