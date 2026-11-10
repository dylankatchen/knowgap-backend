# services/analytics_service.py

import logging
from datetime import datetime, timezone
from services.skill_tiers import tier_for_score, is_mastered
from config import Config

from mongodb import get_db

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB setup for AchieveUp analytics data (separate from KnowGap)
db = get_db()

achieveup_user_badges_collection = db[Config.ACHIEVEUP_USER_BADGES_COLLECTION]


async def get_course_students_analytics(token: str, course_id: str, time_range: str = '30d', skill_id: str = None) -> dict:
    """Get comprehensive analytics for all students in a course."""
    try:
        # Class-wide data, so only an instructor who teaches (or taught) the
        # course. Checked first: Canvas lets students list their own roster.
        from services.achieveup_service import require_course_instructor
        _, error = await require_course_instructor(token, course_id, include_concluded=True)
        if error:
            return error

        # Use explicit collection names
        skill_matrices_collection = db[Config.ACHIEVEUP_SKILL_MATRICES_COLLECTION]
        mastery_collection = db[Config.ACHIEVEUP_STUDENT_SKILL_MASTERY_COLLECTION]

        # Fetch all quiz attempts for the course in one query
        all_quiz_attempts = await db["AchieveUp_Quiz_Attempts"].find({
            'course_id': course_id
        }).to_list(length=None)
        
        # Get students for the course
        from services.achieveup_service import get_instructor_course_students
        students_result = await get_instructor_course_students(token, course_id)
        if 'error' in students_result:
            return students_result
        
        students = students_result if isinstance(students_result, list) else []
        
        # Get all mapped skills for course from AchieveUp_Question_Skills
        question_skills_cursor = db[Config.ACHIEVEUP_QUESTION_SKILLS_COLLECTION].find({'course_ids': course_id})
        course_skills_set = set()
        async for qs in question_skills_cursor:
            for skill in qs.get('skills', []):
                if isinstance(skill, dict):
                    course_skills_set.add(skill.get('name', ''))
                else:
                    course_skills_set.add(skill)
        
        course_skills = list(course_skills_set)
        
        # Also check for skills that might exist in mastery collection but not question mappings (legacy data)
        mastery_skills_cursor = mastery_collection.distinct('skill_id', {'course_id': course_id})
        for skill in await mastery_skills_cursor:
            if skill not in course_skills:
                course_skills.append(skill)
        
        student_analytics = []
        skill_distribution = {}
        all_skill_scores = {}
        
        # Get all badge info for a class.
        class_badge_info = await achieveup_user_badges_collection.find(
            {"course_id": course_id},
            {"user_id": 1, "skill_id": 1, "badge_level": 1, "earned_at": 1}
        ).to_list(length=None)


        # Converting the list of class badges to a dictionary.
        badge_tiers: dict = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
        highest_badges: dict = {}
        for badge in class_badge_info:
            key = (badge.get("user_id"), badge.get("skill_id"))
            if not highest_badges.get(key) or (badge_tiers.get(badge.get("badge_level"), 0) > badge_tiers.get(highest_badges.get(key).get("badge_level"), 0)):
                highest_badges[key] = badge

        # Debug info tracking
        real_data_count = 0
        data_source = "real"

        for i, student in enumerate(students):
            student_id = student.get('id')
            
            # Get all mastery data for this student in this course
            mastery_data = await mastery_collection.find({
                'student_id': student_id,
                'course_id': course_id
            }).to_list(length=None)
            
            # Process real mastery data
            if mastery_data:
                real_data_count += len(mastery_data)
                data_source = "real"

            skill_breakdown = {}
            skill_scores = {}
            skills_mastered = 0
            
            # Create a lookup for mastery documents by skill_id
            mastery_lookup = {doc.get('skill_id'): doc for doc in mastery_data}
            
            for skill in course_skills:
                # Skill names might be objects or strings in some matrices
                # In the new system, they are objects: {"id": "...", "name": "...", "description": "..."}
                skill_id = skill.get('id') if isinstance(skill, dict) else skill
                skill_name = skill.get('name') if isinstance(skill, dict) else skill
                
                doc = mastery_lookup.get(skill_id)
                
                if doc:
                    score = doc.get('mastery_percentage', 0)
                    questions_attempted = doc.get('total_attempted', 0)
                    questions_correct = doc.get('total_correct', 0)

                    level = tier_for_score(score)
                    if is_mastered(score):
                        skills_mastered += 1

                    skill_breakdown[skill_name] = {
                        "score": round(score, 1),
                        "level": level,
                        "questionsAttempted": questions_attempted,
                        "questionsCorrect": questions_correct
                    }
                    skill_scores[skill_name] = score
                    
                    if skill_name not in skill_distribution:
                        skill_distribution[skill_name] = 0
                        all_skill_scores[skill_name] = []
                    skill_distribution[skill_name] += 1
                    all_skill_scores[skill_name].append(score)
                else:
                    skill_breakdown[skill_name] = {
                        "score": 0,
                        "level": tier_for_score(0),
                        "questionsAttempted": 0,
                        "questionsCorrect": 0
                    }
                    skill_scores[skill_name] = 0
                    
                    if skill_name not in skill_distribution:
                        skill_distribution[skill_name] = 0
                        all_skill_scores[skill_name] = []
                    skill_distribution[skill_name] += 1
                    all_skill_scores[skill_name].append(0)

                # Add badge info to the skills breakdown.
                badge = highest_badges.get((student_id, skill_id))
                if badge:
                    skill_breakdown[skill_name]["badgeLevel"] = badge.get("badge_level")
                    earned = badge.get("earned_at")
                    skill_breakdown[skill_name]["badgeEarnedAt"] = earned.isoformat() if hasattr(earned, "isoformat") else earned
            
            overall_progress = round(sum(skill_scores.values()) / len(skill_scores), 1) if skill_scores else 0
            risk_level = 'low' if overall_progress >= 75 else 'medium' if overall_progress >= 50 else 'high'

            # Count this student's actual earned badges (one per skill, at
            # its highest tier
            badges_earned = sum(1 for key in highest_badges if key[0] == student_id)
            
            student_analytics.append({
                'id': student_id,
                'name': student.get('name', 'Unknown'),
                'progress': overall_progress,
                'skillsMastered': skills_mastered,
                'badgesEarned': badges_earned,
                'riskLevel': risk_level,
                'skillBreakdown': skill_breakdown
            })
        
        # Calculate average scores for each skill
        average_scores = {s: round(sum(v)/len(v), 1) if v else 0 for s, v in all_skill_scores.items()}
        
        # Calculate assignment stats
        real_assignment_count = 0
        try:
            # Count assignments directly for this course in the new collection
            real_assignment_count = await db[Config.ACHIEVEUP_QUESTION_SKILLS_COLLECTION].count_documents({
                'course_ids': course_id
            })
            
            # Fallback to check old collection if no assignments found
            if real_assignment_count == 0:
                matrices = await db[Config.ACHIEVEUP_SKILL_MATRICES_COLLECTION].find({'course_id': course_id}).to_list(length=None)
                matrix_ids = [m.get('matrix_id') for m in matrices if m.get('matrix_id')]
                
                if matrix_ids:
                    real_assignment_count = await db[Config.ACHIEVEUP_SKILL_ASSIGNMENTS_COLLECTION].count_documents({
                        'matrix_id': {'$in': matrix_ids}
                    })
        except Exception as e:
            logger.error(f"Error counting assignments for debug: {str(e)}")

        response = {
            'analytics': {
                'students': student_analytics,
                'skillDistribution': skill_distribution,
                'averageScores': average_scores,
                'debug': {
                    'dataSource': data_source,
                    'realRecordCount': real_data_count,
                    'realAssignmentCount': real_assignment_count,
                    'queryCourseId': course_id,
                    'serverTime': datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
                }
            }
        }

        return response
        
    except Exception as e:
        logger.error(f"Get course students analytics error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': 'Internal server error', 'statusCode': 500}
