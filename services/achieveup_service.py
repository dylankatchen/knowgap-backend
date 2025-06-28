# services/achieveup_service.py

import logging
import uuid
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from services.achieveup_auth_service import achieveup_verify_token
from config import Config

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup for AchieveUp data (separate from KnowGap)
client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
db = client[Config.DATABASE]

# Collections
achieveup_skill_matrices_collection = db["AchieveUp_Skill_Matrices"]
achieveup_question_skills_collection = db["AchieveUp_Question_Skills"]
achieveup_badges_collection = db["AchieveUp_Badges"]
achieveup_progress_collection = db["AchieveUp_Progress"]
achieveup_analytics_collection = db["AchieveUp_Analytics"]

async def create_skill_matrix(token: str, course_id: str, matrix_name: str, skills: list) -> dict:
    """Create skill matrix for a course."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Check if matrix already exists for this course
        existing_matrix = await achieveup_skill_matrices_collection.find_one({'course_id': course_id})
        if existing_matrix:
            return {
                'error': 'Matrix already exists',
                'message': 'A skill matrix already exists for this course',
                'statusCode': 409
            }
        
        # Create matrix document
        matrix_id = str(uuid.uuid4())
        matrix_doc = {
            '_id': matrix_id,
            'course_id': course_id,
            'matrix_name': matrix_name,
            'skills': skills,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert into database
        await achieveup_skill_matrices_collection.insert_one(matrix_doc)
        
        return matrix_doc
        
    except Exception as e:
        logger.error(f"Create skill matrix error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def update_skill_matrix(token: str, matrix_id: str, skills: list) -> dict:
    """Update skill matrix."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Update matrix
        result = await achieveup_skill_matrices_collection.update_one(
            {'_id': matrix_id},
            {
                '$set': {
                    'skills': skills,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            return {
                'error': 'Matrix not found',
                'message': 'Skill matrix not found',
                'statusCode': 404
            }
        
        # Get updated matrix
        updated_matrix = await achieveup_skill_matrices_collection.find_one({'_id': matrix_id})
        return updated_matrix
        
    except Exception as e:
        logger.error(f"Update skill matrix error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_skill_matrix(token: str, course_id: str) -> dict:
    """Get skill matrix for a course."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Find matrix
        matrix = await achieveup_skill_matrices_collection.find_one({'course_id': course_id})
        if not matrix:
            return {
                'error': 'Matrix not found',
                'message': 'No skill matrix found for this course',
                'statusCode': 404
            }
        
        return matrix
        
    except Exception as e:
        logger.error(f"Get skill matrix error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def assign_skills_to_questions(token: str, course_id: str, question_skills: dict) -> dict:
    """Assign skills to quiz questions."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Store question-skill assignments
        for question_id, skills in question_skills.items():
            assignment_doc = {
                'question_id': question_id,
                'course_id': course_id,
                'skills': skills,
                'assigned_at': datetime.utcnow()
            }
            
            # Upsert assignment
            await achieveup_question_skills_collection.update_one(
                {'question_id': question_id, 'course_id': course_id},
                {'$set': assignment_doc},
                upsert=True
            )
        
        return {'message': 'Skills assigned successfully'}
        
    except Exception as e:
        logger.error(f"Assign skills error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def suggest_skills_for_question(token: str, question_text: str, course_context: str = None) -> dict:
    """Suggest skills for a quiz question using AI."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Simple keyword-based skill suggestion (can be enhanced with AI)
        suggested_skills = []
        
        # Common skill keywords
        skill_keywords = {
            'problem_solving': ['solve', 'problem', 'analyze', 'evaluate'],
            'critical_thinking': ['think', 'critical', 'reason', 'logic'],
            'communication': ['explain', 'describe', 'communicate', 'present'],
            'technical_skills': ['code', 'program', 'algorithm', 'data'],
            'research': ['research', 'find', 'investigate', 'explore'],
            'creativity': ['create', 'design', 'innovate', 'imagine']
        }
        
        question_lower = question_text.lower()
        context_lower = course_context.lower() if course_context else ""
        
        for skill, keywords in skill_keywords.items():
            for keyword in keywords:
                if keyword in question_lower or keyword in context_lower:
                    suggested_skills.append(skill)
                    break
        
        # Remove duplicates
        suggested_skills = list(set(suggested_skills))
        
        return suggested_skills
        
    except Exception as e:
        logger.error(f"Suggest skills error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def generate_badges_for_student(token: str, student_id: str, course_id: str, skill_levels: dict) -> dict:
    """Generate badges for a student based on skill levels."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        badges = []
        
        # Generate badges based on skill levels
        for skill_name, level in skill_levels.items():
            if level in ['beginner', 'intermediate', 'advanced']:
                badge_id = str(uuid.uuid4())
                
                # Determine badge type based on level
                if level == 'advanced':
                    badge_type = 'skill_master'
                    description = f"Mastered {skill_name}"
                elif level == 'intermediate':
                    badge_type = 'consistent_learner'
                    description = f"Consistent progress in {skill_name}"
                else:
                    badge_type = 'quick_learner'
                    description = f"Started learning {skill_name}"
                
                badge_doc = {
                    '_id': badge_id,
                    'student_id': student_id,
                    'course_id': course_id,
                    'skill': skill_name,
                    'badge_type': badge_type,
                    'description': description,
                    'earned_at': datetime.utcnow(),
                    'level': level
                }
                
                # Insert badge
                await achieveup_badges_collection.insert_one(badge_doc)
                badges.append(badge_doc)
        
        return badges
        
    except Exception as e:
        logger.error(f"Generate badges error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_student_badges(token: str, student_id: str) -> dict:
    """Get badges for a student."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Find badges
        cursor = achieveup_badges_collection.find({'student_id': student_id})
        badges = await cursor.to_list(length=None)
        
        return badges
        
    except Exception as e:
        logger.error(f"Get student badges error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_student_progress(token: str, student_id: str, course_id: str) -> dict:
    """Get skill progress for a student in a course."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Find progress
        progress = await achieveup_progress_collection.find_one({
            'student_id': student_id,
            'course_id': course_id
        })
        
        if not progress:
            return {
                'student_id': student_id,
                'course_id': course_id,
                'skill_progress': {},
                'last_updated': datetime.utcnow().isoformat()
            }
        
        return progress
        
    except Exception as e:
        logger.error(f"Get student progress error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def update_student_progress(token: str, student_id: str, course_id: str, skill_updates: dict) -> dict:
    """Update skill progress for a student in a course."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get current progress
        current_progress = await achieveup_progress_collection.find_one({
            'student_id': student_id,
            'course_id': course_id
        })
        
        if current_progress:
            skill_progress = current_progress.get('skill_progress', {})
        else:
            skill_progress = {}
        
        # Update skill progress
        for skill_name, update_data in skill_updates.items():
            score = update_data.get('score', 0)
            notes = update_data.get('notes', '')
            
            # Determine level based on score
            if score >= 80:
                level = 'advanced'
            elif score >= 60:
                level = 'intermediate'
            else:
                level = 'beginner'
            
            skill_progress[skill_name] = {
                'score': score,
                'level': level,
                'total_questions': skill_progress.get(skill_name, {}).get('total_questions', 0) + 1,
                'correct_answers': skill_progress.get(skill_name, {}).get('correct_answers', 0) + (1 if score >= 60 else 0),
                'notes': notes
            }
        
        # Update or insert progress
        progress_doc = {
            'student_id': student_id,
            'course_id': course_id,
            'skill_progress': skill_progress,
            'last_updated': datetime.utcnow()
        }
        
        await achieveup_progress_collection.update_one(
            {'student_id': student_id, 'course_id': course_id},
            {'$set': progress_doc},
            upsert=True
        )
        
        return progress_doc
        
    except Exception as e:
        logger.error(f"Update student progress error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_individual_analytics(token: str, student_id: str) -> dict:
    """Get analytics data for a student."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get student progress data
        cursor = achieveup_progress_collection.find({'student_id': student_id})
        progress_data = await cursor.to_list(length=None)
        
        # Generate analytics
        analytics = {
            'timeSeriesData': [],
            'performance': [],
            'distribution': [],
            'trends': [],
            'radar': []
        }
        
        # Process progress data for analytics
        for progress in progress_data:
            for skill_name, skill_data in progress.get('skill_progress', {}).items():
                analytics['performance'].append({
                    'skill': skill_name,
                    'score': skill_data.get('score', 0),
                    'level': skill_data.get('level', 'beginner'),
                    'course_id': progress['course_id']
                })
        
        return analytics
        
    except Exception as e:
        logger.error(f"Get individual analytics error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def export_course_data(token: str, course_id: str) -> dict:
    """Export course data (CSV format)."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Collect all course data
        course_data = {
            'skill_matrices': [],
            'badges': [],
            'skill_progress': []
        }
        
        # Get skill matrix
        matrix = await achieveup_skill_matrices_collection.find_one({'course_id': course_id})
        if matrix:
            course_data['skill_matrices'].append(matrix)
        
        # Get badges
        cursor = achieveup_badges_collection.find({'course_id': course_id})
        course_data['badges'] = await cursor.to_list(length=None)
        
        # Get progress
        cursor = achieveup_progress_collection.find({'course_id': course_id})
        course_data['skill_progress'] = await cursor.to_list(length=None)
        
        return course_data
        
    except Exception as e:
        logger.error(f"Export course data error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def import_course_data(token: str, course_id: str, import_data: dict) -> dict:
    """Import course data."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Import skill matrices
        for matrix in import_data.get('skill_matrices', []):
            matrix['course_id'] = course_id
            matrix['_id'] = str(uuid.uuid4())
            matrix['created_at'] = datetime.utcnow()
            matrix['updated_at'] = datetime.utcnow()
            await achieveup_skill_matrices_collection.insert_one(matrix)
        
        # Import badges
        for badge in import_data.get('badges', []):
            badge['course_id'] = course_id
            badge['_id'] = str(uuid.uuid4())
            badge['earned_at'] = datetime.utcnow()
            await achieveup_badges_collection.insert_one(badge)
        
        # Import progress
        for progress in import_data.get('skill_progress', []):
            progress['course_id'] = course_id
            progress['last_updated'] = datetime.utcnow()
            await achieveup_progress_collection.insert_one(progress)
        
        return {'message': 'Course data imported successfully'}
        
    except Exception as e:
        logger.error(f"Import course data error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500} 