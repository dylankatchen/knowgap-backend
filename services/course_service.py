from motor.motor_asyncio import AsyncIOMotorClient
from utils.course_utils import get_quiz_questions, get_course_name, clean_text, get_incorrect_user_ids, get_quizzes
from config import Config
from utils.course_utils import (
    get_course_name, clean_text, get_incorrect_user_ids, get_quizzes
)
import aiohttp
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timezone
import traceback
import json  # Add this at the top if not present
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
db = client[Config.DATABASE]
course_contexts_collection = db[Config.CONTEXTS_COLLECTION]
students_collection = db[Config.STUDENTS_COLLECTION]
quizzes_collection = db[Config.QUIZZES_COLLECTION]

async def update_context(course_id, course_context,toggle_risk = True):
    """Updates or inserts the course context for a specific course."""
    try:
        result = await course_contexts_collection.update_one(
            {'course_id': course_id},
            {
                '$set': {
                    'course_id': course_id,
                    'course_context': course_context,
                }
            },
            upsert=True
        )
        status = 'Success' if result.modified_count > 0 or result.upserted_id else 'No changes made'
        return {'status': status, 'message': 'Course context updated successfully' if status == 'Success' else 'No updates applied'}
    except Exception as e:
        logger.error("Error updating course context: %s", e)
        return {'status': 'Error', 'message': str(e)}
    
#haley
async def update_course_risk_toggle(course_id,toggle_risk = True):
    """ Updates toggle on risk analysis"""
    try:
        result = await course_contexts_collection.update_one(
            {'course_id': course_id},
            {
                '$set': {
                    'toggle_risk': toggle_risk,
                }
            },
            upsert=True
        )
        status = 'Success' if result.modified_count > 0 or result.upserted_id else 'No changes made'
        return {'status': status, 'message': 'Course context updated successfully' if status == 'Success' else 'No updates applied'}
    except Exception as e:
        logger.error("Error updating toggle risk: %s", e)
        return {'status': 'Error', 'message': str(e)}
    
async def get_course_risk_toggle(course_id):
    """Updates or inserts the course context for a specific course."""
    try:
        doc = await course_contexts_collection.find_one({'course_id': course_id})
        
        if not doc:
            return {'toggle_risk': True, 'course_id': course_id}
        
        return {
            'toggle_risk': doc.get('toggle_risk', True),
            'course_id': course_id
        }
    except Exception as e:
        logger.error("Error getting risk toggle: %s", e)
        return {'status': 'Error', 'message': str(e)}
 

async def get_incorrect_question_data(courseid, currentquiz, access_token, link):
    """Fetches incorrect answer data for a specific quiz."""
    api_url = f'https://{link}/api/v1/courses/{courseid}/quizzes/{currentquiz}/questions'
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error("Failed to fetch quiz statistics: Status %s, Response: %s", response.status, error_text)
                    return {'error': f'Failed to fetch data from API: {error_text}'}, response.status
                
                # Attempt to parse JSON response
                try:
                    data = await response.json()
                except Exception as e:
                    logger.error("Failed to parse JSON from API response: %s", e)
                    return {'error': f'Failed to parse JSON: {str(e)}'}, 500
                
                question_data = data
                question_texts, question_ids = [], []
                
                # Process each question in the statistics
                for question in question_data:
                    if "question_text" in question and "id" in question:
                        cleaned_text = BeautifulSoup(question["question_text"], "html.parser").get_text()
                        question_texts.append(clean_text(cleaned_text))
                        question_ids.append(question["id"])
                    else:
                        logger.warning("Question data missing required fields: %s", question)
                
                return [question_texts, question_ids]
    except Exception as e:
        logger.error("Error fetching incorrect question data: %s", e)
        return {'error': f'Exception occurred: {str(e)}'}, 500

