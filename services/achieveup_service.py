# services/achieveup_service.py

<<<<<<< HEAD
import logging
import uuid
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from services.achieveup_auth_service import achieveup_verify_token
from config import Config
=======
import json
import logging
import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from config import Config
from utils.ai_utils import generate_core_topic
>>>>>>> 3223e75b8314e72d7bf5da19b4609ac4d2e1335f

# Set up logging
logger = logging.getLogger(__name__)

<<<<<<< HEAD
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
=======
# MongoDB setup
client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
db = client[Config.DATABASE]
skill_matrices_collection = db["Skill_Matrices"]
badges_collection = db["Badges"]
skill_progress_collection = db["Skill_Progress"]
quizzes_collection = db[Config.QUIZZES_COLLECTION]
students_collection = db[Config.STUDENTS_COLLECTION]

# Skill levels and their descriptions
SKILL_LEVELS = {
    'beginner': {'min_score': 0, 'max_score': 60, 'description': 'Basic understanding'},
    'intermediate': {'min_score': 61, 'max_score': 80, 'description': 'Good understanding'},
    'advanced': {'min_score': 81, 'max_score': 100, 'description': 'Mastery level'}
}

# Badge types and their criteria
BADGE_TYPES = {
    'skill_master': {'description': 'Mastered a specific skill', 'criteria': 90},
    'consistent_learner': {'description': 'Consistent improvement over time', 'criteria': 3},
    'quick_learner': {'description': 'Rapid skill acquisition', 'criteria': 2},
    'persistent': {'description': 'Continued effort despite challenges', 'criteria': 5}
}

