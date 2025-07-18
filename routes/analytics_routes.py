from quart import Blueprint, request, jsonify
from services.analytics_service import (
    get_course_analytics,
    get_student_comparison,
    get_skill_performance_analytics,
    export_analytics_data,
    get_trend_analytics
)

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics/course/<course_id>', methods=['GET'])
async def get_course_analytics_route(course_id):
    """Get comprehensive analytics for a course. (AchieveUp only)"""
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
        time_range = request.args.get('time_range', '30d')  # 7d, 30d, 90d, 1y
        skill_id = request.args.get('skill_id')
        
        # Call analytics service
        result = await get_course_analytics(token, course_id, time_range, skill_id)
        
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

@analytics_bp.route('/analytics/compare', methods=['GET'])
async def get_student_comparison_route():
    """Get student comparison analytics. (AchieveUp only)"""
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
        comparison_type = request.args.get('type', 'percentile')  # percentile, ranking, distribution
        
        if not course_id:
            return jsonify({
                'error': 'Missing course_id',
                'message': 'Course ID is required',
                'statusCode': 400
            }), 400
        
        # Call analytics service
        result = await get_student_comparison(token, course_id, skill_id, comparison_type)
        
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

@analytics_bp.route('/analytics/skills/<skill_id>/performance', methods=['GET'])
async def get_skill_performance_analytics_route(skill_id):
    """Get detailed performance analytics for a specific skill. (AchieveUp only)"""
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
        time_range = request.args.get('time_range', '30d')
        
        if not course_id:
            return jsonify({
                'error': 'Missing course_id',
                'message': 'Course ID is required',
                'statusCode': 400
            }), 400
        
        # Call analytics service
        result = await get_skill_performance_analytics(token, skill_id, course_id, time_range)
        
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

@analytics_bp.route('/analytics/trends', methods=['GET'])
async def get_trend_analytics_route():
    """Get trend analytics across multiple courses or skills. (AchieveUp only)"""
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
        course_ids = request.args.get('course_ids')  # comma-separated list
        skill_ids = request.args.get('skill_ids')  # comma-separated list
        time_range = request.args.get('time_range', '90d')
        trend_type = request.args.get('type', 'progress')  # progress, performance, engagement
        
        # Call analytics service
        result = await get_trend_analytics(token, course_ids, skill_ids, time_range, trend_type)
        
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

@analytics_bp.route('/analytics/export', methods=['GET'])
async def export_analytics_data_route():
    """Export analytics data. (AchieveUp only)"""
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
        format_type = request.args.get('format', 'json')  # json, csv, pdf
        analytics_type = request.args.get('type', 'course')  # course, skill, comparison, trends
        
        if not course_id and analytics_type != 'trends':
            return jsonify({
                'error': 'Missing course_id',
                'message': 'Course ID is required for this analytics type',
                'statusCode': 400
            }), 400
        
        # Call analytics service
        result = await export_analytics_data(token, course_id, skill_id, format_type, analytics_type)
        
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

@analytics_bp.route('/analytics/course/<course_id>/students', methods=['GET'])
async def get_course_students_analytics_route(course_id):
    """Get analytics for all students in a course. (AchieveUp only)"""
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
        time_range = request.args.get('time_range', '30d')
        skill_id = request.args.get('skill_id')
        
        # Call analytics service
        from services.analytics_service import get_course_students_analytics
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

@analytics_bp.route('/analytics/course/<course_id>/risk-assessment', methods=['GET'])
async def get_course_risk_assessment_route(course_id):
    """Get risk assessment analytics for a course. (AchieveUp only)"""
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
        time_range = request.args.get('time_range', '30d')
        risk_threshold = request.args.get('risk_threshold', '0.7')
        
        # Call analytics service
        from services.analytics_service import get_course_risk_assessment
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

@analytics_bp.route('/analytics/export/<course_id>', methods=['GET'])
async def export_course_analytics_route(course_id):
    """Export analytics data for a course. (AchieveUp only)"""
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
        format_type = request.args.get('format', 'json')  # json, csv, pdf
        analytics_type = request.args.get('type', 'course')  # course, students, skills
        time_range = request.args.get('time_range', '30d')
        
        # Call analytics service
        from services.analytics_service import export_course_analytics
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

@analytics_bp.route('/analytics/individual-graphs', methods=['GET'])
async def get_individual_graphs_route():
    """Get individual student graphs and analytics. (AchieveUp only)"""
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
        student_id = request.args.get('student_id')
        graph_type = request.args.get('type', 'progress')  # progress, performance, skills
        time_range = request.args.get('time_range', '30d')
        
        if not course_id or not student_id:
            return jsonify({
                'error': 'Missing required parameters',
                'message': 'Course ID and student ID are required',
                'statusCode': 400
            }), 400
        
        # Call analytics service
        from services.analytics_service import get_individual_graphs
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