async def sync_all_quizzes_questions(course_id, access_token, link):
    """Sync all quizzes and questions for a course into the database (instructor-only, heavy operation)."""
    clean_link = link.replace("https://", "").replace("http://", "")
    quizlist, quizname = await get_quizzes(course_id, access_token, clean_link)
    db_quiz_ids = set()
    async for doc in quizzes_collection.find({'courseid': str(course_id)}, {'quizid': 1}):
        db_quiz_ids.add(doc.get('quizid'))
    semaphore = asyncio.Semaphore(3)
    async def limited_get_quiz_questions(course_id, quiz_id, access_token, clean_link):
        async with semaphore:
            return await get_quiz_questions(course_id, quiz_id, access_token, clean_link)
    quiz_ids_to_add = [quiz_id for quiz_id in quizlist if quiz_id not in db_quiz_ids]
    tasks = [limited_get_quiz_questions(course_id, quiz_id, access_token, clean_link) for quiz_id in quiz_ids_to_add]
    questions_results = await asyncio.gather(*tasks)
    for quiz_id, questions in zip(quiz_ids_to_add, questions_results):
        if not questions:
            continue
        course_name = await get_course_name(course_id, access_token, clean_link)
        quiz_title = quizname.get(str(quiz_id), 'Unknown Quiz')
        db_question_ids = set()
        async for doc in quizzes_collection.find({'courseid': str(course_id), 'quizid': int(quiz_id)}, {'questionid': 1}):
            db_question_ids.add(str(doc.get('questionid')))
        for question in questions:
            if str(question["id"]) not in db_question_ids:
                try:
                    question_text = BeautifulSoup(question["question_text"], "html.parser").get_text()
                    cleaned_text = clean_text(question_text)
                    await quizzes_collection.update_one(
                        {
                            'quizid': int(quiz_id),
                            'courseid': str(course_id),
                            'questionid': str(question["id"])
                        },
                        {
                            "$set": {
                                'course_name': course_name,
                                'quiz_name': quiz_title,
                                'question_text': cleaned_text,
                                'question_type': question.get("question_type", "unknown"),
                                'updated_at': datetime.now(timezone.utc)
                            }
                        },
                        upsert=True
                    )
                except Exception as e:
                    logger.info(f"Error adding question {question['id']} for quiz {quiz_id}: {e}")
                    continue
    return {'status': 'Success', 'message': 'All quizzes/questions synced'}

