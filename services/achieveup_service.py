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
client = AsyncIOMotorClient(
        Config.DB_CONNECTION_STRING,
        tlsAllowInvalidCertificates=(Config.ENV == 'development')
    )
db = client[Config.DATABASE]

# Collections
achieveup_skill_matrices_collection = db[Config.ACHIEVEUP_SKILL_MATRICES_COLLECTION]
achieveup_question_skills_collection = db[Config.ACHIEVEUP_QUESTION_SKILLS_COLLECTION]
achieveup_badges_collection = db[Config.ACHIEVEUP_BADGES_COLLECTION]
achieveup_progress_collection = db[Config.ACHIEVEUP_PROGRESS_COLLECTION]
achieveup_analytics_collection = db[Config.ACHIEVEUP_ANALYTICS_COLLECTION]

async def create_skill_matrix(token: str, course_id: str, matrix_name: str, skills: list) -> dict:
    """Create skill matrix for a course."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get user info and verify instructor access
        user = user_result['user']
        user_role = user['role']
        canvas_token_type = user.get('canvasTokenType', 'student')
        
        # Verify instructor access (consistent with other endpoints)
        if user_role != 'instructor' or canvas_token_type != 'instructor':
            return {
                'error': 'Access denied',
                'message': 'Instructor access required',
                'statusCode': 403
            }
        
        # Check if matrix name already exists for this course (allow multiple matrices per course)
        existing_matrix = await achieveup_skill_matrices_collection.find_one({
            'course_id': course_id, 
            'matrix_name': matrix_name
        })
        if existing_matrix:
            return {
                'error': 'Matrix name already exists',
                'message': f'A skill matrix with the name \'{matrix_name}\' already exists for this course',
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

async def get_all_skill_matrices_by_course(token: str, course_id: str) -> dict:
    """Get ALL skill matrices for a course (for frontend matrix selection)."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get user info from the correct structure
        user = user_result['user']
        user_id = user['id']
        user_role = user['role']
        canvas_token_type = user.get('canvasTokenType', 'student')
        
        # Verify instructor access (consistent with other endpoints)
        if user_role != 'instructor' or canvas_token_type != 'instructor':
            return {
                'error': 'Access denied',
                'message': 'Instructor access required',
                'statusCode': 403
            }
        
        # ENHANCED DEBUG LOGGING FOR MATRIX RETRIEVAL
        logger.info(f"DEBUG: Searching for matrices with course_id='{course_id}' (type: {type(course_id)})")
        
        # Try both string and exact matches to debug data type issues
        query_string = {'course_id': str(course_id)}
        query_exact = {'course_id': course_id}
        
        logger.info(f"DEBUG: Query 1 (string): {query_string}")
        matrices_string = await achieveup_skill_matrices_collection.find(query_string).to_list(length=None)
        logger.info(f"DEBUG: Found {len(matrices_string)} matrices with string course_id")
        
        logger.info(f"DEBUG: Query 2 (exact): {query_exact}")
        matrices_exact = await achieveup_skill_matrices_collection.find(query_exact).to_list(length=None)
        logger.info(f"DEBUG: Found {len(matrices_exact)} matrices with exact course_id")
        
        # Use string query as primary (most consistent)
        matrices = matrices_string
        
        # Log what we found
        for i, matrix in enumerate(matrices):
            logger.info(f"DEBUG: Matrix {i+1}: name='{matrix.get('matrix_name')}', course_id='{matrix.get('course_id')}' (type: {type(matrix.get('course_id'))})")
        
        # If no matrices found, check what matrices exist in database
        if len(matrices) == 0:
            logger.warning(f"DEBUG: No matrices found for course_id='{course_id}'. Checking all matrices...")
            all_matrices = await achieveup_skill_matrices_collection.find({}).to_list(length=None)
            logger.info(f"DEBUG: Total matrices in database: {len(all_matrices)}")
            for matrix in all_matrices:
                logger.info(f"DEBUG: Existing matrix: course_id='{matrix.get('course_id')}' (type: {type(matrix.get('course_id'))}), name='{matrix.get('matrix_name')}'")
        
        # Convert ObjectId to string for JSON serialization
        for matrix in matrices:
            if '_id' in matrix:
                matrix['_id'] = str(matrix['_id'])
        
        logger.info(f"DEBUG: Returning {len(matrices)} matrices for course {course_id}")
        
        return {
            'matrices': matrices,
            'count': len(matrices)
        }
        
    except Exception as e:
        logger.error(f"Get all skill matrices by course error: {str(e)}")
        import traceback
        traceback.print_exc()
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

