# services/progress_service.py

import logging
import json
import csv
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from services.achieveup_auth_service import achieveup_verify_token
from config import Config

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup for AchieveUp progress data (separate from KnowGap)
client = AsyncIOMotorClient(
        Config.DB_CONNECTION_STRING,
        tlsAllowInvalidCertificates=(Config.ENV == 'development')
    )
db = client[Config.DATABASE]
achieveup_user_progress_collection = db[Config.ACHIEVEUP_USER_PROGRESS_COLLECTION]
achieveup_progress_analytics_collection = db[Config.ACHIEVEUP_PROGRESS_ANALYTICS_COLLECTION]

async def get_user_progress(token: str, course_id: str = None, skill_id: str = None) -> dict:
    """Get progress for the current user."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        
        # Build query
        query = {'user_id': user_id}
        if course_id:
            query['course_id'] = course_id
        if skill_id:
            query['skill_id'] = skill_id
        
        # Get progress from database
        progress_data = []
        async for progress in achieveup_user_progress_collection.find(query):
            progress.pop('_id', None)
            progress_data.append(progress)
        
        # Calculate summary statistics
        total_skills = len(progress_data)
        completed_skills = len([p for p in progress_data if p.get('progress_percentage', 0) >= 100])
        average_progress = sum(p.get('progress_percentage', 0) for p in progress_data) / total_skills if total_skills > 0 else 0
        
        # Get recent activity
        recent_activity = await get_recent_activity(user_id, course_id)
        
        return {
            'progress': progress_data,
            'summary': {
                'total_skills': total_skills,
                'completed_skills': completed_skills,
                'average_progress': round(average_progress, 2),
                'completion_rate': round((completed_skills / total_skills * 100) if total_skills > 0 else 0, 2)
            },
            'recent_activity': recent_activity
        }
        
    except Exception as e:
        logger.error(f"Get user progress error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def update_user_progress(token: str, data: dict) -> dict:
    """Update user progress (e.g., after completing a quiz)."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        course_id = data.get('course_id')
        skill_id = data.get('skill_id')
        quiz_id = data.get('quiz_id')
        questions_attempted = data.get('questions_attempted', 0)
        questions_correct = data.get('questions_correct', 0)
        
        if not course_id or not skill_id or not quiz_id:
            return {
                'error': 'Missing required fields',
                'message': 'Course ID, skill ID, and quiz ID are required',
                'statusCode': 400
            }
        
        # Calculate progress percentage
        progress_percentage = (questions_correct / questions_attempted * 100) if questions_attempted > 0 else 0
        
        # Update or create progress record
        progress_doc = {
            'user_id': user_id,
            'course_id': course_id,
            'skill_id': skill_id,
            'quiz_id': quiz_id,
            'questions_attempted': questions_attempted,
            'questions_correct': questions_correct,
            'progress_percentage': progress_percentage,
            'last_updated': datetime.utcnow()
        }
        
        # Use upsert to create or update
        await achieveup_user_progress_collection.update_one(
            {
                'user_id': user_id,
                'course_id': course_id,
                'skill_id': skill_id
            },
            {'$set': progress_doc},
            upsert=True
        )
        
        # Update analytics
        await update_progress_analytics(user_id, course_id, skill_id, progress_percentage)
        
        return {
            'message': 'Progress updated successfully',
            'progress': progress_doc
        }
        
    except Exception as e:
        logger.error(f"Update user progress error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_progress_analytics(token: str, course_id: str = None, time_range: str = '30d') -> dict:
    """Get progress analytics and insights."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        
        # Calculate date range
        end_date = datetime.utcnow()
        if time_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif time_range == '30d':
            start_date = end_date - timedelta(days=30)
        elif time_range == '90d':
            start_date = end_date - timedelta(days=90)
        elif time_range == '1y':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Build query
        query = {
            'user_id': user_id,
            'last_updated': {'$gte': start_date, '$lte': end_date}
        }
        if course_id:
            query['course_id'] = course_id
        
        # Get analytics data
        analytics_data = []
        async for analytics in achieveup_progress_analytics_collection.find(query):
            analytics.pop('_id', None)
            analytics_data.append(analytics)
        
        # Calculate trends
        trends = calculate_progress_trends(analytics_data)
        
        # Get recommendations
        recommendations = generate_progress_recommendations(analytics_data)
        
        return {
            'analytics': analytics_data,
            'trends': trends,
            'recommendations': recommendations,
            'time_range': time_range
        }
        
    except Exception as e:
        logger.error(f"Get progress analytics error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def export_progress_data(token: str, course_id: str = None, format_type: str = 'json') -> dict:
    """Export progress data for the user."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        
        # Get all progress data
        query = {'user_id': user_id}
        if course_id:
            query['course_id'] = course_id
        
        progress_data = []
        async for progress in achieveup_user_progress_collection.find(query):
            progress.pop('_id', None)
            progress_data.append(progress)
        
        # Format data based on export type
        if format_type == 'csv':
            export_data = format_progress_csv(progress_data)
            content_type = 'text/csv'
        elif format_type == 'pdf':
            export_data = format_progress_pdf(progress_data)
            content_type = 'application/pdf'
        else:  # json
            export_data = json.dumps(progress_data, default=str)
            content_type = 'application/json'
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"achieveup_progress_{user_id}_{timestamp}.{format_type}"
        
        return {
            'data': export_data,
            'filename': filename,
            'content_type': content_type,
            'format': format_type,
            'record_count': len(progress_data)
        }
        
    except Exception as e:
        logger.error(f"Export progress data error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

# Helper functions
async def get_recent_activity(user_id: str, course_id: str = None) -> list:
    """Get recent activity for a user."""
    query = {'user_id': user_id}
    if course_id:
        query['course_id'] = course_id
    
    # Get recent progress updates
    recent_updates = []
    async for progress in achieveup_user_progress_collection.find(query).sort('last_updated', -1).limit(10):
        recent_updates.append({
            'skill_id': progress.get('skill_id'),
            'progress_percentage': progress.get('progress_percentage'),
            'last_updated': progress.get('last_updated'),
            'quiz_id': progress.get('quiz_id')
        })
    
    return recent_updates

async def update_progress_analytics(user_id: str, course_id: str, skill_id: str, progress_percentage: float):
    """Update progress analytics."""
    analytics_doc = {
        'user_id': user_id,
        'course_id': course_id,
        'skill_id': skill_id,
        'progress_percentage': progress_percentage,
        'timestamp': datetime.utcnow()
    }
    
    await achieveup_progress_analytics_collection.insert_one(analytics_doc)

def calculate_progress_trends(analytics_data: list) -> dict:
    """Calculate progress trends from analytics data."""
    if not analytics_data:
        return {'trend': 'stable', 'change_percentage': 0}
    
    # Sort by timestamp
    sorted_data = sorted(analytics_data, key=lambda x: x.get('timestamp', datetime.min))
    
    if len(sorted_data) < 2:
        return {'trend': 'stable', 'change_percentage': 0}
    
    # Calculate trend
    first_progress = sorted_data[0].get('progress_percentage', 0)
    last_progress = sorted_data[-1].get('progress_percentage', 0)
    change_percentage = last_progress - first_progress
    
    if change_percentage > 5:
        trend = 'improving'
    elif change_percentage < -5:
        trend = 'declining'
    else:
        trend = 'stable'
    
    return {
        'trend': trend,
        'change_percentage': round(change_percentage, 2),
        'first_progress': first_progress,
        'last_progress': last_progress
    }

def generate_progress_recommendations(analytics_data: list) -> list:
    """Generate progress recommendations based on analytics."""
    recommendations = []
    
    if not analytics_data:
        recommendations.append({
            'type': 'start',
            'message': 'Start working on skills to see your progress!',
            'priority': 'high'
        })
        return recommendations
    
    # Analyze progress patterns
    low_progress_skills = [a for a in analytics_data if a.get('progress_percentage', 0) < 50]
    high_progress_skills = [a for a in analytics_data if a.get('progress_percentage', 0) >= 75]
    
    if low_progress_skills:
        recommendations.append({
            'type': 'focus',
            'message': f'Focus on improving {len(low_progress_skills)} skills with low progress',
            'priority': 'high'
        })
    
    if high_progress_skills:
        recommendations.append({
            'type': 'maintain',
            'message': f'Great work! Maintain your high progress in {len(high_progress_skills)} skills',
            'priority': 'medium'
        })
    
    # Add general recommendations
    recommendations.append({
        'type': 'practice',
        'message': 'Practice regularly to maintain and improve your skills',
        'priority': 'medium'
    })
    
    return recommendations

def format_progress_csv(progress_data: list) -> str:
    """Format progress data as CSV."""
    if not progress_data:
        return ""
    
    # Create CSV string
    output = []
    fieldnames = ['user_id', 'course_id', 'skill_id', 'quiz_id', 'questions_attempted', 
                  'questions_correct', 'progress_percentage', 'last_updated']
    
    # Add header
    output.append(','.join(fieldnames))
    
    # Add data rows
    for progress in progress_data:
        row = []
        for field in fieldnames:
            value = progress.get(field, '')
            if isinstance(value, datetime):
                value = value.isoformat()
            row.append(str(value))
        output.append(','.join(row))
    
    return '\n'.join(output)

def format_progress_pdf(progress_data: list) -> str:
    """Format progress data as PDF (placeholder - would use a PDF library in production)."""
    # This is a placeholder - in production you'd use a library like reportlab
    return f"PDF export for {len(progress_data)} progress records (placeholder)" 