async def update_student_quiz_data(course_id, access_token, link, student_id=None):
    """Updates the database with quiz information and failed questions per student."""
    clean_link = link.replace("https://", "").replace("http://", "")
    try:
        # Always fetch quizlist and quizname for both instructor and student mode
        quizlist, quizname = await get_quizzes(course_id, access_token, clean_link)
        if student_id is None:
            # Only fetch quiz list, do not sync quizzes/questions in instructor mode
            return {'status': 'Success', 'message': 'Instructor sync: only fetched quiz list'}
        url = f"https://{clean_link}/api/v1/courses/{course_id}/enrollments"
        headers = {'Authorization': f'Bearer {access_token}'}
        studentmap = {}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch enrollments: {response.status}")
                    return {'status': 'Error', 'message': f'Failed to fetch enrollments: {response.status}'}
                enrollments = await response.json()
                # logger.info(f"Retrieved {len(enrollments)} enrollments from Canvas")
                # If student_id is provided, process only that student
                if student_id:
                    student_ids = [str(student_id)]
                else:
                    # Instructor/admin mode: process all students in the course
                    student_ids = [str(e.get('user_id')) for e in enrollments if e.get('type') == 'StudentEnrollment']
                # logger.info(f"Processing student IDs: {student_ids}")
        # For each student to process
        for sid in student_ids:
            # Ensure the student record has the course_id key
            student_record = await students_collection.find_one({'_id': str(sid)})
            if student_record is not None and str(course_id) not in student_record:
                await students_collection.update_one(
                    {'_id': str(sid)},
                    {"$set": {str(course_id): []}}
                )
            found = False
            user_role = None
            for enrollment in enrollments:
                if str(enrollment.get('user_id')) == str(sid):
                    found = True
                    user_role = enrollment.get('type')
                    # logger.info(f"Found student enrollment - ID: {sid}, Name: {enrollment.get('user', {}).get('name', 'Unknown')}, Role: {user_role}")
                    break
            if not found:
                logger.error(f"Student {sid} not found in course enrollments")
                continue
            # Process each quiz for this student
            for i, quiz_id in enumerate(quizlist):
                try:
                    quiz_title = quizname.get(str(quiz_id), 'Unknown Quiz')
                    # logger.info(f"Processing quiz {i+1}/{len(quizlist)}: {quiz_title}")
                    # For students, we need to fetch their submissions and then get questions
                    if user_role == 'StudentEnrollment':
                        # logger.info(f"Fetching student submission for quiz {quiz_id}")
                        submission_url = f"https://{clean_link}/api/v1/courses/{course_id}/quizzes/{quiz_id}/submissions"
                        async with aiohttp.ClientSession() as session:
                            async with session.get(submission_url, headers=headers) as sub_response:
                                if sub_response.status != 200:
                                    logger.error(f"Failed to fetch student submission for quiz {quiz_id}: {sub_response.status}")
                                    continue
                                submission_data = await sub_response.json()
                                # print(f"Submission data for quiz {quiz_id}, student {sid}: {submission_data}")
                                student_submission = None
                                for sub in submission_data.get('quiz_submissions', []):
                                    # print(f"Comparing sid: {sid} ({type(sid)}) with sub['user_id']: {sub.get('user_id')} ({type(sub.get('user_id'))})")
                                    if str(sub.get('user_id')) == str(sid):
                                        student_submission = sub
                                        # print(f"Found submission for student {sid} in quiz {quiz_id}")
                                        # logger.info(f"Student submission JSON for quiz {quiz_id}, student {sid}: {json.dumps(student_submission, indent=2)}")
                                        break
                                if not student_submission:
                                    # print(f"No submission found for student {sid} in quiz {quiz_id}")
                                    logger.warning(f"No submission found for student {sid} in quiz {quiz_id}")
                                    continue
                                # Try to fetch questions, but handle 403 gracefully
                                questions_url = f"https://{clean_link}/api/v1/courses/{course_id}/quizzes/{quiz_id}/questions"
                                async with aiohttp.ClientSession() as session2:
                                    async with session2.get(questions_url, headers=headers) as q_response:
                                        if q_response.status != 200:
                                            error_text = await q_response.text()
                                            logger.error(f"Failed to fetch questions for quiz {quiz_id}: {q_response.status}")
                                            logger.error(f"Error response: {error_text}")
                                            if q_response.status == 403:
                                                # logger.error(f"403 Forbidden - Access token may not have permission to view quiz questions")
                                                # logger.error(f"This could be due to:")
                                                # logger.error(f"1. Access token lacks 'url:GET|/api/v1/courses/:course_id/quizzes/:quiz_id/questions' scope")
                                                # logger.error(f"2. Quiz is unpublished or has restricted access")
                                                # logger.error(f"3. User role doesn't have permission to view quiz questions")
                                                # logger.warning(f"Skipping quiz {quiz_id} due to permissions - student will not get video recommendations for this quiz")
                                                # Alternative approach: Use submission data to infer incorrect answers
                                                # logger.info(f"Attempting alternative approach using submission data for quiz {quiz_id}")
                                                # Use correct field for points possible
                                                points_possible = student_submission.get('quiz_points_possible', 1)
                                                score = student_submission.get('score', 0)
                                                kept_score = student_submission.get('kept_score', 0)
                                                percentage = (kept_score / points_possible) * 100 if points_possible > 0 else 0
                                                # logger.info(f"Student {sid} scored {kept_score}/{points_possible} ({percentage:.1f}%) on quiz {quiz_title}")
                                                # Always add a quiz object for any found submission
                                                if sid not in studentmap:
                                                    studentmap[sid] = []
                                                studentmap[sid].append({
                                                    'quiz_name': quiz_title,
                                                    'quiz_id': quiz_id,
                                                    'questions': [],  # fallback: no specific questions
                                                    'used': False
                                                })
                                                # logger.info(f"[Fallback] Added quiz {quiz_title} for student {sid} (no question-level data)")
                                            continue
                                        questions_data = await q_response.json()
                                        question_map = {str(q['id']): q for q in questions_data}
                                        incorrect_questions = []
                                        for qid, answer in student_submission.get('answers', {}).items():
                                            qid_str = str(qid)
                                            question = question_map.get(qid_str)
                                            if not question:
                                                continue
                                            correct_answers = question.get('correct_answers', [])
                                            if not isinstance(correct_answers, list):
                                                correct_answers = [correct_answers]
                                            if answer not in correct_answers:
                                                incorrect_questions.append({
                                                    'question': BeautifulSoup(question.get('question_text', ''), 'html.parser').get_text(),
                                                    'question_id': qid_str
                                                })
                                        # Always add a quiz object if the student has a submission
                                        if sid not in studentmap:
                                            studentmap[sid] = []
                                        studentmap[sid].append({
                                            'quiz_name': quiz_title,
                                            'quiz_id': quiz_id,
                                            'questions': incorrect_questions,  # may be empty
                                            'used': False
                                        })
                                        # logger.info(f"Added quiz {quiz_title} for student {sid} with {len(incorrect_questions)} incorrect questions")
                    else:
                        # For instructors/admins, use quiz statistics
                        results = await update_quiz_reccs(course_id, quiz_id, access_token, clean_link)
                        if isinstance(results, dict) and 'error' in results:
                            logger.error(f"Error updating quiz recommendations for quiz {quiz_id}: {results['error']}")
                            continue
                        question_texts, selectors, question_ids = results
                        # logger.info(f"Found {len(question_texts)} questions for quiz {quiz_title}")
                        if sid not in studentmap:
                            studentmap[sid] = []
                        added_any = False
                        for j, user_ids in enumerate(selectors):
                            if str(sid) in [str(uid) for uid in user_ids]:
                                question_info = {
                                    "question": question_texts[j],
                                    "question_id": question_ids[j]
                                }
                                quiz_found = False
                                for quiz in studentmap[sid]:
                                    if quiz['quiz_name'] == quiz_title:
                                        existing_questions = {q['question_id'] for q in quiz['questions']}
                                        if question_info['question_id'] not in existing_questions:
                                            quiz['questions'].append(question_info)
                                            # logger.info(f"Added question {question_info['question_id']} to quiz {quiz_title} for student {sid}")
                                            added_any = True
                                        quiz_found = True
                                        break
                                if not quiz_found:
                                    studentmap[sid].append({
                                        "quiz_name": quiz_title,
                                        "quiz_id": quiz_id,
                                        "questions": [question_info],
                                        "used": False
                                    })
                                    # logger.info(f"Created new quiz entry {quiz_title} for student {sid} with question {question_info['question_id']}")
                                    added_any = True
                        if not added_any:
                            # logger.info(f"No incorrect questions found for student {sid} in quiz {quiz_title}")
                            pass
                except Exception as e:
                    # logger.error(f"Exception while processing quiz {quiz_id} for student {sid}: {str(e)}")
                    # logger.error(f"Full traceback for quiz {quiz_id} for student {sid}: {traceback.format_exc()}")
                    continue
            # Save to database for this student
            if sid in studentmap:
                try:
                    result = await students_collection.update_one(
                        {'_id': str(sid)},
                        {"$set": {str(course_id): studentmap[sid]}} ,
                        upsert=True
                    )
                    # logger.info(f"Updated quiz data for student {sid} - Modified: {result.modified_count}, Upserted: {result.upserted_id is not None}")
                    if not studentmap[sid]:
                        # logger.warning(f"Student {sid} has no quiz/question objects after update for course {course_id}")
                        pass
                except Exception as e:
                    # logger.error("Error updating database for student %s: %s", sid, e)
                    continue
        # Log summary of processing results
        # logger.info("=== Database Update Summary ===")
        # for sid in student_ids:
        #     if sid in studentmap:
        #         quiz_count = len(studentmap[sid])
        #         total_questions = sum(len(quiz.get('questions', [])) for quiz in studentmap[sid])
        #         logger.info(f"Student {sid}: {quiz_count} quizzes with {total_questions} total questions")
        #     else:
        #         logger.warning(f"Student {sid}: No quiz data processed")
        # logger.info("=== End Summary ===")
        return {'status': 'Success', 'message': 'Database update completed successfully'}
    except Exception as e:
        logger.error("Error in update_student_quiz_data: %s", e)
        return {'status': 'Error', 'error': str(e)}

