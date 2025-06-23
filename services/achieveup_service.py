# services/achieveup_service.py

import json
import logging
import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from config import Config
from utils.ai_utils import generate_core_topic

# Set up logging
logger = logging.getLogger(__name__)

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
            'course_id': course_id,
            'matrix_name': matrix_name,
            'skills': skills,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
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
        
        return badges
        
    except Exception as e:
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
        
        return progress
        
    except Exception as e:
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
            'student_id': student_id,
            'course_id': course_id,
            'skill_progress': skill_progress,
            'last_updated': datetime.utcnow()
        }
        
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