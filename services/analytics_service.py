# services/analytics_service.py

import logging
import json
import statistics
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from services.achieveup_auth_service import achieveup_verify_token
from config import Config

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup for AchieveUp analytics data (separate from KnowGap)
client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
db = client[Config.DATABASE]
achieveup_course_analytics_collection = db["AchieveUp_Course_Analytics"]
achieveup_student_analytics_collection = db["AchieveUp_Student_Analytics"]
achieveup_skill_analytics_collection = db["AchieveUp_Skill_Analytics"]

async def get_course_analytics(token: str, course_id: str, time_range: str = '30d', skill_id: str = None) -> dict:
    """Get comprehensive analytics for a course."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = calculate_start_date(time_range, end_date)
        
        # Build query
        query = {
            'course_id': course_id,
            'timestamp': {'$gte': start_date, '$lte': end_date}
        }
        if skill_id:
            query['skill_id'] = skill_id
        
        # Get course analytics data
        analytics_data = []
        async for analytics in achieveup_course_analytics_collection.find(query):
            analytics.pop('_id', None)
            analytics_data.append(analytics)
        
        # Calculate course-wide statistics
        course_stats = calculate_course_statistics(analytics_data)
        
        # Get skill breakdown
        skill_breakdown = await get_skill_breakdown(course_id, start_date, end_date, skill_id)
        
        # Get performance trends
        performance_trends = calculate_performance_trends(analytics_data)
        
        # Get student engagement metrics
        engagement_metrics = await get_engagement_metrics(course_id, start_date, end_date)
        
        return {
            'course_id': course_id,
            'time_range': time_range,
            'course_statistics': course_stats,
            'skill_breakdown': skill_breakdown,
            'performance_trends': performance_trends,
            'engagement_metrics': engagement_metrics,
            'data_points': len(analytics_data)
        }
        
    except Exception as e:
        logger.error(f"Get course analytics error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_student_comparison(token: str, course_id: str, skill_id: str = None, comparison_type: str = 'percentile') -> dict:
    """Get student comparison analytics."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        
        # Build query
        query = {'course_id': course_id}
        if skill_id:
            query['skill_id'] = skill_id
        
        # Get all student data for comparison
        student_data = []
        async for student in achieveup_student_analytics_collection.find(query):
            student.pop('_id', None)
            student_data.append(student)
        
        if not student_data:
            return {
                'error': 'No data available',
                'message': 'No student data found for comparison',
                'statusCode': 404
            }
        
        # Calculate comparison based on type
        if comparison_type == 'percentile':
            comparison_result = calculate_percentile_comparison(user_id, student_data)
        elif comparison_type == 'ranking':
            comparison_result = calculate_ranking_comparison(user_id, student_data)
        elif comparison_type == 'distribution':
            comparison_result = calculate_distribution_comparison(student_data)
        else:
            comparison_result = calculate_percentile_comparison(user_id, student_data)
        
        return {
            'course_id': course_id,
            'skill_id': skill_id,
            'comparison_type': comparison_type,
            'comparison_data': comparison_result,
            'total_students': len(student_data)
        }
        
    except Exception as e:
        logger.error(f"Get student comparison error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_skill_performance_analytics(token: str, skill_id: str, course_id: str, time_range: str = '30d') -> dict:
    """Get detailed performance analytics for a specific skill."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = calculate_start_date(time_range, end_date)
        
        # Build query
        query = {
            'skill_id': skill_id,
            'course_id': course_id,
            'timestamp': {'$gte': start_date, '$lte': end_date}
        }
        
        # Get skill analytics data
        skill_data = []
        async for analytics in achieveup_skill_analytics_collection.find(query):
            analytics.pop('_id', None)
            skill_data.append(analytics)
        
        if not skill_data:
            return {
                'error': 'No data available',
                'message': 'No skill data found',
                'statusCode': 404
            }
        
        # Calculate skill-specific statistics
        skill_stats = calculate_skill_statistics(skill_data)
        
        # Get performance over time
        performance_over_time = calculate_performance_over_time(skill_data)
        
        # Get difficulty analysis
        difficulty_analysis = calculate_difficulty_analysis(skill_data)
        
        # Get learning recommendations
        learning_recommendations = generate_skill_recommendations(skill_stats)
        
        return {
            'skill_id': skill_id,
            'course_id': course_id,
            'time_range': time_range,
            'skill_statistics': skill_stats,
            'performance_over_time': performance_over_time,
            'difficulty_analysis': difficulty_analysis,
            'learning_recommendations': learning_recommendations,
            'data_points': len(skill_data)
        }
        
    except Exception as e:
        logger.error(f"Get skill performance analytics error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_trend_analytics(token: str, course_ids: str = None, skill_ids: str = None, time_range: str = '90d', trend_type: str = 'progress') -> dict:
    """Get trend analytics across multiple courses or skills."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = calculate_start_date(time_range, end_date)
        
        # Parse course and skill IDs
        course_id_list = course_ids.split(',') if course_ids else []
        skill_id_list = skill_ids.split(',') if skill_ids else []
        
        # Build query
        query = {
            'timestamp': {'$gte': start_date, '$lte': end_date}
        }
        
        if course_id_list:
            query['course_id'] = {'$in': course_id_list}
        if skill_id_list:
            query['skill_id'] = {'$in': skill_id_list}
        
        # Get trend data based on type
        if trend_type == 'progress':
            trend_data = await get_progress_trends(query)
        elif trend_type == 'performance':
            trend_data = await get_performance_trends(query)
        elif trend_type == 'engagement':
            trend_data = await get_engagement_trends(query)
        else:
            trend_data = await get_progress_trends(query)
        
        # Calculate trend analysis
        trend_analysis = analyze_trends(trend_data, trend_type)
        
        return {
            'trend_type': trend_type,
            'time_range': time_range,
            'course_ids': course_id_list,
            'skill_ids': skill_id_list,
            'trend_data': trend_data,
            'trend_analysis': trend_analysis
        }
        
    except Exception as e:
        logger.error(f"Get trend analytics error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def export_analytics_data(token: str, course_id: str = None, skill_id: str = None, format_type: str = 'json', analytics_type: str = 'course') -> dict:
    """Export analytics data."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        
        # Get analytics data based on type
        if analytics_type == 'course':
            data = await get_course_analytics_data(course_id, skill_id)
        elif analytics_type == 'skill':
            data = await get_skill_analytics_data(course_id, skill_id)
        elif analytics_type == 'comparison':
            data = await get_comparison_analytics_data(course_id, skill_id)
        elif analytics_type == 'trends':
            data = await get_trends_analytics_data()
        else:
            data = await get_course_analytics_data(course_id, skill_id)
        
        # Format data based on export type
        if format_type == 'csv':
            export_data = format_analytics_csv(data)
            content_type = 'text/csv'
        elif format_type == 'pdf':
            export_data = format_analytics_pdf(data)
            content_type = 'application/pdf'
        else:  # json
            export_data = json.dumps(data, default=str)
            content_type = 'application/json'
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"achieveup_analytics_{analytics_type}_{timestamp}.{format_type}"
        
        return {
            'data': export_data,
            'filename': filename,
            'content_type': content_type,
            'format': format_type,
            'analytics_type': analytics_type,
            'record_count': len(data) if isinstance(data, list) else 1
        }
        
    except Exception as e:
        logger.error(f"Export analytics data error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

# Helper functions
def calculate_start_date(time_range: str, end_date: datetime) -> datetime:
    """Calculate start date based on time range."""
    if time_range == '7d':
        return end_date - timedelta(days=7)
    elif time_range == '30d':
        return end_date - timedelta(days=30)
    elif time_range == '90d':
        return end_date - timedelta(days=90)
    elif time_range == '1y':
        return end_date - timedelta(days=365)
    else:
        return end_date - timedelta(days=30)

def calculate_course_statistics(analytics_data: list) -> dict:
    """Calculate course-wide statistics."""
    if not analytics_data:
        return {}
    
    progress_values = [a.get('progress_percentage', 0) for a in analytics_data]
    
    return {
        'average_progress': round(statistics.mean(progress_values), 2),
        'median_progress': round(statistics.median(progress_values), 2),
        'min_progress': min(progress_values),
        'max_progress': max(progress_values),
        'total_attempts': len(analytics_data),
        'completion_rate': round(len([p for p in progress_values if p >= 100]) / len(progress_values) * 100, 2)
    }

async def get_skill_breakdown(course_id: str, start_date: datetime, end_date: datetime, skill_id: str = None) -> list:
    """Get skill breakdown for a course."""
    # This would aggregate data by skill
    # For now, return mock data
    return [
        {
            'skill_id': 'skill_1',
            'skill_name': 'Problem Solving',
            'average_progress': 75.5,
            'total_attempts': 150,
            'completion_rate': 60.0
        },
        {
            'skill_id': 'skill_2',
            'skill_name': 'Critical Thinking',
            'average_progress': 68.2,
            'total_attempts': 120,
            'completion_rate': 45.0
        }
    ]

def calculate_performance_trends(analytics_data: list) -> dict:
    """Calculate performance trends over time."""
    if not analytics_data:
        return {}
    
    # Group by date and calculate averages
    daily_averages = {}
    for data in analytics_data:
        date = data.get('timestamp', datetime.utcnow()).date()
        if date not in daily_averages:
            daily_averages[date] = []
        daily_averages[date].append(data.get('progress_percentage', 0))
    
    # Calculate daily averages
    trends = []
    for date, values in sorted(daily_averages.items()):
        trends.append({
            'date': date.isoformat(),
            'average_progress': round(statistics.mean(values), 2),
            'attempts': len(values)
        })
    
    return {'daily_trends': trends}

async def get_engagement_metrics(course_id: str, start_date: datetime, end_date: datetime) -> dict:
    """Get student engagement metrics."""
    # This would calculate engagement metrics
    # For now, return mock data
    return {
        'active_students': 45,
        'average_session_duration': 25.5,
        'total_sessions': 180,
        'engagement_score': 78.2
    }

def calculate_percentile_comparison(user_id: str, student_data: list) -> dict:
    """Calculate percentile comparison for a user."""
    if not student_data:
        return {}
    
    # Find user's data
    user_data = next((s for s in student_data if s.get('user_id') == user_id), None)
    if not user_data:
        return {'error': 'User data not found'}
    
    user_progress = user_data.get('progress_percentage', 0)
    
    # Calculate percentile
    all_progress = [s.get('progress_percentage', 0) for s in student_data]
    all_progress.sort()
    
    percentile = 0
    for i, progress in enumerate(all_progress):
        if progress >= user_progress:
            percentile = (i / len(all_progress)) * 100
            break
    
    return {
        'user_progress': user_progress,
        'percentile': round(percentile, 1),
        'total_students': len(student_data),
        'rank': len([p for p in all_progress if p > user_progress]) + 1
    }

def calculate_ranking_comparison(user_id: str, student_data: list) -> dict:
    """Calculate ranking comparison for a user."""
    if not student_data:
        return {}
    
    # Sort by progress percentage
    sorted_data = sorted(student_data, key=lambda x: x.get('progress_percentage', 0), reverse=True)
    
    # Find user's rank
    user_rank = 0
    for i, student in enumerate(sorted_data):
        if student.get('user_id') == user_id:
            user_rank = i + 1
            break
    
    return {
        'user_rank': user_rank,
        'total_students': len(sorted_data),
        'top_performers': sorted_data[:5],
        'user_data': next((s for s in student_data if s.get('user_id') == user_id), None)
    }

def calculate_distribution_comparison(student_data: list) -> dict:
    """Calculate distribution comparison."""
    if not student_data:
        return {}
    
    progress_values = [s.get('progress_percentage', 0) for s in student_data]
    
    return {
        'distribution': {
            '0-25%': len([p for p in progress_values if 0 <= p < 25]),
            '25-50%': len([p for p in progress_values if 25 <= p < 50]),
            '50-75%': len([p for p in progress_values if 50 <= p < 75]),
            '75-100%': len([p for p in progress_values if 75 <= p <= 100])
        },
        'statistics': {
            'mean': round(statistics.mean(progress_values), 2),
            'median': round(statistics.median(progress_values), 2),
            'std_dev': round(statistics.stdev(progress_values), 2) if len(progress_values) > 1 else 0
        }
    }

def calculate_skill_statistics(skill_data: list) -> dict:
    """Calculate skill-specific statistics."""
    if not skill_data:
        return {}
    
    progress_values = [s.get('progress_percentage', 0) for s in skill_data]
    
    return {
        'average_progress': round(statistics.mean(progress_values), 2),
        'median_progress': round(statistics.median(progress_values), 2),
        'min_progress': min(progress_values),
        'max_progress': max(progress_values),
        'total_attempts': len(skill_data),
        'success_rate': round(len([p for p in progress_values if p >= 70]) / len(progress_values) * 100, 2)
    }

def calculate_performance_over_time(skill_data: list) -> list:
    """Calculate performance over time for a skill."""
    if not skill_data:
        return []
    
    # Group by date
    daily_performance = {}
    for data in skill_data:
        date = data.get('timestamp', datetime.utcnow()).date()
        if date not in daily_performance:
            daily_performance[date] = []
        daily_performance[date].append(data.get('progress_percentage', 0))
    
    # Calculate daily averages
    performance_trend = []
    for date, values in sorted(daily_performance.items()):
        performance_trend.append({
            'date': date.isoformat(),
            'average_progress': round(statistics.mean(values), 2),
            'attempts': len(values)
        })
    
    return performance_trend

def calculate_difficulty_analysis(skill_data: list) -> dict:
    """Calculate difficulty analysis for a skill."""
    if not skill_data:
        return {}
    
    # Analyze question difficulty based on success rates
    difficulty_levels = {
        'easy': 0,
        'medium': 0,
        'hard': 0
    }
    
    for data in skill_data:
        progress = data.get('progress_percentage', 0)
        if progress >= 80:
            difficulty_levels['easy'] += 1
        elif progress >= 50:
            difficulty_levels['medium'] += 1
        else:
            difficulty_levels['hard'] += 1
    
    total = sum(difficulty_levels.values())
    if total > 0:
        difficulty_levels = {k: round(v / total * 100, 2) for k, v in difficulty_levels.items()}
    
    return difficulty_levels

def generate_skill_recommendations(skill_stats: dict) -> list:
    """Generate learning recommendations based on skill statistics."""
    recommendations = []
    
    if not skill_stats:
        return recommendations
    
    avg_progress = skill_stats.get('average_progress', 0)
    success_rate = skill_stats.get('success_rate', 0)
    
    if avg_progress < 50:
        recommendations.append({
            'type': 'focus',
            'message': 'This skill needs more attention. Consider additional practice.',
            'priority': 'high'
        })
    elif avg_progress < 70:
        recommendations.append({
            'type': 'improve',
            'message': 'Good progress, but there\'s room for improvement.',
            'priority': 'medium'
        })
    else:
        recommendations.append({
            'type': 'maintain',
            'message': 'Excellent progress! Keep up the good work.',
            'priority': 'low'
        })
    
    if success_rate < 60:
        recommendations.append({
            'type': 'practice',
            'message': 'Focus on understanding the fundamentals.',
            'priority': 'high'
        })
    
    return recommendations

async def get_progress_trends(query: dict) -> list:
    """Get progress trends data."""
    # This would query the database for progress trends
    # For now, return mock data
    return [
        {'date': '2024-01-01', 'average_progress': 65.2},
        {'date': '2024-01-02', 'average_progress': 68.1},
        {'date': '2024-01-03', 'average_progress': 72.5}
    ]

async def get_performance_trends(query: dict) -> list:
    """Get performance trends data."""
    # Mock data
    return [
        {'date': '2024-01-01', 'performance_score': 75.0},
        {'date': '2024-01-02', 'performance_score': 78.2},
        {'date': '2024-01-03', 'performance_score': 81.5}
    ]

async def get_engagement_trends(query: dict) -> list:
    """Get engagement trends data."""
    # Mock data
    return [
        {'date': '2024-01-01', 'engagement_score': 70.0},
        {'date': '2024-01-02', 'engagement_score': 72.5},
        {'date': '2024-01-03', 'engagement_score': 75.8}
    ]

def analyze_trends(trend_data: list, trend_type: str) -> dict:
    """Analyze trends and provide insights."""
    if not trend_data:
        return {}
    
    # Calculate trend direction
    if len(trend_data) >= 2:
        first_value = trend_data[0].get('average_progress', 0)
        last_value = trend_data[-1].get('average_progress', 0)
        change = last_value - first_value
        
        if change > 5:
            direction = 'increasing'
        elif change < -5:
            direction = 'decreasing'
        else:
            direction = 'stable'
    else:
        direction = 'insufficient_data'
        change = 0
    
    return {
        'trend_direction': direction,
        'change_percentage': round(change, 2),
        'data_points': len(trend_data),
        'trend_type': trend_type
    }

async def get_course_analytics_data(course_id: str, skill_id: str = None) -> list:
    """Get course analytics data for export."""
    # Mock data
    return [
        {'course_id': course_id, 'skill_id': skill_id, 'analytics_type': 'course'}
    ]

async def get_skill_analytics_data(course_id: str, skill_id: str = None) -> list:
    """Get skill analytics data for export."""
    # Mock data
    return [
        {'course_id': course_id, 'skill_id': skill_id, 'analytics_type': 'skill'}
    ]

async def get_comparison_analytics_data(course_id: str, skill_id: str = None) -> list:
    """Get comparison analytics data for export."""
    # Mock data
    return [
        {'course_id': course_id, 'skill_id': skill_id, 'analytics_type': 'comparison'}
    ]

async def get_trends_analytics_data() -> list:
    """Get trends analytics data for export."""
    # Mock data
    return [
        {'analytics_type': 'trends', 'trend_data': 'mock_trend_data'}
    ]

def format_analytics_csv(data: list) -> str:
    """Format analytics data as CSV."""
    if not data:
        return ""
    
    # Create CSV string
    output = []
    if data:
        fieldnames = list(data[0].keys())
        output.append(','.join(fieldnames))
        
        for item in data:
            row = []
            for field in fieldnames:
                value = item.get(field, '')
                if isinstance(value, datetime):
                    value = value.isoformat()
                row.append(str(value))
            output.append(','.join(row))
    
    return '\n'.join(output)

def format_analytics_pdf(data: list) -> str:
    """Format analytics data as PDF (placeholder)."""
    return f"PDF export for {len(data)} analytics records (placeholder)" 