async def update_quiz_questions_per_course(course_id, access_token, link):
    """Updates the database with quiz questions for a course."""
    try:
        # Clean the link to remove protocol
        clean_link = link.replace("https://", "").replace("http://", "")
        
        # Get quizzes for the course
        quizlist, quizname = await get_quizzes(course_id, access_token, clean_link)
        if not quizlist:
            # logger.warning(f"No quizzes found for course {course_id}")
            return {'status': 'Success', 'message': 'No quizzes found'}

        # Get course name
        course_name = await get_course_name(course_id, access_token, clean_link)
        if not course_name:
            # logger.error(f"Failed to get course name for course {course_id}")
            return {'status': 'Error', 'error': 'Failed to get course name'}

        # Process each quiz
        for quiz_id, quiz_title in zip(quizlist, quizname):
            try:
                # Get questions for this quiz
                questions = await get_quiz_questions(course_id, quiz_id, access_token, clean_link)
                if not questions:
                    # logger.warning(f"No questions found for quiz {quiz_id}")
                    continue

                # Save each question to the database
                for question in questions:
                    try:
                        # Clean question text
                        question_text = BeautifulSoup(question["question_text"], "html.parser").get_text()
                        cleaned_text = clean_text(question_text)

                        # Save to database
                        await quizzes_collection.update_one(
                            {
                                'quizid': int(quiz_id),
                                'courseid': str(course_id),
                                'questionid': str(question["id"])
                            },
                            {
                                "$set": {
                                    'course_name': course_name,
                                    'quiz_name': quiz_title,
                                    'question_text': cleaned_text,
                                    'question_type': question.get("question_type", "unknown"),
                                    'updated_at': datetime.now(timezone.utc)
                                }
                            },
                            upsert=True
                        )
                    except Exception as e:
                        # logger.error(f"Error saving question {question.get('id')} for quiz {quiz_id}: {e}")
                        continue

            except Exception as e:
                # logger.error(f"Error processing quiz {quiz_id}: {e}")
                if "403" in str(e):
                    # logger.error(f"Quiz {quiz_id} ({quiz_title}) is not accessible - likely due to permissions or quiz status")
                    # logger.error(f"Consider checking if the quiz is published and accessible to the current user role")
                    pass
                continue

        return {'status': 'Success', 'message': 'Quiz questions updated successfully'}

    except Exception as e:
        # logger.error(f"Error in update_quiz_questions_per_course: {e}")
        return {'status': 'Error', 'error': str(e)}

