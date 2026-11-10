# services/mastery_service.py

import logging
import uuid
from datetime import datetime, timezone

from pymongo import UpdateOne

from config import Config
from mongodb import get_db
from utils.text_utils import normalize_text, hash_text

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup
db = get_db()

mastery_collection = db[Config.ACHIEVEUP_STUDENT_SKILL_MASTERY_COLLECTION]
question_skills_collection = db[Config.ACHIEVEUP_QUESTION_SKILLS_COLLECTION] # Fixed collection name

async def tally_submission(submission_data: dict) -> dict:
    """
    Count one processed quiz submission's answers per assigned skill.

    Returns {(skill_id, matrix_id): {'correct': n, 'total': n}}; empty when the
    submission has no questions or none are assigned a skill.
    """
    question_ids = [q['question_id'] for q in submission_data.get('questions', [])]
    if not question_ids:
        return {}

    question_skills_map = {}  # {question_id: [{skill_id, matrix_id}]}
    async for doc in question_skills_collection.find({'question_id': {'$in': question_ids}}):
        q_id = doc.get('question_id')
        m_id = doc.get('matrix_id') or "primary"  # Use a default matrix ID if missing
        skills = doc.get('skills', [])
        question_skills_map.setdefault(q_id, [])

        # The schema uses a list of skill names/IDs
        if isinstance(skills, list):
            for s_id in skills:
                question_skills_map[q_id].append({'skill_id': s_id, 'matrix_id': m_id})
        elif isinstance(doc.get('skill_id'), str):
            # Legacy fallback
            question_skills_map[q_id].append({'skill_id': doc.get('skill_id'), 'matrix_id': m_id})

    counts = {}
    for question in submission_data.get('questions', []):
        for skill_info in question_skills_map.get(question.get('question_id'), []):
            key = (skill_info['skill_id'], skill_info['matrix_id'])
            stats = counts.setdefault(key, {'correct': 0, 'total': 0})
            stats['total'] += 1
            if question.get('correct', False):
                stats['correct'] += 1
    return counts


class CourseMasteryTally:
    """
    A course's mastery totals, built in memory while a sync reads every
    submission, then swapped into the database in one step by
    replace_course_mastery. Readers never see a half-built course, and badges
    are judged on the final scores rather than on the first few quizzes.
    """

    def __init__(self):
        # {(student_id, skill_id, matrix_id): {'correct', 'total'}}
        self.totals = {}
        self.student_names = {}

    async def add_submission(self, submission_data: dict) -> None:
        student_id = submission_data.get('student_id')
        if not student_id:
            logger.warning("Submission missing student_id, skipping mastery update")
            return
        if submission_data.get('student_name'):
            self.student_names[student_id] = submission_data['student_name']

        # Errors propagate: a submission missing from the tally must fail the
        # sync rather than be swapped in as if the student never took it.
        counts = await tally_submission(submission_data)

        # No await below, so parallel submissions can't interleave these updates.
        for (skill_id, matrix_id), stats in counts.items():
            total = self.totals.setdefault((student_id, skill_id, matrix_id), {'correct': 0, 'total': 0})
            total['correct'] += stats['correct']
            total['total'] += stats['total']


async def replace_course_mastery(course_id: str, course_name: str, tally: CourseMasteryTally) -> int:
    """
    Make the tally the course's mastery data: one bulk write sets every
    (student, skill) total to its new value, then rows the tally no longer
    has (e.g. a skill unassigned since the last sync) are removed. Each row
    always holds a complete total, either the previous sync's or this one's.
    Then awards any badges the final scores earn. Returns the row count.
    """
    course_id = str(course_id)
    sync_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    operations = []
    percentages = {}
    for (student_id, skill_id, matrix_id), stats in tally.totals.items():
        percentage = (stats['correct'] / stats['total']) * 100 if stats['total'] > 0 else 0
        percentages[(student_id, skill_id)] = max(percentage, percentages.get((student_id, skill_id), 0))
        operations.append(UpdateOne(
            {'student_id': student_id, 'course_id': course_id, 'skill_id': skill_id, 'matrix_id': matrix_id},
            {'$set': {
                'skill_name': skill_id,
                'total_correct': stats['correct'],
                'total_attempted': stats['total'],
                'mastery_percentage': percentage,
                'sync_id': sync_id,
                'last_updated': now,
            }},
            upsert=True,
        ))

    if operations:
        await mastery_collection.bulk_write(operations, ordered=False)
    await mastery_collection.delete_many({'course_id': course_id, 'sync_id': {'$ne': sync_id}})

    for (student_id, skill_id), percentage in percentages.items():
        try:
            await check_and_award_badge(student_id, course_id, skill_id, percentage,
                                        tally.student_names.get(student_id), course_name)
        except Exception as e:
            logger.error(f"Error awarding badge to student {student_id} for skill {skill_id}: {str(e)}")

    return len(operations)


async def check_and_award_badge(user_id: str, course_id: str, skill_id: str, percentage: float, student_name: str = None, course_name: str = None):
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
        await create_badge_for_student(user_id, course_id, skill_id, badge_level, percentage, student_name, course_name)

