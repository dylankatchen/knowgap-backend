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
client = AsyncIOMotorClient(
        Config.DB_CONNECTION_STRING,
        tlsAllowInvalidCertificates=(Config.ENV == 'development')
    )
db = client[Config.DATABASE]
achieveup_course_analytics_collection = db[Config.ACHIEVEUP_COURSE_ANALYTICS_COLLECTION]
achieveup_student_analytics_collection = db[Config.ACHIEVEUP_STUDENT_ANALYTICS_COLLECTION]
achieveup_skill_analytics_collection = db[Config.ACHIEVEUP_SKILL_ANALYTICS_COLLECTION]

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

async def get_course_students_analytics(token: str, course_id: str, time_range: str = '30d', skill_id: str = None) -> dict:
    """Get comprehensive analytics for all students in a course."""
    try:
        # Verify user token
        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # FIXED: Direct database collection references
        from motor.motor_asyncio import AsyncIOMotorClient
        from config import Config
        import random
        
        client = AsyncIOMotorClient(
        Config.DB_CONNECTION_STRING,
        tlsAllowInvalidCertificates=(Config.ENV == 'development')
    )
        db = client[Config.DATABASE]
        
        # Use explicit collection names
        skill_matrices_collection = db[Config.ACHIEVEUP_SKILL_MATRICES_COLLECTION]
        progress_collection = db[Config.ACHIEVEUP_PROGRESS_COLLECTION]
        
        # Get students for the course
        from services.achieveup_service import get_instructor_course_students
        students_result = await get_instructor_course_students(token, course_id)
        if 'error' in students_result:
            return students_result
        
        students = students_result if isinstance(students_result, list) else []
        
        # Get skill matrix for course
        skill_matrix = await skill_matrices_collection.find_one({'course_id': course_id})
        course_skills = skill_matrix.get('skills', []) if skill_matrix else []
        
        # Fallback: Define skills for each course if not found in database (only if demo mode enabled)
        if not course_skills and Config.ENABLE_DEMO_MODE:
            course_skills_map = {
                "demo_001": ["HTML/CSS Fundamentals", "JavaScript Programming", "DOM Manipulation", "Responsive Design", "Web APIs"],
                "demo_002": ["SQL Fundamentals", "Database Design", "Data Normalization", "Query Optimization", "Stored Procedures"],
                "demo_003": ["Network Protocols (TCP/IP)", "Network Security", "Routing & Switching", "Wireless Networks", "Network Troubleshooting"]
            }
            course_skills = course_skills_map.get(course_id, [])
        
        student_analytics = []
        skill_distribution = {}
        all_skill_scores = {}
        
        for i, student in enumerate(students):
            student_id = student.get('id')
            print(student, 'student')
            
            # Get all progress data for this student
            progress_data = await progress_collection.find({
                'student_id': student_id,
                'course_id': course_id
            }).to_list(length=None)
            
            # If no progress data found, generate realistic demo data (only if demo mode enabled)
            if (not progress_data or len(progress_data) == 0) and Config.ENABLE_DEMO_MODE:
                # Use student ID as seed for consistent random data
                seed_value = hash(student_id) % (2**32)
                rng = random.Random(seed_value)
                
                # Generate realistic skill scores (varied by student)
                base_performance = 0.4 + (i * 0.02)  # Varied student ability
                skill_breakdown = {}
                skill_scores = {}
                skills_mastered = 0
                
                for skill in course_skills:
                    # Generate realistic score with some variation (using seeded random)
                    score = base_performance * 100 + rng.uniform(-20, 30)
                    score = max(15, min(100, score))  # Clamp between 15-100
                    
                    # Determine level
                    if score >= 80:
                        level = "advanced"
                        skills_mastered += 1
                    elif score >= 60:
                        level = "intermediate"
                    else:
                        level = "beginner"
                    
                    # Generate realistic question counts (using seeded random)
                    questions_attempted = rng.randint(2, 8)
                    questions_correct = max(0, int(questions_attempted * (score / 100) + rng.uniform(-1, 1)))
                    questions_correct = min(questions_attempted, questions_correct)
                    
                    skill_breakdown[skill] = {
                        "score": round(score, 1),
                        "level": level,
                        "questionsAttempted": questions_attempted,
                        "questionsCorrect": questions_correct
                    }
                    
                    skill_scores[skill] = score
                    
                    # Track distribution
                    if skill not in skill_distribution:
                        skill_distribution[skill] = 0
                        all_skill_scores[skill] = []
                    skill_distribution[skill] += 1
                    all_skill_scores[skill].append(score)
                
                # Calculate overall metrics
                overall_progress = round(sum(skill_scores.values()) / len(skill_scores), 1) if skill_scores else 0
                badges_earned = skills_mastered + (len([s for s in skill_breakdown.values() if s["level"] == "intermediate"]))
                
                if overall_progress >= 75:
                    risk_level = 'low'
                elif overall_progress >= 50:
                    risk_level = 'medium'
                else:
                    risk_level = 'high'
                
                analytics = {
                    'id': student_id,
                    'name': student.get('name', 'Unknown'),
                    'progress': overall_progress,
                    'skillsMastered': skills_mastered,
                    'badgesEarned': badges_earned,
                    'riskLevel': risk_level,
                    'skillBreakdown': skill_breakdown
                }
                student_analytics.append(analytics)
                continue
            
            # Process actual progress data from database
            skill_breakdown = {}
            skill_scores = {}
            total_questions_attempted = 0
            total_questions_correct = 0
            skills_mastered = 0
            
            for skill in course_skills:
                skill_progress = [p for p in progress_data if p.get('skill') == skill]
                if skill_progress:
                    # Get the latest progress for this skill
                    latest_progress = max(skill_progress, key=lambda x: x.get('updated_at', datetime.min))
                    
                    score = latest_progress.get('score', 0)
                    level = latest_progress.get('level', 'beginner')
                    questions_attempted = latest_progress.get('questions_attempted', 0)
                    questions_correct = latest_progress.get('questions_correct', 0)
                    
                    skill_breakdown[skill] = {
                        "score": round(score, 1),
                        "level": level,
                        "questionsAttempted": questions_attempted,
                        "questionsCorrect": questions_correct
                    }
                    
                    skill_scores[skill] = score
                    total_questions_attempted += questions_attempted
                    total_questions_correct += questions_correct
                    
                    # Count skills mastered (score >= 80)
                    if score >= 80:
                        skills_mastered += 1
                    
                    # Track skill distribution
                    if skill not in skill_distribution:
                        skill_distribution[skill] = 0
                        all_skill_scores[skill] = []
                    skill_distribution[skill] += 1
                    all_skill_scores[skill].append(score)
                else:
                    skill_breakdown[skill] = {
                        "score": 0,
                        "level": "beginner", 
                        "questionsAttempted": 0,
                        "questionsCorrect": 0
                    }
                    skill_scores[skill] = 0
                    
                    # Still track for distribution
                    if skill not in skill_distribution:
                        skill_distribution[skill] = 0
                        all_skill_scores[skill] = []
                    skill_distribution[skill] += 1
                    all_skill_scores[skill].append(0)
            
            # Calculate overall progress
            overall_progress = round(sum(skill_scores.values()) / len(skill_scores), 1) if skill_scores else 0
            
            # Calculate risk level
            if overall_progress >= 75:
                risk_level = 'low'
            elif overall_progress >= 50:
                risk_level = 'medium'
            else:
                risk_level = 'high'
            
            # Calculate badges (simple logic: 1 badge per skill at intermediate, 2 per advanced)
            badges_earned = 0
            for skill_data in skill_breakdown.values():
                if skill_data["level"] == "intermediate":
                    badges_earned += 1
                elif skill_data["level"] == "advanced":
                    badges_earned += 2
            
            analytics = {
                'id': student_id,
                'name': student.get('name', 'Unknown'),
                'progress': overall_progress,
                'skillsMastered': skills_mastered,
                'badgesEarned': badges_earned,
                'riskLevel': risk_level,
                'skillBreakdown': skill_breakdown
            }
            student_analytics.append(analytics)
        
        # Calculate average scores for each skill
        average_scores = {}
        for skill, scores in all_skill_scores.items():
            if scores:
                average_scores[skill] = round(sum(scores) / len(scores), 1)
            else:
                average_scores[skill] = 0
        
        # Format response according to frontend requirements
        response = {
            'analytics': {
                'students': student_analytics,
                'skillDistribution': skill_distribution,
                'averageScores': average_scores
            }
        }
        
        # Close database connection
        client.close()
        
        return response
        
    except Exception as e:
        logger.error(f"Get course students analytics error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_course_risk_assessment(token: str, course_id: str, time_range: str = '30d', risk_threshold: str = '0.7') -> dict:
    """Get risk assessment analytics for a course."""
    try:
        # Verify user token
        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get student analytics first
        analytics_result = await get_course_students_analytics(token, course_id, time_range)
        if 'error' in analytics_result:
            return analytics_result
        
        student_analytics = analytics_result['analytics']['students']
        threshold = float(risk_threshold)
        
        # Identify at-risk students
        high_risk_students = [s for s in student_analytics if s['riskLevel'] == 'high']
        medium_risk_students = [s for s in student_analytics if s['riskLevel'] == 'medium']
        
        # Analyze risk factors
        risk_factors = analyze_risk_factors(student_analytics, threshold)
        
        # Generate recommendations
        recommendations = generate_risk_recommendations(high_risk_students, medium_risk_students, risk_factors)
        
        # Calculate trend data
        trend_data = await calculate_risk_trends(course_id, time_range)
        
        return {
            'courseId': course_id,
            'timeRange': time_range,
            'riskThreshold': threshold,
            'summary': {
                'totalStudents': len(student_analytics),
                'highRiskCount': len(high_risk_students),
                'mediumRiskCount': len(medium_risk_students),
                'lowRiskCount': len([s for s in student_analytics if s['riskLevel'] == 'low']),
                'overallRiskPercentage': round((len(high_risk_students) + len(medium_risk_students)) / len(student_analytics) * 100, 1) if student_analytics else 0
            },
            'highRiskStudents': high_risk_students,
            'mediumRiskStudents': medium_risk_students,
            'riskFactors': risk_factors,
            'recommendations': recommendations,
            'trendData': trend_data,
            'generatedAt': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get course risk assessment error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def export_course_analytics(token: str, course_id: str, format_type: str = 'json', analytics_type: str = 'course', time_range: str = '30d') -> dict:
    """Export analytics data for a course in various formats."""
    try:
        # Verify user token
        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get appropriate analytics data
        if analytics_type == 'students':
            data = await get_course_students_analytics(token, course_id, time_range)
        elif analytics_type == 'risk':
            data = await get_course_risk_assessment(token, course_id, time_range)
        else:  # course
            data = await get_course_analytics(token, course_id, time_range)
        
        if 'error' in data:
            return data
        
        # Export based on format
        if format_type == 'csv':
            exported_data = export_to_csv(data, analytics_type)
        elif format_type == 'pdf':
            exported_data = await export_to_pdf(data, analytics_type)
        else:  # json
            exported_data = {
                'format': 'json',
                'data': data,
                'filename': f"course_{course_id}_{analytics_type}_{time_range}.json"
            }
        
        return {
            'courseId': course_id,
            'exportType': analytics_type,
            'format': format_type,
            'timeRange': time_range,
            'exportData': exported_data,
            'generatedAt': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Export course analytics error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_individual_graphs(token: str, course_id: str, student_id: str, graph_type: str = 'progress', time_range: str = '30d') -> dict:
    """Get individual student graphs and analytics."""
    try:
        # Verify user token
        from services.achieveup_auth_service import achieveup_verify_token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get student progress data
        from services.achieveup_service import achieveup_progress_collection, achieveup_skill_matrices_collection
        from datetime import datetime, timedelta
        
        # Calculate date range
        end_date = datetime.utcnow()
        if time_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif time_range == '90d':
            start_date = end_date - timedelta(days=90)
        elif time_range == '1y':
            start_date = end_date - timedelta(days=365)
        else:  # 30d default
            start_date = end_date - timedelta(days=30)
        
        # Get progress data
        progress_data = await achieveup_progress_collection.find({
            'student_id': student_id,
            'course_id': course_id,
            'updated_at': {'$gte': start_date, '$lte': end_date}
        }).sort([('updated_at', 1)]).to_list(length=None)
        
        # Get skill matrix
        skill_matrix = await achieveup_skill_matrices_collection.find_one({'course_id': course_id})
        course_skills = skill_matrix.get('skills', []) if skill_matrix else []
        
        # Generate graphs based on type
        if graph_type == 'progress':
            graph_data = generate_progress_graph(progress_data, course_skills, time_range)
        elif graph_type == 'performance':
            graph_data = generate_performance_graph(progress_data, course_skills, time_range)
        elif graph_type == 'skills':
            graph_data = generate_skills_graph(progress_data, course_skills, time_range)
        else:
            graph_data = generate_overview_graph(progress_data, course_skills, time_range)
        
        return {
            'studentId': student_id,
            'courseId': course_id,
            'graphType': graph_type,
            'timeRange': time_range,
            'graphData': graph_data,
            'metadata': {
                'totalDataPoints': len(progress_data),
                'totalSkills': len(course_skills),
                'dateRange': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            },
            'generatedAt': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get individual graphs error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

def calculate_student_risk_level(progress_data: list, total_skills: int, time_range: str) -> str:
    """Calculate risk level for a student based on their progress data."""
    if not progress_data or total_skills == 0:
        return 'high'
    
    # Calculate completion rate
    completed = len([p for p in progress_data if p.get('completed', False)])
    completion_rate = completed / total_skills
    
    # Calculate average score
    scores = [p.get('score', 0) for p in progress_data if 'score' in p]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # Calculate activity frequency
    from datetime import datetime, timedelta
    recent_cutoff = datetime.utcnow() - timedelta(days=7)
    recent_activity = len([p for p in progress_data if p.get('updated_at', datetime.min) > recent_cutoff])
    
    # Risk scoring
    risk_score = 0
    
    # Completion rate factor (40% weight)
    if completion_rate >= 0.8:
        risk_score += 0
    elif completion_rate >= 0.6:
        risk_score += 1
    elif completion_rate >= 0.4:
        risk_score += 2
    else:
        risk_score += 3
    
    # Average score factor (30% weight)
    if avg_score >= 80:
        risk_score += 0
    elif avg_score >= 70:
        risk_score += 1
    elif avg_score >= 60:
        risk_score += 2
    else:
        risk_score += 3
    
    # Activity factor (30% weight)
    if recent_activity >= 3:
        risk_score += 0
    elif recent_activity >= 1:
        risk_score += 1
    else:
        risk_score += 2
    
    # Determine risk level
    if risk_score <= 2:
        return 'low'
    elif risk_score <= 5:
        return 'medium'
    else:
        return 'high'

def analyze_risk_factors(student_analytics: list, threshold: float) -> dict:
    """Analyze common risk factors across students."""
    if not student_analytics:
        return {}
    
    total_students = len(student_analytics)
    
    # Calculate factor frequencies
    low_completion = len([s for s in student_analytics if s['progress'] < threshold * 100])
    low_scores = len([s for s in student_analytics if s['progress'] < 70])
    inactive_students = len([s for s in student_analytics if s['activityCount'] < 3])
    
    return {
        'lowCompletion': {
            'count': low_completion,
            'percentage': round(low_completion / total_students * 100, 1),
            'description': f'Students with less than {threshold * 100}% completion rate'
        },
        'lowScores': {
            'count': low_scores,
            'percentage': round(low_scores / total_students * 100, 1),
            'description': 'Students with average scores below 70%'
        },
        'inactiveStudents': {
            'count': inactive_students,
            'percentage': round(inactive_students / total_students * 100, 1),
            'description': 'Students with fewer than 3 recent activities'
        }
    }

def generate_risk_recommendations(high_risk: list, medium_risk: list, risk_factors: dict) -> list:
    """Generate recommendations based on risk assessment."""
    recommendations = []
    
    if high_risk:
        recommendations.append({
            'priority': 'high',
            'type': 'intervention',
            'message': f'{len(high_risk)} students need immediate attention. Consider one-on-one meetings or additional support.',
            'action': 'Schedule individual meetings with high-risk students',
            'students': [s['id'] for s in high_risk[:5]]  # Limit to top 5
        })
    
    if medium_risk:
        recommendations.append({
            'priority': 'medium',
            'type': 'monitoring',
            'message': f'{len(medium_risk)} students should be monitored closely. Consider group study sessions or additional resources.',
            'action': 'Provide additional learning resources and monitor progress',
            'students': [s['id'] for s in medium_risk[:3]]  # Limit to top 3
        })
    
    # Factor-specific recommendations
    if risk_factors.get('lowCompletion', {}).get('percentage', 0) > 30:
        recommendations.append({
            'priority': 'medium',
            'type': 'engagement',
            'message': 'Many students have low completion rates. Consider reviewing assignment difficulty or providing clearer instructions.',
            'action': 'Review course pacing and provide completion incentives'
        })
    
    if risk_factors.get('inactiveStudents', {}).get('percentage', 0) > 25:
        recommendations.append({
            'priority': 'medium',
            'type': 'engagement',
            'message': 'Many students are inactive. Consider sending engagement reminders or creating more interactive content.',
            'action': 'Implement engagement strategies and regular check-ins'
        })
    
    return recommendations

async def calculate_risk_trends(course_id: str, time_range: str) -> dict:
    """Calculate risk trends over time for a course."""
    try:
        from services.achieveup_service import achieveup_progress_collection
        from datetime import datetime, timedelta
        
        # Get historical data for trend calculation
        end_date = datetime.utcnow()
        if time_range == '7d':
            periods = 7
            delta = timedelta(days=1)
        elif time_range == '30d':
            periods = 30
            delta = timedelta(days=1)
        elif time_range == '90d':
            periods = 12
            delta = timedelta(days=7)
        else:  # 1y
            periods = 12
            delta = timedelta(days=30)
        
        trend_data = []
        for i in range(periods):
            period_end = end_date - (delta * i)
            period_start = period_end - delta
            
            # Get progress data for this period
            progress_count = await achieveup_progress_collection.count_documents({
                'course_id': course_id,
                'updated_at': {'$gte': period_start, '$lte': period_end}
            })
            
            trend_data.append({
                'period': period_start.strftime('%Y-%m-%d'),
                'activity': progress_count,
                'date': period_start.isoformat()
            })
        
        trend_data.reverse()  # Chronological order
        
        return {
            'periods': periods,
            'timeRange': time_range,
            'data': trend_data,
            'summary': {
                'totalActivity': sum([t['activity'] for t in trend_data]),
                'averageActivity': round(sum([t['activity'] for t in trend_data]) / len(trend_data), 1) if trend_data else 0,
                'trend': calculate_trend_direction(trend_data)
            }
        }
        
    except Exception as e:
        logger.error(f"Calculate risk trends error: {str(e)}")
        return {'error': 'Error calculating trends'}

def calculate_trend_direction(trend_data: list) -> str:
    """Calculate if trend is increasing, decreasing, or stable."""
    if len(trend_data) < 2:
        return 'insufficient_data'
    
    first_half = trend_data[:len(trend_data)//2]
    second_half = trend_data[len(trend_data)//2:]
    
    first_avg = sum([t['activity'] for t in first_half]) / len(first_half)
    second_avg = sum([t['activity'] for t in second_half]) / len(second_half)
    
    if second_avg > first_avg * 1.1:
        return 'increasing'
    elif second_avg < first_avg * 0.9:
        return 'decreasing'
    else:
        return 'stable'

def export_to_csv(data: dict, analytics_type: str) -> dict:
    """Export analytics data to CSV format."""
    import csv
    import io
    
    output = io.StringIO()
    
    if analytics_type == 'students':
        # Export student analytics to CSV
        fieldnames = ['id', 'name', 'progress', 'skillsMastered', 'badgesEarned', 'riskLevel', 'skillBreakdown']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for student in data.get('analytics', {}).get('students', []):
            row = {k: v for k, v in student.items() if k in fieldnames}
            # Handle skillBreakdown as a JSON string
            row['skillBreakdown'] = json.dumps(row['skillBreakdown'])
            writer.writerow(row)
    
    csv_content = output.getvalue()
    output.close()
    
    return {
        'format': 'csv',
        'content': csv_content,
        'filename': f"analytics_{analytics_type}.csv"
    }

async def export_to_pdf(data: dict, analytics_type: str) -> dict:
    """Export analytics data to PDF format."""
    # This would require a PDF library like reportlab
    # For now, return a placeholder
    return {
        'format': 'pdf',
        'content': 'PDF export not yet implemented',
        'filename': f"analytics_{analytics_type}.pdf",
        'note': 'PDF export feature coming soon'
    }

def generate_progress_graph(progress_data: list, course_skills: list, time_range: str) -> dict:
    """Generate progress over time graph data."""
    from datetime import datetime, timedelta
    
    # Group progress by date
    daily_progress = {}
    for progress in progress_data:
        date = progress.get('updated_at', datetime.now()).strftime('%Y-%m-%d')
        if date not in daily_progress:
            daily_progress[date] = 0
        daily_progress[date] += 1
    
    # Create time series data
    dates = sorted(daily_progress.keys())
    cumulative_progress = 0
    graph_data = []
    
    for date in dates:
        cumulative_progress += daily_progress[date]
        graph_data.append({
            'date': date,
            'progress': cumulative_progress,
            'dailyActivity': daily_progress[date]
        })
    
    return {
        'type': 'line',
        'title': 'Progress Over Time',
        'xAxis': 'Date',
        'yAxis': 'Cumulative Progress',
        'data': graph_data,
        'summary': {
            'totalProgress': cumulative_progress,
            'peakDay': max(daily_progress, key=daily_progress.get) if daily_progress else None,
            'averageDailyActivity': round(sum(daily_progress.values()) / len(daily_progress), 1) if daily_progress else 0
        }
    }

def generate_performance_graph(progress_data: list, course_skills: list, time_range: str) -> dict:
    """Generate performance scores graph data."""
    # Group by skill and calculate average scores
    skill_performance = {}
    for progress in progress_data:
        skill = progress.get('skill', 'Unknown')
        score = progress.get('score', 0)
        
        if skill not in skill_performance:
            skill_performance[skill] = []
        skill_performance[skill].append(score)
    
    # Calculate averages
    graph_data = []
    for skill, scores in skill_performance.items():
        avg_score = sum(scores) / len(scores)
        graph_data.append({
            'skill': skill,
            'averageScore': round(avg_score, 1),
            'attempts': len(scores),
            'bestScore': max(scores),
            'latestScore': scores[-1] if scores else 0
        })
    
    # Sort by average score
    graph_data.sort(key=lambda x: x['averageScore'], reverse=True)
    
    return {
        'type': 'bar',
        'title': 'Performance by Skill',
        'xAxis': 'Skills',
        'yAxis': 'Average Score',
        'data': graph_data,
        'summary': {
            'overallAverage': round(sum([d['averageScore'] for d in graph_data]) / len(graph_data), 1) if graph_data else 0,
            'bestSkill': graph_data[0]['skill'] if graph_data else None,
            'skillsAttempted': len(graph_data),
            'totalSkills': len(course_skills)
        }
    }

def generate_skills_graph(progress_data: list, course_skills: list, time_range: str) -> dict:
    """Generate skills mastery graph data."""
    # Calculate mastery level for each skill
    skill_mastery = {}
    for skill in course_skills:
        skill_progress = [p for p in progress_data if p.get('skill') == skill]
        
        if skill_progress:
            completed = len([p for p in skill_progress if p.get('completed', False)])
            total_attempts = len(skill_progress)
            avg_score = sum([p.get('score', 0) for p in skill_progress]) / len(skill_progress)
            mastery_level = calculate_mastery_level(completed, total_attempts, avg_score)
        else:
            mastery_level = 'not_attempted'
            avg_score = 0
            completed = 0
            total_attempts = 0
        
        skill_mastery[skill] = {
            'skill': skill,
            'masteryLevel': mastery_level,
            'averageScore': round(avg_score, 1),
            'completed': completed,
            'totalAttempts': total_attempts,
            'completionRate': round(completed / total_attempts * 100, 1) if total_attempts > 0 else 0
        }
    
    return {
        'type': 'radar',
        'title': 'Skills Mastery Overview',
        'data': list(skill_mastery.values()),
        'summary': {
            'masteredSkills': len([s for s in skill_mastery.values() if s['masteryLevel'] == 'mastered']),
            'developingSkills': len([s for s in skill_mastery.values() if s['masteryLevel'] == 'developing']),
            'beginnerSkills': len([s for s in skill_mastery.values() if s['masteryLevel'] == 'beginner']),
            'notAttempted': len([s for s in skill_mastery.values() if s['masteryLevel'] == 'not_attempted']),
            'overallMastery': calculate_overall_mastery(list(skill_mastery.values()))
        }
    }

def generate_overview_graph(progress_data: list, course_skills: list, time_range: str) -> dict:
    """Generate overview dashboard graph data."""
    # Combine multiple graph types for overview
    progress_graph = generate_progress_graph(progress_data, course_skills, time_range)
    performance_graph = generate_performance_graph(progress_data, course_skills, time_range)
    skills_graph = generate_skills_graph(progress_data, course_skills, time_range)
    
    return {
        'type': 'dashboard',
        'title': 'Student Overview Dashboard',
        'components': {
            'progress': progress_graph,
            'performance': performance_graph,
            'skills': skills_graph
        },
        'summary': {
            'totalActivities': len(progress_data),
            'skillsWorkedOn': len(set([p.get('skill') for p in progress_data if p.get('skill')])),
            'averageScore': round(sum([p.get('score', 0) for p in progress_data]) / len(progress_data), 1) if progress_data else 0,
            'timeRange': time_range
        }
    }

def calculate_mastery_level(completed: int, total_attempts: int, avg_score: float) -> str:
    """Calculate mastery level based on completion and performance."""
    if total_attempts == 0:
        return 'not_attempted'
    
    completion_rate = completed / total_attempts
    
    if completion_rate >= 0.8 and avg_score >= 85:
        return 'mastered'
    elif completion_rate >= 0.6 and avg_score >= 70:
        return 'developing'
    elif completion_rate >= 0.3 or avg_score >= 60:
        return 'beginner'
    else:
        return 'struggling'

def calculate_overall_mastery(skill_data: list) -> str:
    """Calculate overall mastery level across all skills."""
    if not skill_data:
        return 'no_data'
    
    mastery_levels = [s['masteryLevel'] for s in skill_data]
    mastered_count = len([l for l in mastery_levels if l == 'mastered'])
    developing_count = len([l for l in mastery_levels if l == 'developing'])
    
    total_skills = len(skill_data)
    mastery_rate = mastered_count / total_skills
    developing_rate = developing_count / total_skills
    
    if mastery_rate >= 0.7:
        return 'advanced'
    elif mastery_rate >= 0.4 or (mastery_rate + developing_rate) >= 0.7:
        return 'proficient'
    elif (mastery_rate + developing_rate) >= 0.4:
        return 'developing'
    else:
        return 'beginner' 