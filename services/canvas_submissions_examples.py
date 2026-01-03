# services/canvas_submissions_service.py - Usage Examples

"""
Usage Examples for Canvas Submissions Service
==============================================

This file demonstrates how to use the Canvas submissions service
to fetch and process real student quiz data.
"""

# Example 1: Get a single student's quiz submission
async def example_get_student_submission():
    from services.canvas_submissions_service import get_student_quiz_submission
    
    canvas_token = "your_canvas_api_token"
    course_id = "12345"
    quiz_id = "67890"
    student_id = "54321"
    
    submission = await get_student_quiz_submission(
        canvas_token, course_id, quiz_id, student_id
    )
    
    if 'error' not in submission:
        print(f"Score: {submission.get('score')}")
        print(f"Questions answered: {len(submission.get('questions', []))}")

# Example 2: Get all submissions for a course quiz
async def example_get_all_submissions():
    from services.canvas_submissions_service import get_all_course_submissions
    
    canvas_token = "your_canvas_api_token"
    course_id = "12345"
    quiz_id = "67890"
    
    result = await get_all_course_submissions(canvas_token, course_id, quiz_id)
    
    if 'error' not in result:
        print(f"Total submissions: {result.get('count')}")
        for submission in result.get('submissions', []):
            print(f"Student {submission.get('user_id')}: {submission.get('score')}")

# Example 3: Get all submissions for a student in a course
async def example_get_student_course_submissions():
    from services.canvas_submissions_service import get_student_submissions_for_course
    
    token = "achieveup_auth_token"
    student_id = "54321"
    course_id = "12345"
    
    result = await get_student_submissions_for_course(token, student_id, course_id)
    
    if 'error' not in result:
        print(f"Total submissions: {result.get('total_submissions')}")
        for submission in result.get('submissions', []):
            print(f"Quiz {submission.get('quiz_id')}: {submission.get('score')}")

# Example 4: Sync all course submissions to cache
async def example_sync_course():
    from services.canvas_submissions_service import sync_course_submissions
    
    token = "achieveup_auth_token"
    course_id = "12345"
    
    result = await sync_course_submissions(token, course_id)
    
    if 'error' not in result:
        print(f"Synced {result.get('total_synced')} submissions")
        print(f"Errors: {result.get('total_errors')}")

# Example 5: Using with badge generation
async def example_badge_generation():
    from services.badge_service import generate_badges_for_user
    from services.canvas_submissions_service import sync_course_submissions
    
    token = "achieveup_auth_token"
    course_id = "12345"
    
    # First, sync submissions to ensure fresh data
    await sync_course_submissions(token, course_id)
    
    # Then generate badges based on real progress
    result = await generate_badges_for_user(token, {'course_id': course_id})
    
    if 'error' not in result:
        print(f"Generated {len(result.get('badges', []))} badges")
