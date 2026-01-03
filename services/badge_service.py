# services/badge_service.py

import logging
import uuid
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from services.achieveup_auth_service import achieveup_verify_token
from config import Config

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup for AchieveUp badge data (separate from KnowGap)
client = AsyncIOMotorClient(
        Config.DB_CONNECTION_STRING,
        tlsAllowInvalidCertificates=(Config.ENV == 'development')
    )
db = client[Config.DATABASE]
achieveup_badges_collection = db[Config.ACHIEVEUP_BADGES_COLLECTION]
achieveup_user_badges_collection = db[Config.ACHIEVEUP_USER_BADGES_COLLECTION]
achieveup_badge_progress_collection = db[Config.ACHIEVEUP_BADGE_PROGRESS_COLLECTION]

async def generate_badges_for_user(token: str, data: dict) -> dict:
    """Generate badges for a user based on their progress."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        course_id = data.get('course_id')
        
        if not course_id:
            return {
                'error': 'Missing course_id',
                'message': 'Course ID is required',
                'statusCode': 400
            }
        
        # Get user's skill progress for the course
        progress_data = await get_user_skill_progress(user_id, course_id)
        
        # Generate badges based on progress
        generated_badges = []
        
        for skill_progress in progress_data:
            skill_id = skill_progress.get('skill_id')
            progress_percentage = skill_progress.get('progress_percentage', 0)
            
            # Define badge thresholds
            if progress_percentage >= 90:
                badge_level = 'expert'
                badge_name = f"Expert in {skill_progress.get('skill_name', 'Skill')}"
            elif progress_percentage >= 75:
                badge_level = 'advanced'
                badge_name = f"Advanced in {skill_progress.get('skill_name', 'Skill')}"
            elif progress_percentage >= 50:
                badge_level = 'intermediate'
                badge_name = f"Intermediate in {skill_progress.get('skill_name', 'Skill')}"
            elif progress_percentage >= 25:
                badge_level = 'beginner'
                badge_name = f"Beginner in {skill_progress.get('skill_name', 'Skill')}"
            else:
                continue  # No badge for low progress
            
            # Check if badge already exists
            existing_badge = await achieveup_user_badges_collection.find_one({
                'user_id': user_id,
                'skill_id': skill_id,
                'badge_level': badge_level,
                'course_id': course_id
            })
            
            if not existing_badge:
                # Create new badge
                badge_id = str(uuid.uuid4())
                badge_doc = {
                    'badge_id': badge_id,
                    'user_id': user_id,
                    'skill_id': skill_id,
                    'skill_name': skill_progress.get('skill_name'),
                    'badge_level': badge_level,
                    'badge_name': badge_name,
                    'course_id': course_id,
                    'progress_percentage': progress_percentage,
                    'earned_at': datetime.utcnow(),
                    'shareable_link': f"/badges/{badge_id}/share"
                }
                
                await achieveup_user_badges_collection.insert_one(badge_doc)
                generated_badges.append(badge_doc)
        
        return {
            'message': f'Generated {len(generated_badges)} new badges',
            'badges': generated_badges
        }
        
    except Exception as e:
        logger.error(f"Generate badges error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_user_badges(token: str, course_id: str = None, skill_id: str = None) -> dict:
    """Get all badges for the current user."""
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
        
        # Get badges from database
        badges = []
        async for badge in achieveup_user_badges_collection.find(query):
            badge.pop('_id', None)
            badges.append(badge)
        
        # Sort by earned date (newest first)
        badges.sort(key=lambda x: x.get('earned_at', datetime.min), reverse=True)
        
        return {'badges': badges}
        
    except Exception as e:
        logger.error(f"Get user badges error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_badge_details(token: str, badge_id: str) -> dict:
    """Get detailed information about a specific badge."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        
        # Find badge in database
        badge = await achieveup_user_badges_collection.find_one({
            'badge_id': badge_id,
            'user_id': user_id
        })
        
        if not badge:
            return {
                'error': 'Badge not found',
                'message': 'Badge not found or access denied',
                'statusCode': 404
            }
        
        # Remove MongoDB _id field
        badge.pop('_id', None)
        
        # Add additional badge details
        badge_details = {
            **badge,
            'description': f"Earned {badge.get('badge_level', '').title()} level badge for {badge.get('skill_name', 'skill')}",
            'criteria': f"Complete {get_badge_criteria(badge.get('badge_level'))}% of {badge.get('skill_name', 'skill')} assessments",
            'rarity': get_badge_rarity(badge.get('badge_level')),
            'next_level': get_next_badge_level(badge.get('badge_level'))
        }
        
        return {'badge': badge_details}
        
    except Exception as e:
        logger.error(f"Get badge details error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def share_badge(token: str, badge_id: str, data: dict) -> dict:
    """Share a badge (generate shareable link)."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        
        # Find badge in database
        badge = await achieveup_user_badges_collection.find_one({
            'badge_id': badge_id,
            'user_id': user_id
        })
        
        if not badge:
            return {
                'error': 'Badge not found',
                'message': 'Badge not found or access denied',
                'statusCode': 404
            }
        
        # Generate shareable link
        share_id = str(uuid.uuid4())
        share_link = f"https://achieveup.ucf.edu/badges/{share_id}"
        
        # Store shareable link
        await achieveup_badges_collection.update_one(
            {'badge_id': badge_id},
            {'$set': {
                'share_id': share_id,
                'share_link': share_link,
                'shared_at': datetime.utcnow(),
                'share_settings': data.get('settings', {})
            }},
            upsert=True
        )
        
        return {
            'message': 'Badge shared successfully',
            'share_link': share_link,
            'share_id': share_id
        }
        
    except Exception as e:
        logger.error(f"Share badge error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_badge_progress(token: str, skill_id: str, course_id: str) -> dict:
    """Get progress toward earning a badge for a specific skill."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        
        # Get current progress
        progress = await achieveup_badge_progress_collection.find_one({
            'user_id': user_id,
            'skill_id': skill_id,
            'course_id': course_id
        })
        
        if not progress:
            # Initialize progress if not exists
            progress = {
                'user_id': user_id,
                'skill_id': skill_id,
                'course_id': course_id,
                'progress_percentage': 0,
                'questions_attempted': 0,
                'questions_correct': 0,
                'last_updated': datetime.utcnow()
            }
            await achieveup_badge_progress_collection.insert_one(progress)
        
        # Calculate next badge level
        current_level = get_current_badge_level(progress.get('progress_percentage', 0))
        next_level = get_next_badge_level(current_level)
        next_threshold = get_badge_threshold(next_level)
        
        # Get earned badges for this skill
        earned_badges = []
        async for badge in achieveup_user_badges_collection.find({
            'user_id': user_id,
            'skill_id': skill_id,
            'course_id': course_id
        }):
            earned_badges.append({
                'badge_level': badge.get('badge_level'),
                'badge_name': badge.get('badge_name'),
                'earned_at': badge.get('earned_at')
            })
        
        progress.pop('_id', None)
        
        return {
            'progress': progress,
            'current_level': current_level,
            'next_level': next_level,
            'next_threshold': next_threshold,
            'earned_badges': earned_badges,
            'remaining_for_next': max(0, next_threshold - progress.get('progress_percentage', 0))
        }
        
    except Exception as e:
        logger.error(f"Get badge progress error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

# Helper functions
async def get_user_skill_progress(user_id: str, course_id: str) -> list:
    """
    Get user's skill progress for a course based on real quiz submissions.
    
    Calculates progress by:
    1. Fetching all quiz submissions for the student
    2. Getting skill assignments for each question
    3. Calculating percentage of correct answers per skill
    
    Args:
        user_id: Student's Canvas user ID
        course_id: Canvas course ID
        
    Returns:
        list: Skill progress data with percentages
    """
    try:
        from services.canvas_submissions_service import get_cached_submission
        
        # Get all skill assignments for this course
        skill_assignments = {}
        async for assignment in db[Config.ACHIEVEUP_QUESTION_SKILLS_COLLECTION].find({'course_id': course_id}):
            question_id = assignment.get('question_id')
            skills = assignment.get('skills', [])
            skill_assignments[question_id] = skills
        
        # If no skill assignments exist, return empty list
        if not skill_assignments:
            logger.warning(f"No skill assignments found for course {course_id}")
            return []
        
        # Get all quiz submissions for this student in the course
        submissions_cursor = db.get_collection('AchieveUp_Quiz_Submissions').find({
            'student_id': user_id,
            'course_id': course_id
        })
        
        # Track skill performance
        skill_stats = {}  # {skill_name: {'correct': int, 'total': int}}
        
        async for submission in submissions_cursor:
            questions = submission.get('questions', [])
            
            for question in questions:
                question_id = question.get('question_id')
                correct = question.get('correct', False)
                
                # Get assigned skills for this question
                assigned_skills = skill_assignments.get(question_id, [])
                
                for skill in assigned_skills:
                    skill_name = skill.get('name') if isinstance(skill, dict) else skill
                    
                    if skill_name not in skill_stats:
                        skill_stats[skill_name] = {'correct': 0, 'total': 0}
                    
                    skill_stats[skill_name]['total'] += 1
                    if correct:
                        skill_stats[skill_name]['correct'] += 1
        
        # Calculate progress percentages
        progress_data = []
        for skill_name, stats in skill_stats.items():
            total = stats['total']
            correct = stats['correct']
            
            if total > 0:
                progress_percentage = (correct / total) * 100
            else:
                progress_percentage = 0
            
            progress_data.append({
                'skill_id': skill_name.lower().replace(' ', '_'),
                'skill_name': skill_name,
                'progress_percentage': round(progress_percentage, 2),
                'questions_attempted': total,
                'questions_correct': correct
            })
        
        # Sort by skill name for consistency
        progress_data.sort(key=lambda x: x['skill_name'])
        
        return progress_data
        
    except Exception as e:
        logger.error(f"Get user skill progress error: {str(e)}")
        # Return empty list on error rather than failing completely
        return []

def get_badge_criteria(badge_level: str) -> int:
    """Get the criteria percentage for a badge level."""
    criteria_map = {
        'beginner': 25,
        'intermediate': 50,
        'advanced': 75,
        'expert': 90
    }
    return criteria_map.get(badge_level, 0)

def get_badge_rarity(badge_level: str) -> str:
    """Get the rarity of a badge level."""
    rarity_map = {
        'beginner': 'Common',
        'intermediate': 'Uncommon',
        'advanced': 'Rare',
        'expert': 'Legendary'
    }
    return rarity_map.get(badge_level, 'Common')

def get_next_badge_level(current_level: str) -> str:
    """Get the next badge level."""
    level_progression = ['beginner', 'intermediate', 'advanced', 'expert']
    try:
        current_index = level_progression.index(current_level)
        if current_index < len(level_progression) - 1:
            return level_progression[current_index + 1]
    except ValueError:
        pass
    return None

def get_current_badge_level(progress_percentage: float) -> str:
    """Get current badge level based on progress percentage."""
    if progress_percentage >= 90:
        return 'expert'
    elif progress_percentage >= 75:
        return 'advanced'
    elif progress_percentage >= 50:
        return 'intermediate'
    elif progress_percentage >= 25:
        return 'beginner'
    else:
        return 'none'

def get_badge_threshold(badge_level: str) -> int:
    """Get the threshold percentage for a badge level."""
    threshold_map = {
        'beginner': 25,
        'intermediate': 50,
        'advanced': 75,
        'expert': 90
    }
    return threshold_map.get(badge_level, 0)

async def get_student_earned_badges(token: str, student_id: str) -> dict:
    """Get all earned badges for a specific student with course information."""
    try:
        # Verify token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get all badges for the student (only earned ones with progress >= 80)
        badges = []
        async for badge_doc in achieveup_user_badges_collection.find({'user_id': student_id}):
            # Only include badges that are actually earned (80% or higher)
            if badge_doc.get('progress_percentage', 0) >= 80:
                badge_doc.pop('_id', None)
                badges.append(badge_doc)
        
        # Get course names from Canvas API
        from services.achieveup_canvas_service import get_instructor_courses
        
        # Get the canvas token from the user document
        user_doc = await db[Config.ACHIEVEUP_USERS_COLLECTION].find_one({'user_id': user_result.get('user_id')})
        canvas_token = user_doc.get('canvas_token') if user_doc else None
        
        # Create a map of course_id to course_name
        course_map = {}
        if canvas_token:
            try:
                courses_result = await get_instructor_courses(canvas_token)
                if 'courses' in courses_result:
                    for course in courses_result['courses']:
                        course_map[str(course.get('id'))] = course.get('name', 'Unknown Course')
            except Exception as e:
                logger.error(f"Error fetching courses: {str(e)}")
        
        # Enrich badges with course names
        enriched_badges = []
        for badge in badges:
            enriched_badge = {
                'badge_id': badge.get('badge_id'),
                'badge_name': badge.get('badge_name'),
                'skill_name': badge.get('skill_name'),
                'badge_level': badge.get('badge_level'),
                'progress_percentage': badge.get('progress_percentage'),
                'earned_at': badge.get('earned_at'),
                'course_id': badge.get('course_id'),
                'course_name': course_map.get(str(badge.get('course_id')), 'Unknown Course')
            }
            enriched_badges.append(enriched_badge)
        
        # Sort by earned date (newest first)
        enriched_badges.sort(key=lambda x: x.get('earned_at', datetime.min), reverse=True)
        
        return {
            'student_id': student_id,
            'total_badges': len(enriched_badges),
            'badges': enriched_badges
        }
        
    except Exception as e:
        logger.error(f"Get student earned badges error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500} 