async def create_instructor_skill_matrix(token: str, course_id: str, matrix_name: str, skills: list, quiz_questions: dict) -> dict:
    """Create skill matrix with quiz question mapping for instructor."""
    try:
        # Verify user token and instructor status
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        user_id = user_result['user']['id']
        client = AsyncIOMotorClient(
        Config.DB_CONNECTION_STRING,
        tlsAllowInvalidCertificates=(Config.ENV == 'development')
    )
        db = client[Config.DATABASE]
        user_doc = await db['AchieveUp_Users'].find_one({'user_id': user_id})
        if not user_doc or user_doc.get('canvas_token_type', 'student') != 'instructor':
            return {'error': 'Forbidden', 'message': 'Instructor token required', 'statusCode': 403}
        # Create matrix document
        matrix_id = str(uuid.uuid4())
        matrix_doc = {
            '_id': matrix_id,
            'course_id': course_id,
            'matrix_name': matrix_name,
            'skills': skills,
            'quiz_questions': quiz_questions,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'created_by': user_id
        }
        await db['AchieveUp_Skill_Matrices'].insert_one(matrix_doc)
        return matrix_doc
    except Exception as e:
        logger.error(f"Create instructor skill matrix error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_instructor_course_analytics(token: str, course_id: str) -> dict:
    """Get detailed analytics for instructor's course."""
    try:
        # Verify user token and instructor status
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        user_id = user_result['user']['id']
        client = AsyncIOMotorClient(
        Config.DB_CONNECTION_STRING,
        tlsAllowInvalidCertificates=(Config.ENV == 'development')
    )
        db = client[Config.DATABASE]
        user_doc = await db['AchieveUp_Users'].find_one({'user_id': user_id})
        if not user_doc or user_doc.get('canvas_token_type', 'student') != 'instructor':
            return {'error': 'Forbidden', 'message': 'Instructor token required', 'statusCode': 403}
        # Gather analytics data
        # Example: count students, average progress, skill distribution, risk students, top performers
        progress_cursor = db['AchieveUp_Progress'].find({'course_id': course_id})
        students = []
        skill_distribution = {}
        total_progress = 0
        total_students = 0
        risk_students = []
        top_performers = []
        async for doc in progress_cursor:
            students.append(doc['student_id'])
            total_students += 1
            # Calculate average progress (simple mean of all skill scores)
            if 'skill_progress' in doc:
                avg_score = sum([v['score'] for v in doc['skill_progress'].values()]) / max(len(doc['skill_progress']), 1)
                total_progress += avg_score
                # Skill distribution
                for skill, v in doc['skill_progress'].items():
                    skill_distribution.setdefault(skill, []).append(v['score'])
                # Risk students (example: avg_score < 50)
                if avg_score < 50:
                    risk_students.append(doc['student_id'])
                # Top performers (example: avg_score > 90)
                if avg_score > 90:
                    top_performers.append(doc['student_id'])
        average_progress = total_progress / max(total_students, 1)
        # Aggregate skill distribution
        skill_dist_summary = {k: sum(v)/len(v) if v else 0 for k, v in skill_distribution.items()}
        analytics = {
            'course_id': course_id,
            'total_students': total_students,
            'average_progress': average_progress,
            'skill_distribution': skill_dist_summary,
            'risk_students': risk_students,
            'top_performers': top_performers
        }
        return analytics
    except Exception as e:
        logger.error(f"Get instructor course analytics error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def analyze_questions(token: str, questions: list) -> dict:
    """Analyze question complexity and suggest skills for multiple questions."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        analysis_results = []
        
        for question in questions:
            question_id = question.get('id')
            question_text = question.get('text', '')
            
            if not question_id or not question_text:
                continue
            
            # Analyze question complexity
            complexity = analyze_question_complexity(question_text)
            
            # Get skill suggestions
            suggested_skills = await suggest_skills_for_question(token, question_text)
            
            # Calculate confidence score
            confidence = calculate_confidence_score(question_text, suggested_skills)
            
            analysis_results.append({
                'questionId': question_id,
                'complexity': complexity,
                'suggestedSkills': suggested_skills if isinstance(suggested_skills, list) else [],
                'confidence': confidence
            })
        
        return analysis_results
        
    except Exception as e:
        logger.error(f"Analyze questions error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_question_suggestions(token: str, question_id: str) -> dict:
    """Get AI-powered skill suggestions for a specific question."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get question data from demo service
        from services.achieveup_canvas_demo_service import get_demo_quiz_questions
        
        # Extract quiz_id from question_id (questions are typically named like quiz_demo_001_1_q1)
        # Try to find the question in demo data
        question_data = None
        course_id = None
        
        # Check all demo quizzes for this question
        demo_quizzes = {
            "quiz_demo_001_1": "demo_001",
            "quiz_demo_001_2": "demo_001", 
            "quiz_demo_002_1": "demo_002",
            "quiz_demo_003_1": "demo_003"
        }
        
        for quiz_id, cid in demo_quizzes.items():
            quiz_questions = await get_demo_quiz_questions(quiz_id)
            for q in quiz_questions:
                if q.get('id') == question_id or question_id in q.get('id', ''):
                    question_data = q
                    course_id = cid
                    break
            if question_data:
                break
        
        # If no specific question found, use question_id to determine context
        if not question_data:
            if 'demo_001' in question_id or 'web' in question_id.lower():
                course_id = 'demo_001'
            elif 'demo_002' in question_id or 'database' in question_id.lower() or 'sql' in question_id.lower():
                course_id = 'demo_002'
            elif 'demo_003' in question_id or 'network' in question_id.lower():
                course_id = 'demo_003'
            else:
                course_id = 'demo_001'  # Default to web development
        
        # Course-specific skill mappings
        course_skills = {
            'demo_001': [
                'HTML/CSS Fundamentals',
                'JavaScript Programming',
                'DOM Manipulation', 
                'Responsive Design',
                'Web APIs'
            ],
            'demo_002': [
                'SQL Fundamentals',
                'Database Design',
                'Data Normalization',
                'Query Optimization',
                'Stored Procedures'
            ],
            'demo_003': [
                'Network Protocols (TCP/IP)',
                'Network Security',
                'Routing & Switching',
                'Wireless Networks',
                'Network Troubleshooting'
            ]
        }
        
        available_skills = course_skills.get(course_id, course_skills['demo_001'])
        
        # Analyze question content for skill suggestions
        if question_data:
            question_text = question_data.get('question_text', '').lower()
            question_name = question_data.get('question_name', '').lower()
            content = f"{question_text} {question_name}"
        else:
            content = question_id.lower()
        
        # Smart skill mapping based on content analysis
        suggested_skills = []
        confidence_scores = []
        
        if course_id == 'demo_001':  # Web Development
            if any(keyword in content for keyword in ['javascript', 'js', 'variable', 'function', 'array', 'object']):
                suggested_skills.append('JavaScript Programming')
                confidence_scores.append(0.92)
            if any(keyword in content for keyword in ['css', 'html', 'style', 'layout', 'grid', 'flexbox', 'responsive']):
                suggested_skills.append('HTML/CSS Fundamentals')
                confidence_scores.append(0.88)
            if any(keyword in content for keyword in ['responsive', 'mobile', 'media', 'breakpoint']):
                suggested_skills.append('Responsive Design')
                confidence_scores.append(0.85)
            if any(keyword in content for keyword in ['dom', 'element', 'event', 'manipulation']):
                suggested_skills.append('DOM Manipulation')
                confidence_scores.append(0.90)
            if any(keyword in content for keyword in ['api', 'fetch', 'ajax', 'request', 'response']):
                suggested_skills.append('Web APIs')
                confidence_scores.append(0.87)
                
        elif course_id == 'demo_002':  # Database
            if any(keyword in content for keyword in ['select', 'insert', 'update', 'delete', 'sql']):
                suggested_skills.append('SQL Fundamentals')
                confidence_scores.append(0.95)
            if any(keyword in content for keyword in ['table', 'schema', 'design', 'entity', 'relationship']):
                suggested_skills.append('Database Design')
                confidence_scores.append(0.88)
            if any(keyword in content for keyword in ['normal', '1nf', '2nf', '3nf', 'bcnf']):
                suggested_skills.append('Data Normalization')
                confidence_scores.append(0.92)
            if any(keyword in content for keyword in ['index', 'optimize', 'performance', 'query plan']):
                suggested_skills.append('Query Optimization')
                confidence_scores.append(0.85)
            if any(keyword in content for keyword in ['procedure', 'function', 'trigger', 'stored']):
                suggested_skills.append('Stored Procedures')
                confidence_scores.append(0.90)
                
        elif course_id == 'demo_003':  # Networking
            if any(keyword in content for keyword in ['tcp', 'ip', 'protocol', 'packet', 'routing']):
                suggested_skills.append('Network Protocols (TCP/IP)')
                confidence_scores.append(0.93)
            if any(keyword in content for keyword in ['security', 'firewall', 'encryption', 'vpn']):
                suggested_skills.append('Network Security')
                confidence_scores.append(0.89)
            if any(keyword in content for keyword in ['router', 'switch', 'routing', 'switching']):
                suggested_skills.append('Routing & Switching')
                confidence_scores.append(0.91)
            if any(keyword in content for keyword in ['wireless', 'wifi', '802.11', 'bluetooth']):
                suggested_skills.append('Wireless Networks')
                confidence_scores.append(0.86)
            if any(keyword in content for keyword in ['troubleshoot', 'debug', 'diagnose', 'problem']):
                suggested_skills.append('Network Troubleshooting')
                confidence_scores.append(0.84)
        
        # If no specific matches, suggest 2-3 most relevant skills for the course
        if not suggested_skills:
            suggested_skills = available_skills[:3]
            confidence_scores = [0.75, 0.70, 0.65]
        
        # Limit to top 3 suggestions
        if len(suggested_skills) > 3:
            # Sort by confidence and take top 3
            skill_confidence_pairs = list(zip(suggested_skills, confidence_scores))
            skill_confidence_pairs.sort(key=lambda x: x[1], reverse=True)
            suggested_skills = [pair[0] for pair in skill_confidence_pairs[:3]]
            confidence_scores = [pair[1] for pair in skill_confidence_pairs[:3]]
        
        # Calculate overall confidence
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.75
        
        return {
            'suggestions': suggested_skills,
            'confidence': round(overall_confidence, 2),
            'course_id': course_id,
            'available_skills': available_skills
        }
        
    except Exception as e:
        logger.error(f"Get question suggestions error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

def analyze_question_complexity(question_text: str) -> str:
    """Analyze the complexity of a question based on its content."""
    question_lower = question_text.lower()
    
    # Simple complexity analysis based on keywords and length
    complexity_indicators = {
        'low': ['what is', 'define', 'list', 'name', 'identify', 'simple', 'basic'],
        'medium': ['explain', 'describe', 'compare', 'analyze', 'evaluate', 'discuss'],
        'high': ['synthesize', 'create', 'design', 'develop', 'implement', 'solve complex']
    }
    
    score = 0
    for level, indicators in complexity_indicators.items():
        for indicator in indicators:
            if indicator in question_lower:
                if level == 'low':
                    score += 1
                elif level == 'medium':
                    score += 2
                elif level == 'high':
                    score += 3
    
    # Consider question length
    if len(question_text) > 200:
        score += 1
    elif len(question_text) > 100:
        score += 0.5
    
    # Determine complexity level
    if score >= 3:
        return 'high'
    elif score >= 1.5:
        return 'medium'
    else:
        return 'low'

def calculate_confidence_score(question_text: str, suggested_skills: list) -> float:
    """Calculate confidence score for skill suggestions."""
    if not suggested_skills:
        return 0.0
    
    # Simple confidence calculation based on skill count and question length
    base_confidence = min(len(suggested_skills) * 0.2, 0.8)
    
    # Adjust based on question length (longer questions might have more context)
    length_factor = min(len(question_text) / 500, 0.2)
    
    return min(base_confidence + length_factor, 1.0)
 
async def get_instructor_dashboard(token: str) -> dict:
    """Get instructor dashboard data with course overview and analytics."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result['user']['id']
        
        # Get instructor's Canvas courses
        from services.achieveup_canvas_service import get_instructor_courses
        from services.achieveup_auth_service import get_user_canvas_token
        
        canvas_token = await get_user_canvas_token(user_id)
        if not canvas_token:
            return {
                'error': 'No Canvas token',
                'message': 'No Canvas API token found for user',
                'statusCode': 400
            }
        
        courses_result = await get_instructor_courses(canvas_token)
        if 'error' in courses_result:
            return courses_result
        
        courses = courses_result if isinstance(courses_result, list) else []
        
        # Get skill matrices count
        matrices_count = await achieveup_skill_matrices_collection.count_documents({})
        
        # Get recent activity
        recent_matrices = await achieveup_skill_matrices_collection.find({}).sort([('created_at', -1)]).limit(5).to_list(length=5)
        
        dashboard_data = {
            'courses': courses,
            'totalCourses': len(courses),
            'totalSkillMatrices': matrices_count,
            'recentMatrices': recent_matrices,
            'lastUpdated': datetime.utcnow().isoformat()
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Get instructor dashboard error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_instructor_course_students(token: str, course_id: str) -> dict:
    """Get list of students in instructor's course."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        user_id = user_result['user']['id']
        
        # Get Canvas API token
        from services.achieveup_auth_service import get_user_canvas_token
        canvas_token = await get_user_canvas_token(user_id)
        if not canvas_token:
            return {
                'error': 'No Canvas token',
                'message': 'No Canvas API token found for user',
                'statusCode': 400
            }
        
        # Get students from Canvas
        from services.achieveup_canvas_service import get_course_students
        students_result = await get_course_students(canvas_token, course_id)
        
        return students_result
        
    except Exception as e:
        logger.error(f"Get instructor course students error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def get_instructor_student_analytics(token: str, course_id: str) -> dict:
    """Get student analytics for instructor's course."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get students for the course
        students_result = await get_instructor_course_students(token, course_id)
        if 'error' in students_result:
            return students_result
        
        students = students_result if isinstance(students_result, list) else []
        
        # Get skill matrix for course
        skill_matrix = await achieveup_skill_matrices_collection.find_one({'course_id': course_id})
        
        # Get progress data for students
        student_analytics = []
        for student in students:
            student_id = student.get('id')
            progress_data = await achieveup_progress_collection.find({'student_id': student_id, 'course_id': course_id}).to_list(length=None)
            
            analytics = {
                'studentId': student_id,
                'studentName': student.get('name', 'Unknown'),
                'email': student.get('email', ''),
                'progressCount': len(progress_data),
                'skillsCompleted': len([p for p in progress_data if p.get('completed', False)]),
                'lastActivity': max([p.get('updated_at', datetime.min) for p in progress_data] + [datetime.min])
            }
            student_analytics.append(analytics)
        
        return {
            'courseId': course_id,
            'totalStudents': len(students),
            'skillMatrix': skill_matrix,
            'studentAnalytics': student_analytics,
            'generatedAt': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get instructor student analytics error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def suggest_course_skills_ai(token: str, course_data: dict) -> dict:
    """Generate AI-powered skill suggestions for a course."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Import AI service
        from services.achieveup_ai_service import suggest_skills_for_course
        
        # Generate skills
        skills = await suggest_skills_for_course(course_data)
        
        return {
            'courseId': course_data.get('courseId'),
            'courseName': course_data.get('courseName'),
            'suggestedSkills': skills,
            'generatedAt': datetime.utcnow().isoformat(),
            'method': 'ai' if any('relevance' in skill and skill['relevance'] > 0.85 for skill in skills) else 'fallback'
        }
        
    except Exception as e:
        logger.error(f"AI skill suggestion error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def analyze_questions_with_ai(token: str, questions: list) -> dict:
    """Analyze questions using AI for complexity and skill mapping."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Extract course_id from the questions context if available
        # Try to determine course from question IDs or request context
        course_id = None
        course_skills = []
        
        # Check if we can extract course from question IDs
        for question in questions:
            q_id = question.get('id', '')
            if 'demo_001' in q_id:
                course_id = 'demo_001'
                break
            elif 'demo_002' in q_id:
                course_id = 'demo_002'
                break
            elif 'demo_003' in q_id:
                course_id = 'demo_003'
                break
        
        # Get course skills from skill matrix if we have course_id
        if course_id:
            skill_matrix = await achieveup_skill_matrices_collection.find_one({'course_id': course_id})
            course_skills = skill_matrix.get('skills', []) if skill_matrix else []
        
        # Fallback: Use course-specific skills based on common patterns
        if not course_skills and course_id:
            course_skills_map = {
                'demo_001': ['HTML/CSS Fundamentals', 'JavaScript Programming', 'DOM Manipulation', 'Responsive Design', 'Web APIs'],
                'demo_002': ['SQL Fundamentals', 'Database Design', 'Data Normalization', 'Query Optimization', 'Stored Procedures'],
                'demo_003': ['Network Protocols (TCP/IP)', 'Network Security', 'Routing & Switching', 'Wireless Networks', 'Network Troubleshooting']
            }
            course_skills = course_skills_map.get(course_id, [])
        
        # If still no skills, try to infer from question content
        if not course_skills:
            all_text = ' '.join([q.get('text', '') + ' ' + q.get('id', '') for q in questions]).lower()
            if any(keyword in all_text for keyword in ['javascript', 'html', 'css', 'web', 'dom']):
                course_skills = ['HTML/CSS Fundamentals', 'JavaScript Programming', 'DOM Manipulation', 'Responsive Design', 'Web APIs']
            elif any(keyword in all_text for keyword in ['sql', 'database', 'table', 'query']):
                course_skills = ['SQL Fundamentals', 'Database Design', 'Data Normalization', 'Query Optimization', 'Stored Procedures']
            elif any(keyword in all_text for keyword in ['network', 'tcp', 'ip', 'router', 'protocol']):
                course_skills = ['Network Protocols (TCP/IP)', 'Network Security', 'Routing & Switching', 'Wireless Networks', 'Network Troubleshooting']
            else:
                course_skills = ['HTML/CSS Fundamentals', 'JavaScript Programming', 'DOM Manipulation', 'Responsive Design', 'Web APIs']  # Default to web dev
        
        # Import AI service
        from services.achieveup_ai_service import analyze_questions
        
        # Analyze questions with course skills context
        analysis_results = await analyze_questions(questions, course_skills)
        
        return {
            'totalQuestions': len(questions),
            'analyses': analysis_results,
            'generatedAt': datetime.utcnow().isoformat(),
            'course_id': course_id,
            'course_skills_used': course_skills
        }
        
    except Exception as e:
        logger.error(f"AI question analysis error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def bulk_assign_skills_with_ai(token: str, course_id: str, questions: list) -> dict:
    """Perform bulk skill assignment using AI."""
    try:
        # Verify user token
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get course skill matrix
        skill_matrix = await achieveup_skill_matrices_collection.find_one({'course_id': course_id})
        course_skills = skill_matrix.get('skills', []) if skill_matrix else []
        
        # Import AI service
        from services.achieveup_ai_service import bulk_assign_skills
        
        # Perform bulk assignment
        assignments = await bulk_assign_skills(course_id, None, questions, course_skills)
        
        # Store assignments in database
        for question_id, skills in assignments.items():
            if skills:  # Only store if there are skills assigned
                assignment_doc = {
                    'course_id': course_id,
                    'question_id': question_id,
                    'skills': skills,
                    'ai_generated': True,
                    'human_reviewed': False,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                # Upsert the assignment
                await achieveup_question_skills_collection.replace_one(
                    {'question_id': question_id},
                    assignment_doc,
                    upsert=True
                )
        
        return {
            'courseId': course_id,
            'assignedQuestions': len([q for q in assignments.values() if q]),
            'totalQuestions': len(questions),
            'assignments': assignments,
            'generatedAt': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Bulk AI skill assignment error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def analyze_questions_with_ai_instructor(token: str, questions: list) -> dict:
    """Instructor-specific question analysis with enhanced features."""
    try:
        # Verify user token and instructor role
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Enhanced analysis for instructors
        from services.achieveup_ai_service import analyze_questions
        
        analysis_results = await analyze_questions(questions)
        
        # Add instructor-specific insights
        complexity_distribution = {
            'low': len([a for a in analysis_results if a.get('complexity') == 'low']),
            'medium': len([a for a in analysis_results if a.get('complexity') == 'medium']),
            'high': len([a for a in analysis_results if a.get('complexity') == 'high'])
        }
        
        avg_confidence = sum([a.get('confidence', 0) for a in analysis_results]) / len(analysis_results) if analysis_results else 0
        
        return {
            'totalQuestions': len(questions),
            'analyses': analysis_results,
            'complexityDistribution': complexity_distribution,
            'averageConfidence': round(avg_confidence, 2),
            'recommendations': generate_instructor_recommendations(complexity_distribution, avg_confidence),
            'generatedAt': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Instructor AI question analysis error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

async def bulk_assign_skills_with_ai_instructor(token: str, course_id: str, questions: list) -> dict:
    """Instructor-specific bulk skill assignment with enhanced features."""
    try:
        # Verify user token and instructor role
        user_result = await achieveup_verify_token(token)
        if 'error' in user_result:
            return user_result
        
        # Get course skill matrix
        skill_matrix = await achieveup_skill_matrices_collection.find_one({'course_id': course_id})
        course_skills = skill_matrix.get('skills', []) if skill_matrix else []
        
        if not course_skills:
            return {
                'error': 'No skill matrix found',
                'message': 'Please create a skill matrix for this course first',
                'statusCode': 400
            }
        
        # Import AI service
        from services.achieveup_ai_service import bulk_assign_skills
        
        # Perform bulk assignment
        assignments = await bulk_assign_skills(course_id, None, questions, course_skills)
        
        # Store assignments with instructor tracking
        successful_assignments = 0
        for question_id, skills in assignments.items():
            if skills:
                assignment_doc = {
                    'course_id': course_id,
                    'question_id': question_id,
                    'skills': skills,
                    'ai_generated': True,
                    'human_reviewed': False,
                    'assigned_by_instructor': True,
                    'instructor_id': user_result['user']['id'],
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                await achieveup_question_skills_collection.replace_one(
                    {'question_id': question_id},
                    assignment_doc,
                    upsert=True
                )
                successful_assignments += 1
        
        # Generate skill usage statistics
        skill_usage = {}
        for skills in assignments.values():
            for skill in skills:
                skill_usage[skill] = skill_usage.get(skill, 0) + 1
        
        return {
            'courseId': course_id,
            'assignedQuestions': successful_assignments,
            'totalQuestions': len(questions),
            'assignments': assignments,
            'skillUsageStatistics': skill_usage,
            'availableSkills': course_skills,
            'assignmentSummary': {
                'fullyAssigned': len([q for q in assignments.values() if len(q) > 0]),
                'partiallyAssigned': len([q for q in assignments.values() if len(q) == 1]),
                'multipleSkills': len([q for q in assignments.values() if len(q) > 1]),
                'unassigned': len([q for q in assignments.values() if len(q) == 0])
            },
            'generatedAt': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Instructor bulk AI skill assignment error: {str(e)}")
        return {'error': 'Internal server error', 'statusCode': 500}

def generate_instructor_recommendations(complexity_dist: dict, avg_confidence: float) -> list:
    """Generate recommendations for instructors based on analysis results."""
    recommendations = []
    
    total_questions = sum(complexity_dist.values())
    if total_questions == 0:
        return recommendations
    
    # Complexity distribution recommendations
    high_ratio = complexity_dist['high'] / total_questions
    low_ratio = complexity_dist['low'] / total_questions
    
    if high_ratio > 0.6:
        recommendations.append({
            'type': 'complexity',
            'priority': 'medium',
            'message': 'Many questions are high complexity. Consider adding some lower complexity questions for skill building.'
        })
    elif low_ratio > 0.6:
        recommendations.append({
            'type': 'complexity',
            'priority': 'low',
            'message': 'Most questions are low complexity. Consider adding more challenging questions to assess higher-order thinking.'
        })
    
    # Confidence recommendations
    if avg_confidence < 0.6:
        recommendations.append({
            'type': 'confidence',
            'priority': 'high',
            'message': 'Low confidence in skill mapping. Consider reviewing question content or updating skill matrix.'
        })
    elif avg_confidence > 0.85:
        recommendations.append({
            'type': 'confidence',
            'priority': 'low',
            'message': 'High confidence in skill mapping. Questions align well with course skills.'
        })
    
    return recommendations
 