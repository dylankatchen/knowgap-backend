# services/skill_service.py

import logging
import uuid
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from services.achieveup_auth_service import achieveup_verify_token
from config import Config
from openai import AsyncOpenAI


# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup for AchieveUp skill data (separate from KnowGap)
client = AsyncIOMotorClient(
        Config.DB_CONNECTION_STRING,
        tlsAllowInvalidCertificates=(Config.ENV == 'development')
    )
db = client[Config.DATABASE]
achieveup_skill_matrices_collection = db[Config.ACHIEVEUP_SKILL_MATRICES_COLLECTION]
achieveup_skill_assignments_collection = db[Config.ACHIEVEUP_SKILL_ASSIGNMENTS_COLLECTION]

async def create_skill_matrix(token: str, data: dict) -> dict:
    """Create a new skill matrix for a course."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        course_id = data.get('course_id')
        matrix_name = data.get('name')
        skills = data.get('skills', [])
        
        if not course_id or not matrix_name:
            return {
                'error': 'Missing required fields',
                'message': 'Course ID and matrix name are required',
                'statusCode': 400
            }
        

        # Create skill matrix document

        matrix_id = str(uuid.uuid4())
        matrix_doc = {
            'matrix_id': matrix_id,
            'course_id': course_id,
            'name': matrix_name,
            'skills': skills,
            'created_by': user_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert into database
        await achieveup_skill_matrices_collection.insert_one(matrix_doc)
        
        return {
            'matrix_id': matrix_id,
            'message': 'Skill matrix created successfully',
            'matrix': matrix_doc
        }
        
    except Exception as e:
        logger.error(f"Create skill matrix error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_skill_matrix(token: str, matrix_id: str) -> dict:
    """Get a specific skill matrix."""
    try:
        # Verify token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Find matrix in database
        matrix = await achieveup_skill_matrices_collection.find_one({'matrix_id': matrix_id})
        
        if not matrix:
            return {
                'error': 'Matrix not found',
                'message': 'Skill matrix not found',
                'statusCode': 404
            }
        
        # Remove MongoDB _id field
        matrix.pop('_id', None)
        
        return {'matrix': matrix}
        
    except Exception as e:
        logger.error(f"Get skill matrix error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def update_skill_matrix(token: str, matrix_id: str, data: dict) -> dict:
    """Update a skill matrix."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        
        # Check if matrix exists and user has permission
        matrix = await achieveup_skill_matrices_collection.find_one({'matrix_id': matrix_id})
        if not matrix:
            return {
                'error': 'Matrix not found',
                'message': 'Skill matrix not found',
                'statusCode': 404
            }
        
        if matrix.get('created_by') != user_id:
            return {
                'error': 'Unauthorized',
                'message': 'You can only update your own skill matrices',
                'statusCode': 403
            }
        
        # Prepare update data
        update_data = {
            'updated_at': datetime.utcnow()
        }
        
        if 'name' in data:
            update_data['name'] = data['name']
        if 'skills' in data:
            update_data['skills'] = data['skills']
        
        # Update in database
        await achieveup_skill_matrices_collection.update_one(
            {'matrix_id': matrix_id},
            {'$set': update_data}
        )
        
        # Get updated matrix
        updated_matrix = await achieveup_skill_matrices_collection.find_one({'matrix_id': matrix_id})
        updated_matrix.pop('_id', None)
        
        return {
            'message': 'Skill matrix updated successfully',
            'matrix': updated_matrix
        }
        
    except Exception as e:
        logger.error(f"Update skill matrix error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def delete_skill_matrix(token: str, matrix_id: str) -> dict:
    """Delete a skill matrix."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        
        # Check if matrix exists and user has permission
        matrix = await achieveup_skill_matrices_collection.find_one({'matrix_id': matrix_id})
        if not matrix:
            return {
                'error': 'Matrix not found',
                'message': 'Skill matrix not found',
                'statusCode': 404
            }
        
        if matrix.get('created_by') != user_id:
            return {
                'error': 'Unauthorized',
                'message': 'You can only delete your own skill matrices',
                'statusCode': 403
            }
        
        # Delete from database
        await achieveup_skill_matrices_collection.delete_one({'matrix_id': matrix_id})
        
        # Also delete related skill assignments
        await achieveup_skill_assignments_collection.delete_many({'matrix_id': matrix_id})
        
        return {'message': 'Skill matrix deleted successfully'}
        
    except Exception as e:
        logger.error(f"Delete skill matrix error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_course_skill_matrices(token: str, course_id: str) -> dict:
    """Get all skill matrices for a course."""
    try:
        # Verify token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Find all matrices for the course
        matrices = []
        async for matrix in achieveup_skill_matrices_collection.find({'course_id': course_id}):
            matrix.pop('_id', None)
            matrices.append(matrix)
        
        return {'matrices': matrices}
        
    except Exception as e:
        logger.error(f"Get course skill matrices error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def assign_skill_to_question(token: str, data: dict) -> dict:
    """Assign a skill to a quiz question."""
    try:
        # Verify token and get user info
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result.get('user_id')
        question_id = data.get('question_id')
        skill_id = data.get('skill_id')
        matrix_id = data.get('matrix_id')
        
        if not question_id or not skill_id or not matrix_id:
            return {
                'error': 'Missing required fields',
                'message': 'Question ID, skill ID, and matrix ID are required',
                'statusCode': 400
            }
        
        # Check if matrix exists and user has permission
        matrix = await achieveup_skill_matrices_collection.find_one({'matrix_id': matrix_id})
        if not matrix:
            return {
                'error': 'Matrix not found',
                'message': 'Skill matrix not found',
                'statusCode': 404
            }
        
        if matrix.get('created_by') != user_id:
            return {
                'error': 'Unauthorized',
                'message': 'You can only assign skills to your own matrices',
                'statusCode': 403
            }
        
        # Check if skill exists in matrix
        skill_exists = any(skill.get('id') == skill_id for skill in matrix.get('skills', []))
        if not skill_exists:
            return {
                'error': 'Skill not found',
                'message': 'Skill not found in matrix',
                'statusCode': 404
            }
        
        # Create or update assignment
        assignment_doc = {
            'question_id': question_id,
            'skill_id': skill_id,
            'matrix_id': matrix_id,
            'assigned_by': user_id,
            'assigned_at': datetime.utcnow()
        }
        
        await achieveup_skill_assignments_collection.update_one(
            {'question_id': question_id, 'matrix_id': matrix_id},
            {'$set': assignment_doc},
            upsert=True
        )
        
        return {
            'message': 'Skill assigned successfully',
            'assignment': assignment_doc
        }
        
    except Exception as e:
        logger.error(f"Assign skill to question error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_skill_suggestions(token: str, data: dict) -> dict:
    """Get AI-powered skill suggestions for a question."""
    #creating the client
    try:
        # Verify token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        question_text = data.get('question_text')
        course_id = data.get('course_id')
        
        if not question_text or not course_id:
            return {
                'error': 'Missing required fields',
                'message': 'Question text and course ID are required',
                'statusCode': 400
            }
        
        # Get course skill matrices
        matrices = []
        async for matrix in achieveup_skill_matrices_collection.find({'course_id': course_id}):
            matrices.append(matrix)
        
        if not matrices:
            return {
                'error': 'No skill matrices found',
                'message': 'No skill matrices found for this course',
                'statusCode': 404
            }
        
        # Simple keyword-based suggestion algorithm
        # In a real implementation, this would use AI/ML
        suggestions = []
        question_lower = question_text.lower()
        
        for matrix in matrices:
            for skill in matrix.get('skills', []):
                skill_name = skill.get('name', '').lower()
                skill_description = skill.get('description', '').lower()
                
                # Check if skill keywords appear in question
                if (skill_name in question_lower or 
                    any(keyword in question_lower for keyword in skill_name.split()) or
                    any(keyword in question_lower for keyword in skill_description.split())):
                    
                    suggestions.append({
                        'skill_id': skill.get('id'),
                        'skill_name': skill.get('name'),
                        'skill_description': skill.get('description'),
                        'matrix_id': matrix.get('matrix_id'),
                        'matrix_name': matrix.get('name'),
                        'confidence': 0.8  # Placeholder confidence score
                    })
        
        # Sort by confidence and limit results
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        suggestions = suggestions[:5]  # Top 5 suggestions
        
        return {
            'suggestions': suggestions,
            'question_text': question_text
        }
        
    except Exception as e:
        logger.error(f"Get skill suggestions error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500} 