async def create_skill_matrix(course_id, matrix_name, skills):
    """Create a new skill matrix for a course."""
    try:
        matrix_data = {
>>>>>>> 3223e75b8314e72d7bf5da19b4609ac4d2e1335f
            'course_id': course_id,
            'matrix_name': matrix_name,
            'skills': skills,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
<<<<<<< HEAD
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
=======
        result = await skill_matrices_collection.insert_one(matrix_data)
        matrix_data['_id'] = str(result.inserted_id)
        
        logger.info(f"Created skill matrix {matrix_name} for course {course_id}")
        return matrix_data
        
    except Exception as e:
        logger.error(f"Error creating skill matrix: {str(e)}")
        raise

async def assign_skills_to_questions(course_id, question_skills):
    """Assign skills to quiz questions in the database."""
    try:
        updated_count = 0
        
        for question_id, skills in question_skills.items():
            result = await quizzes_collection.update_one(
                {'questionid': question_id, 'courseid': course_id},
                {'$set': {'assigned_skills': skills}}
            )
            if result.modified_count > 0:
                updated_count += 1
        
        logger.info(f"Assigned skills to {updated_count} questions in course {course_id}")
        return {'updated_questions': updated_count}
        
    except Exception as e:
        logger.error(f"Error assigning skills to questions: {str(e)}")
        raise

async def suggest_skills(question_text, course_context=""):
    """Use AI to suggest relevant skills for a question."""
    try:
        # Generate core topic using existing AI utility
        core_topic_result = await generate_core_topic(question_text, "Course", course_context)
        
        if not core_topic_result.get('success'):
            return []
        
        core_topic = core_topic_result['core_topic']
        
        # Define skill categories based on the core topic
        skill_suggestions = []
        
        # Add general skills based on question type
        if 'calculate' in question_text.lower() or 'solve' in question_text.lower():
            skill_suggestions.extend(['Problem Solving', 'Mathematical Reasoning', 'Analytical Thinking'])
        
        if 'explain' in question_text.lower() or 'describe' in question_text.lower():
            skill_suggestions.extend(['Communication', 'Conceptual Understanding', 'Knowledge Application'])
        
        if 'compare' in question_text.lower() or 'analyze' in question_text.lower():
            skill_suggestions.extend(['Critical Thinking', 'Comparative Analysis', 'Evaluation'])
        
        # Add topic-specific skills
        skill_suggestions.append(core_topic)
        
        # Remove duplicates and return
        return list(set(skill_suggestions))
        
    except Exception as e:
        logger.error(f"Error suggesting skills: {str(e)}")
        return []

async def calculate_skill_level(score):
    """Calculate skill level based on score."""
    for level, criteria in SKILL_LEVELS.items():
        if criteria['min_score'] <= score <= criteria['max_score']:
            return level
    return 'beginner'

async def generate_badges(student_id, course_id, skill_levels):
    """Generate badges for student achievements."""
    try:
        badges = []
        
        for skill, level in skill_levels.items():
            # Check for skill mastery badge
            if level == 'advanced':
                badge = {
                    'student_id': student_id,
                    'course_id': course_id,
                    'skill': skill,
                    'badge_type': 'skill_master',
                    'description': f'Mastered {skill}',
                    'earned_at': datetime.utcnow(),
                    'level': level
                }
                badges.append(badge)
            
            # Check for consistent learner badge
            progress_history = await get_skill_progress_history(student_id, course_id, skill)
            if len(progress_history) >= 3:
                recent_scores = [p['score'] for p in progress_history[-3:]]
                if all(score >= 70 for score in recent_scores):
                    badge = {
                        'student_id': student_id,
                        'course_id': course_id,
                        'skill': skill,
                        'badge_type': 'consistent_learner',
                        'description': f'Consistent performance in {skill}',
                        'earned_at': datetime.utcnow(),
                        'level': level
                    }
                    badges.append(badge)
        
        # Insert badges into database
        if badges:
            await badges_collection.insert_many(badges)
            logger.info(f"Generated {len(badges)} badges for student {student_id}")
>>>>>>> 3223e75b8314e72d7bf5da19b4609ac4d2e1335f
        
        return badges
        
    except Exception as e:
<<<<<<< HEAD
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
=======
        logger.error(f"Error generating badges: {str(e)}")
        raise

async def get_skill_progress_history(student_id, course_id, skill):
    """Get progress history for a specific skill."""
    try:
        progress = await skill_progress_collection.find({
            'student_id': student_id,
            'course_id': course_id,
            'skill': skill
        }).sort('timestamp', -1).to_list(length=10)
>>>>>>> 3223e75b8314e72d7bf5da19b4609ac4d2e1335f
        
        return progress
        
    except Exception as e:
<<<<<<< HEAD
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
=======
        logger.error(f"Error getting skill progress history: {str(e)}")
        return []

async def get_skill_progress(student_id, course_id):
    """Get current skill progress for a student in a course."""
    try:
        # Get student's quiz performance
        student_record = await students_collection.find_one({'_id': student_id})
        if not student_record:
            return {'error': 'Student not found'}
        
        course_quizzes = student_record.get(course_id, [])
        
        # Get skill matrix for the course
        skill_matrix = await skill_matrices_collection.find_one({'course_id': course_id})
        if not skill_matrix:
            return {'error': 'No skill matrix found for course'}
        
        skills = skill_matrix.get('skills', [])
        skill_progress = {}
        
        # Calculate skill progress based on quiz performance
        for skill in skills:
            skill_questions = await quizzes_collection.find({
                'courseid': course_id,
                'assigned_skills': skill
            }).to_list(length=100)
            
            if not skill_questions:
                continue
            
            total_questions = len(skill_questions)
            correct_answers = 0
            
            for question in skill_questions:
                question_id = question.get('questionid')
                # Check if student answered this question correctly
                for quiz in course_quizzes:
                    if quiz.get('questionid') == question_id and quiz.get('correct', False):
                        correct_answers += 1
                        break
            
            score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
            level = await calculate_skill_level(score)
            
            skill_progress[skill] = {
                'score': round(score, 2),
                'level': level,
                'total_questions': total_questions,
                'correct_answers': correct_answers
            }
        
        return {
>>>>>>> 3223e75b8314e72d7bf5da19b4609ac4d2e1335f
            'student_id': student_id,
            'course_id': course_id,
            'skill_progress': skill_progress,
            'last_updated': datetime.utcnow()
        }
        
<<<<<<< HEAD
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
=======
    except Exception as e:
        logger.error(f"Error getting skill progress: {str(e)}")
        raise

async def update_skill_assessment(student_id, course_id, skill_updates):
    """Update skill assessment for a student."""
    try:
        for skill, update_data in skill_updates.items():
            assessment_data = {
                'student_id': student_id,
                'course_id': course_id,
                'skill': skill,
                'score': update_data.get('score', 0),
                'level': await calculate_skill_level(update_data.get('score', 0)),
                'timestamp': datetime.utcnow(),
                'notes': update_data.get('notes', '')
            }
            
            await skill_progress_collection.insert_one(assessment_data)
        
        # Generate badges based on updated progress
        skill_levels = {skill: update_data.get('level', 'beginner') 
                       for skill, update_data in skill_updates.items()}
        await generate_badges(student_id, course_id, skill_levels)
        
        logger.info(f"Updated skill assessment for student {student_id} in course {course_id}")
        return {'message': 'Skill assessment updated successfully'}
        
    except Exception as e:
        logger.error(f"Error updating skill assessment: {str(e)}")
        raise

async def create_individual_graphs(student_id):
    """Create individual skill graphs for a student."""
    try:
        # Get all courses the student is enrolled in
        student_record = await students_collection.find_one({'_id': student_id})
        if not student_record:
            return {'error': 'Student not found'}
        
        course_ids = list(student_record.keys())
        course_ids.remove('_id')  # Remove the _id field
        
        graphs_data = {}
        
        for course_id in course_ids:
            progress = await get_skill_progress(student_id, course_id)
            if 'error' not in progress:
                graphs_data[course_id] = progress
        
        # Generate graph data structure
        graph_data = {
            'student_id': student_id,
            'courses': graphs_data,
            'generated_at': datetime.utcnow()
        }
        
        return graph_data
        
    except Exception as e:
        logger.error(f"Error creating individual graphs: {str(e)}")
        raise

async def get_course_skill_summary(course_id):
    """Get a summary of skill performance across all students in a course."""
    try:
        # Get all students in the course
        students = await students_collection.find({course_id: {'$exists': True}}).to_list(length=1000)
        
        # Get skill matrix for the course
        skill_matrix = await skill_matrices_collection.find_one({'course_id': course_id})
        if not skill_matrix:
            return {'error': 'No skill matrix found for course'}
        
        skills = skill_matrix.get('skills', [])
        skill_summary = {}
        
        for skill in skills:
            total_students = 0
            total_score = 0
            level_counts = {'beginner': 0, 'intermediate': 0, 'advanced': 0}
            
            for student in students:
                student_progress = await get_skill_progress(student['_id'], course_id)
                if 'error' not in student_progress and skill in student_progress['skill_progress']:
                    total_students += 1
                    skill_data = student_progress['skill_progress'][skill]
                    total_score += skill_data['score']
                    level_counts[skill_data['level']] += 1
            
            avg_score = (total_score / total_students) if total_students > 0 else 0
            
            skill_summary[skill] = {
                'average_score': round(avg_score, 2),
                'total_students': total_students,
                'level_distribution': level_counts
            }
        
        return {
            'course_id': course_id,
            'skill_summary': skill_summary,
            'generated_at': datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error getting course skill summary: {str(e)}")
        raise 
>>>>>>> 3223e75b8314e72d7bf5da19b4609ac4d2e1335f
