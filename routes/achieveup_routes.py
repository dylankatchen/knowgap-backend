# routes/achieveup_routes.py

import json
import logging
from quart import request, jsonify
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
from services.achieveup_service import (
    create_skill_matrix,
    assign_skills_to_questions,
    generate_badges,
    suggest_skills,
    create_individual_graphs,
    get_skill_progress,
    update_skill_assessment
)

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup
client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
db = client[Config.DATABASE]
achieveup_collection = db["AchieveUp_Data"]
skill_matrices_collection = db["Skill_Matrices"]
badges_collection = db["Badges"]
skill_progress_collection = db["Skill_Progress"]

def init_achieveup_routes(app):
    """Initialize AchieveUp routes for micro-credentialling and skill assessment."""
    
    @app.route('/achieveup/matrix/create', methods=['POST'])
    async def create_matrix():
        """Create a skill matrix for a course or assessment."""
        try:
            data = await request.get_json()
            course_id = data.get('course_id')
            matrix_name = data.get('matrix_name')
            skills = data.get('skills', [])
            
            if not course_id or not matrix_name:
                return jsonify({'error': 'course_id and matrix_name are required'}), 400
            
            result = await create_skill_matrix(course_id, matrix_name, skills)
            return jsonify(result), 201
            
        except Exception as e:
            logger.error(f"Error creating skill matrix: {str(e)}")
            return jsonify({'error': 'Failed to create skill matrix'}), 500
    
    @app.route('/achieveup/matrix/<matrix_id>', methods=['GET'])
    async def get_matrix(matrix_id):
        """Get a specific skill matrix by ID."""
        try:
            matrix = await skill_matrices_collection.find_one({'_id': matrix_id})
            if not matrix:
                return jsonify({'error': 'Matrix not found'}), 404
            
            # Remove MongoDB ObjectId for JSON serialization
            matrix['_id'] = str(matrix['_id'])
            return jsonify(matrix), 200
            
        except Exception as e:
            logger.error(f"Error retrieving matrix: {str(e)}")
            return jsonify({'error': 'Failed to retrieve matrix'}), 500
    
    @app.route('/achieveup/matrix/<matrix_id>', methods=['PUT'])
    async def update_matrix(matrix_id):
        """Update a skill matrix."""
        try:
            data = await request.get_json()
            skills = data.get('skills', [])
            
            result = await skill_matrices_collection.update_one(
                {'_id': matrix_id},
                {'$set': {'skills': skills}}
            )
            
            if result.modified_count == 0:
                return jsonify({'error': 'Matrix not found or no changes made'}), 404
            
            return jsonify({'message': 'Matrix updated successfully'}), 200
            
        except Exception as e:
            logger.error(f"Error updating matrix: {str(e)}")
            return jsonify({'error': 'Failed to update matrix'}), 500
    
    @app.route('/achieveup/skills/assign', methods=['POST'])
    async def assign_skills():
        """Assign skills to quiz questions."""
        try:
            data = await request.get_json()
            course_id = data.get('course_id')
            question_skills = data.get('question_skills', {})
            
            if not course_id:
                return jsonify({'error': 'course_id is required'}), 400
            
            result = await assign_skills_to_questions(course_id, question_skills)
            return jsonify(result), 200
            
        except Exception as e:
            logger.error(f"Error assigning skills: {str(e)}")
            return jsonify({'error': 'Failed to assign skills'}), 500
    
    @app.route('/achieveup/skills/suggest', methods=['POST'])
    async def suggest_skills_endpoint():
        """Get skill suggestions for a question or topic."""
        try:
            data = await request.get_json()
            question_text = data.get('question_text')
            course_context = data.get('course_context', '')
            
            if not question_text:
                return jsonify({'error': 'question_text is required'}), 400
            
            suggestions = await suggest_skills(question_text, course_context)
            return jsonify({'suggestions': suggestions}), 200
            
        except Exception as e:
            logger.error(f"Error suggesting skills: {str(e)}")
            return jsonify({'error': 'Failed to suggest skills'}), 500
    
    @app.route('/achieveup/badges/generate', methods=['POST'])
    async def generate_badges_endpoint():
        """Generate badges for skill achievements."""
        try:
            data = await request.get_json()
            student_id = data.get('student_id')
            course_id = data.get('course_id')
            skill_levels = data.get('skill_levels', {})
            
            if not student_id or not course_id:
                return jsonify({'error': 'student_id and course_id are required'}), 400
            
            badges = await generate_badges(student_id, course_id, skill_levels)
            return jsonify({'badges': badges}), 200
            
        except Exception as e:
            logger.error(f"Error generating badges: {str(e)}")
            return jsonify({'error': 'Failed to generate badges'}), 500
    
    @app.route('/achieveup/badges/<student_id>', methods=['GET'])
    async def get_student_badges(student_id):
        """Get all badges for a specific student."""
        try:
            badges = await badges_collection.find({'student_id': student_id}).to_list(length=100)
            
            # Convert ObjectIds to strings for JSON serialization
            for badge in badges:
                badge['_id'] = str(badge['_id'])
            
            return jsonify({'badges': badges}), 200
            
        except Exception as e:
            logger.error(f"Error retrieving badges: {str(e)}")
            return jsonify({'error': 'Failed to retrieve badges'}), 500
    
    @app.route('/achieveup/progress/<student_id>/<course_id>', methods=['GET'])
    async def get_progress(student_id, course_id):
        """Get skill progress for a student in a specific course."""
        try:
            progress = await get_skill_progress(student_id, course_id)
            return jsonify(progress), 200
            
        except Exception as e:
            logger.error(f"Error retrieving progress: {str(e)}")
            return jsonify({'error': 'Failed to retrieve progress'}), 500
    
    @app.route('/achieveup/progress/update', methods=['POST'])
    async def update_progress():
        """Update skill progress for a student."""
        try:
            data = await request.get_json()
            student_id = data.get('student_id')
            course_id = data.get('course_id')
            skill_updates = data.get('skill_updates', {})
            
            if not student_id or not course_id:
                return jsonify({'error': 'student_id and course_id are required'}), 400
            
            result = await update_skill_assessment(student_id, course_id, skill_updates)
            return jsonify(result), 200
            
        except Exception as e:
            logger.error(f"Error updating progress: {str(e)}")
            return jsonify({'error': 'Failed to update progress'}), 500
    
    @app.route('/achieveup/graphs/individual/<student_id>', methods=['GET'])
    async def get_individual_graphs(student_id):
        """Generate individual skill graphs for a student."""
        try:
            graphs = await create_individual_graphs(student_id)
            return jsonify({'graphs': graphs}), 200
            
        except Exception as e:
            logger.error(f"Error generating graphs: {str(e)}")
            return jsonify({'error': 'Failed to generate graphs'}), 500
    
    @app.route('/achieveup/export/<course_id>', methods=['GET'])
    async def export_course_data(course_id):
        """Export all AchieveUp data for a course."""
        try:
            # Get all data for the course
            matrices = await skill_matrices_collection.find({'course_id': course_id}).to_list(length=100)
            badges = await badges_collection.find({'course_id': course_id}).to_list(length=100)
            progress = await skill_progress_collection.find({'course_id': course_id}).to_list(length=100)
            
            # Convert ObjectIds to strings
            for item in matrices + badges + progress:
                item['_id'] = str(item['_id'])
            
            export_data = {
                'course_id': course_id,
                'skill_matrices': matrices,
                'badges': badges,
                'skill_progress': progress
            }
            
            return jsonify(export_data), 200
            
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            return jsonify({'error': 'Failed to export data'}), 500
    
    @app.route('/achieveup/import', methods=['POST'])
    async def import_course_data():
        """Import AchieveUp data for a course."""
        try:
            data = await request.get_json()
            course_id = data.get('course_id')
            import_data = data.get('data', {})
            
            if not course_id:
                return jsonify({'error': 'course_id is required'}), 400
            
            # Import matrices
            if 'skill_matrices' in import_data:
                for matrix in import_data['skill_matrices']:
                    matrix['course_id'] = course_id
                    await skill_matrices_collection.insert_one(matrix)
            
            # Import badges
            if 'badges' in import_data:
                for badge in import_data['badges']:
                    badge['course_id'] = course_id
                    await badges_collection.insert_one(badge)
            
            # Import progress
            if 'skill_progress' in import_data:
                for progress in import_data['skill_progress']:
                    progress['course_id'] = course_id
                    await skill_progress_collection.insert_one(progress)
            
            return jsonify({'message': 'Data imported successfully'}), 200
            
        except Exception as e:
            logger.error(f"Error importing data: {str(e)}")
            return jsonify({'error': 'Failed to import data'}), 500 