async def update_quiz_reccs(course_id, quiz_id, access_token, link):
    """Fetches quiz statistics to identify questions students answered incorrectly."""
    # Clean the link to remove protocol
    clean_link = link.replace("https://", "").replace("http://", "")
    
    url = f"https://{clean_link}/api/v1/courses/{course_id}/quizzes/{quiz_id}/statistics"
    headers = {'Authorization': f'Bearer {access_token}'}

    # logger.info(f"Fetching quiz statistics for quiz {quiz_id} in course {course_id}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response_text = await response.text()
                # logger.info(f"Quiz statistics API response status: {response.status}")
                # logger.info(f"Quiz statistics API response: {response_text[:500]}...")  # Log first 500 chars
                
                if response.status != 200:
                    # logger.error(f"Failed to fetch quiz statistics. Status: {response.status}, Error: {response_text}")
                    return {'error': f'Failed to fetch data from API: {response_text}'}

                data = await response.json()
                if not data.get("quiz_statistics"):
                    # logger.error(f"No quiz statistics found for quiz {quiz_id}")
                    return {'error': 'No quiz statistics found'}

                question_texts, question_ids, selectors = [], [], []
                
                noanswerset = {"multiple_choice_question", "multiple_answers_question", "true_false_question", "short_answer_question", "numerical_question"}
                answerset = {"fill_in_multiple_blanks_question", "multiple_dropdowns_question", "matching_question"}
                writtenset = {"calculated_question", "essay_question"}

                # logger.info(f"Processing {len(data['quiz_statistics'][0]['question_statistics'])} questions for quiz {quiz_id}")

                for question_stat in data["quiz_statistics"][0]["question_statistics"]:
                    try:
                        question_text = BeautifulSoup(question_stat["question_text"], features="html.parser").get_text()
                        question_texts.append(clean_text(question_text))
                        question_ids.append(question_stat["id"])
                        selectors.append([])

                        question_type = question_stat["question_type"]
                        # logger.info(f"Processing question {question_stat['id']} of type {question_type}")

                        if question_type in noanswerset:
                            for answer in question_stat["answers"]:
                                if not answer["correct"]:
                                    selectors[-1].extend(answer.get("user_ids", [-1]))
                        elif question_type in answerset:
                            for answer_set in question_stat["answer_sets"]:
                                for answer in answer_set["answers"]:
                                    if not answer["correct"]:
                                        selectors[-1].extend(answer.get("user_ids", [-1]))
                        elif question_type in writtenset:
                            for answer in question_stat["answers"]:
                                if answer["id"] != "ungraded" and not answer["full_credit"]:
                                    selectors[-1].extend(answer.get("user_ids", [-1]))
                    except Exception as e:
                        # logger.error(f"Error processing question {question_stat.get('id')}: {e}")
                        continue

                if not question_texts:
                    # logger.warning(f"No questions processed for quiz {quiz_id}")
                    return {'error': 'No questions could be processed'}

                # logger.info(f"Successfully processed {len(question_texts)} questions for quiz {quiz_id}")
                return question_texts, selectors, question_ids

    except Exception as e:
        # logger.error(f"Failed to grab quiz statistics for quiz {quiz_id}: {str(e)}")
        return {'error': f'Failed to grab quiz statistics: {str(e)}'}

