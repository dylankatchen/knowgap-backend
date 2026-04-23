# services/mastery_service.py

import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
from services.badge_service import generate_badges_for_user

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup
client = AsyncIOMotorClient(
    Config.DB_CONNECTION_STRING,
    tlsAllowInvalidCertificates=(Config.ENV == 'development')
)
db = client[Config.DATABASE]
mastery_collection = db[Config.ACHIEVEUP_STUDENT_SKILL_MASTERY_COLLECTION]
question_skills_collection = db[Config.ACHIEVEUP_QUESTION_SKILLS_COLLECTION] # Fixed collection name

async def update_student_mastery(submission_data: dict) -> None:
    """
    Update student skill mastery based on a processed quiz submission.
    
    Args:
        submission_data: Processed submission dictionary from canvas_submissions_service
    """
    try:
        student_id = submission_data.get('student_id')
        student_name = submission_data.get('student_name')
        course_id = submission_data.get('course_id')
        
        if not student_id or not course_id:
            logger.warning("Submission missing student_id or course_id, skipping mastery update")
            return

        # 1. Fetch Skill Assignments for this Course
        # Optimization: We could cache this or pass it in, but fetching here ensures freshness
        skill_assignments = {} # {question_id: [ {id: skill_id, name: skill_name, matrix_id: ...} ]}
        
        # Note: Using the corrected collection name here.
        # The schema in DB seems to be {question_id: ..., skills: [...]} or similar.
        # Based on skill_service.py: assign_skill_to_question upserts:
        # {'question_id': qid, 'matrix_id': mid, ...}
        # But wait, skill_service.py puts 'skill_id' directly in the doc: 
        # {'question_id': ..., 'skill_id': ..., 'matrix_id': ...}
        # So one document per assignment.
        
        # Let's query all assignments for questions in this submission
        question_ids = [q['question_id'] for q in submission_data.get('questions', [])]
        
        if not question_ids:
            return

        cursor = question_skills_collection.find({'question_id': {'$in': question_ids}})
        
        # Helper to group skills by question
        question_skills_map = {} # {question_id: [ {skill_id, matrix_id} ]}

        async for doc in cursor:
            q_id = doc.get('question_id')
            skills = doc.get('skills', [])
            m_id = doc.get('matrix_id') or "primary" # Use a default matrix ID if missing
            
            if q_id not in question_skills_map:
                question_skills_map[q_id] = []
            
            # The schema uses a list of skill names/IDs
            if isinstance(skills, list):
                for s_id in skills:
                    question_skills_map[q_id].append({
                        'skill_id': s_id,
                        'matrix_id': m_id
                    })
            elif isinstance(doc.get('skill_id'), str):
                # Legacy fallback
                question_skills_map[q_id].append({
                    'skill_id': doc.get('skill_id'),
                    'matrix_id': m_id
                })

        # 2. Aggregation Logic
        # We need to calculate the delta or just increment?
        # A simple increment approach works if we process each submission EXACTLY ONCE.
        # But if we re-sync, we might double count.
        # To avoid double counting, we should ideally not use $inc if we are re-processing.
        # BUT, effectively managing "already processed" state for every single question attempts is hard.
        
        # ALTERNATIVE:
        # Since we are aggregating "Cumulative Performance", maybe we should just store the "stats" 
        # and re-calculate mastery specific to this submission's contribution?
        # 
        # Actually, the requirement is "efficiently get data ... without bloating DB".
        # 
        # ROBUST APPROACH:
        # Iterate over questions in submission.
        # identifying (student, course, skill) tuples.
        # Update the aggregated document.
        
        updates = {} # {(skill_id, matrix_id): {'correct': 0, 'total': 0}}
        
        for question in submission_data.get('questions', []):
            q_id = question.get('question_id')
            is_correct = question.get('correct', False)
            
            if q_id in question_skills_map:
                for skill_info in question_skills_map[q_id]:
                    key = (skill_info['skill_id'], skill_info['matrix_id'])
                    if key not in updates:
                        updates[key] = {'correct': 0, 'total': 0}
                    
                    updates[key]['total'] += 1
                    if is_correct:
                        updates[key]['correct'] += 1
                        
        # 3. Perform Bulk Updates (or individual updates)
        # We use $inc to add to the existing totals. 
        # NOTE: This assumes we only call this ONCE per submission attempt.
        # The sync logic in canvas_submissions_service should handle "new" submissions only 
        # or we accept that fully re-syncing a course might not be supported without wiping mastery first.
        # Given the prompt, let's assume incremental updates for new submissions.
        
        for (skill_id, matrix_id), stats in updates.items():
            filter_query = {
                'student_id': student_id,
                'course_id': course_id,
                'skill_id': skill_id,
                'matrix_id': matrix_id
            }
            
            update_query = {
                '$inc': {
                    'total_correct': stats['correct'],
                    'total_attempted': stats['total']
                },
                '$set': {
                    'skill_name': skill_id,
                    'last_updated': datetime.utcnow()
                }
            }
            
            # Upsert the mastery record
            await mastery_collection.update_one(filter_query, update_query, upsert=True)
            
            # 4. Check for Badges immediately
            # We need to fetch the updated doc to check percentage
            updated_doc = await mastery_collection.find_one(filter_query)
            if updated_doc:
                curr_correct = updated_doc.get('total_correct', 0)
                curr_total = updated_doc.get('total_attempted', 0)
                
                if curr_total > 0:
                    percentage = (curr_correct / curr_total) * 100
                    
                    # Store computed percentage for easy access
                    await mastery_collection.update_one(
                        {'_id': updated_doc['_id']},
                        {'$set': {'mastery_percentage': percentage}}
                    )

                    # Trigger badge generation check
                    # We can reuse or adapt badge_service logic.
                    # Since badge_service currently iterates ALL usage, let's call a specific check 
                    # or just let the batch process handle it?
                    # The prompt asked for "efficiently ... award badges".
                    # Let's call a helper to check this specific skill badge.
                    
                    await check_and_award_badge(student_id, course_id, skill_id, percentage, student_name)

    except Exception as e:
        logger.error(f"Error updating student mastery: {str(e)}")


async def check_and_award_badge(user_id: str, course_id: str, skill_id: str, percentage: float, student_name: str = None):
    """
    Check if a student earns a badge for a specific skill based on percentage.
    """
    from services.badge_service import (
        get_current_badge_level, 
        achieveup_user_badges_collection
    )
    
    badge_level = get_current_badge_level(percentage)
    if badge_level == 'none':
        return

    # Check if they already have this badge
    existing = await achieveup_user_badges_collection.find_one({
        'user_id': user_id,
        'skill_id': skill_id,
        'badge_level': badge_level,
        'course_id': course_id
    })
    
    if not existing:
        # Award new badge!
        # We need skill name for the badge. Fetch it from matrix or mastery doc (if cached).
        # For efficiency, we might just query the matrix collection lightly.
        
        # ... logic to insert badge ...
        # For now, let's defer to the existing badge_service generation 
        # OR just insert it here directly to avoid circular dependency complex logic.
        
        # NOTE: To keep it clean, we should expose a 'award_badge_single' in badge_service
        # But to avoid circular imports if badge_service imports this, be careful.
        # badge_service imports: auth, config. 
        # This imports: badge_service. 
        # It's fine if we import inside the function.
        
        from services.badge_service import create_badge_for_student
        await create_badge_for_student(user_id, course_id, skill_id, badge_level, percentage, student_name)