async def get_questions_by_course(course_id):
    """Retrieve all questions for a specific course."""
    results = await quizzes_collection.find({"courseid": course_id}).to_list(length=None)
    all_questions = []

    for result in results:
        result["_id"] = str(result["_id"])  # Convert ObjectId to string for JSON serialization
        all_questions.append(result)

    if not all_questions:
        return {"error": "No questions found for the given course ID"}

    return {"course_id": course_id, "questions": all_questions}

async def get_student_grade(course_id, user_id, access_token, canvas_domain):
    """Fetches a student's current and final grade for a course from Canvas."""
    # Sanitize the canvas_domain to remove protocol if present
    canvas_domain = canvas_domain.replace("https://", "").replace("http://", "")
    url = f"https://{canvas_domain}/api/v1/courses/{course_id}/enrollments?user_id={user_id}"
    headers = {'Authorization': f'Bearer {access_token}'}
    logger.info(f"Calling Canvas enrollments API: {url}")
    logger.info(f"Headers: {headers}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                logger.info(f"Canvas API response status: {response.status}")
                resp_text = await response.text()
                if response.status != 200:
                    logger.error(f"Failed to fetch enrollments: {response.status}")
                    logger.error(f"Response body: {resp_text}")
                    return None
                try:
                    enrollments = json.loads(resp_text)
                except Exception as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Raw response: {resp_text}")
                    return None
                logger.info(f"Enrollments response: {enrollments}")
                if not enrollments:
                    logger.warning("No enrollments found for this user in the course.")
                    return None
                grades = enrollments[0].get('grades', {})
                current_score = grades.get('current_score')
                final_score = grades.get('final_score')
                logger.info(f"Extracted grades: current_score={current_score}, final_score={final_score}")
                return {
                    "current_score": current_score,
                    "final_score": final_score
                }
    except Exception as e:
        logger.error(f"Exception in get_student_grade: {e}")
        return None

async def get_student_profile(access_token, canvas_domain):
    """Fetches the Canvas user profile using the /api/v1/users/self endpoint."""
    # Sanitize the canvas_domain to remove protocol if present
    canvas_domain = canvas_domain.replace("https://", "").replace("http://", "")
    url = f"https://{canvas_domain}/api/v1/users/self"
    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                resp_text = await response.text()
                if response.status != 200:
                    logger.error(f"Failed to fetch user profile: {response.status}")
                    logger.error(f"Response body: {resp_text}")
                    return None
                try:
                    profile = json.loads(resp_text)
                except Exception as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Raw response: {resp_text}")
                    return None
                # Return at least id and name, but include all profile data
                return {
                    "id": profile.get("id"),
                    "name": profile.get("name"),
                    "profile": profile
                }
    except Exception as e:
        logger.error(f"Exception in get_student_profile: {e}")
        return None
