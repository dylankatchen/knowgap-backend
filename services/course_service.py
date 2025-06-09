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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
db = client[Config.DATABASE]
course_contexts_collection = db[Config.CONTEXTS_COLLECTION]
students_collection = db[Config.STUDENTS_COLLECTION]
quizzes_collection = db[Config.QUIZZES_COLLECTION]

async def update_context(course_id, course_context):
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


async def update_student_quiz_data(course_id, access_token, link):
    """Updates the database with quiz information and failed questions per student."""
    # Clean the link to remove protocol
    clean_link = link.replace("https://", "").replace("http://", "")
    
    quizlist, quizname = await get_quizzes(course_id, access_token, clean_link)
    
    url = f"https://{clean_link}/api/v1/courses/{course_id}/enrollments"
    headers = {'Authorization': f'Bearer {access_token}'}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error("Failed to fetch enrollments: %s", error_text)
                    return {'status': 'Error', 'error': f'Failed to fetch enrollments: {error_text}'}

                data = await response.json()
                studentmap = {}

                for i, quiz_id in enumerate(quizlist):
                    results = await update_quiz_reccs(course_id, quiz_id, access_token, clean_link)

                    if isinstance(results, dict) and 'error' in results:
                        return {'status': 'Error', 'error': results['error']}
                    
                    question_texts, selectors, question_ids = results

                    for j, user_ids in enumerate(selectors):
                        for student_id in user_ids:
                            if student_id != -1:
                                question_info = {"question": question_texts[j], "question_id": question_ids[j]}
                                if student_id in studentmap:
                                    quiz_found = False
                                    for quiz in studentmap[student_id]:
                                        if quiz['quiz_name'] == quizname[i]:
                                            existing_questions = {q['question_id'] for q in quiz['questions']}
                                            if question_info['question_id'] not in existing_questions:
                                                quiz['questions'].append(question_info)
                                            quiz_found = True
                                            break
                                    if not quiz_found:
                                        studentmap[student_id].append({
                                            "quiz_name": quizname[i],
                                            "quiz_id": quiz_id,
                                            "questions": [question_info],
                                            "used": False
                                        })
                                else:
                                    studentmap[student_id] = [{
                                        "quiz_name": quizname[i],
                                        "quiz_id": quiz_id,
                                        "questions": [question_info],
                                        "used": False
                                    }]
                
                # Save to database
                for student_id, quizzes in studentmap.items():
                    try:
                        await students_collection.update_one(
                            {'_id': str(student_id)},
                            {"$set": {str(course_id): quizzes}},
                            upsert=True
                        )
                    except Exception as e:
                        logger.error("Error updating database for student %s: %s", student_id, e)
                        return {'status': 'Error', 'error': f'Database update failed: {str(e)}'}
    except Exception as e:
        logger.error("Error in update_student_quiz_data: %s", e)
        return {'status': 'Error', 'error': str(e)}
    
    return {'status': 'Success', 'message': 'Database update completed successfully'}



async def update_quiz_questions_per_course(course_id, access_token, link):
    """Updates the database with quiz questions for a course."""
    try:
        # Clean the link to remove protocol
        clean_link = link.replace("https://", "").replace("http://", "")
        
        # Get quizzes for the course
        quizlist, quizname = await get_quizzes(course_id, access_token, clean_link)
        if not quizlist:
            logger.warning(f"No quizzes found for course {course_id}")
            return 1

        # Get course name
        course_name = await get_course_name(course_id, access_token, clean_link)
        if not course_name:
            logger.error(f"Failed to get course name for course {course_id}")
            return 0

        # Process each quiz
        for quiz_id, quiz_title in zip(quizlist, quizname):
            try:
                # Get questions for this quiz
                questions = await get_quiz_questions(course_id, quiz_id, access_token, clean_link)
                if not questions:
                    logger.warning(f"No questions found for quiz {quiz_id}")
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
                        logger.error(f"Error saving question {question.get('id')} for quiz {quiz_id}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error processing quiz {quiz_id}: {e}")
                continue

        return 1

    except Exception as e:
        logger.error(f"Error in update_quiz_questions_per_course: {e}")
        return 0

async def update_quiz_reccs(course_id, quiz_id, access_token, link):
    """Fetches quiz statistics to identify questions students answered incorrectly."""
    # Clean the link to remove protocol
    clean_link = link.replace("https://", "").replace("http://", "")
    
    url = f"https://{clean_link}/api/v1/courses/{course_id}/quizzes/{quiz_id}/statistics"
    headers = {'Authorization': f'Bearer {access_token}'}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {'error': f'Failed to fetch data from API: {error_text}'}

                data = await response.json()
                question_texts, question_ids, selectors = [], [], []
                
                noanswerset = {"multiple_choice_question", "multiple_answers_question", "true_false_question", "short_answer_question", "numerical_question"}
                answerset = {"fill_in_multiple_blanks_question", "multiple_dropdowns_question", "matching_question"}
                writtenset = {"calculated_question", "essay_question"}

                for question_stat in data["quiz_statistics"][0]["question_statistics"]:
                    question_text = BeautifulSoup(question_stat["question_text"], features="html.parser").get_text()
                    question_texts.append(clean_text(question_text))
                    question_ids.append(question_stat["id"])
                    selectors.append([])

                    question_type = question_stat["question_type"]
                    if question_type in noanswerset:
                        for answer in question_stat["answers"]:
                            if not answer["correct"]:
                                selectors[-1] += answer.get("user_ids", [-1])
                    elif question_type in answerset:
                        for answer_set in question_stat["answer_sets"]:
                            for answer in answer_set["answers"]:
                                if not answer["correct"]:
                                    selectors[-1] += answer.get("user_ids", [-1])
                    if question_type in writtenset:
                        for answer in question_stat["answers"]:
                            if answer["id"] != "ungraded" and not answer["full_credit"]:
                                selectors[-1] += answer.get("user_ids", [-1])

                return question_texts, selectors, question_ids

    except Exception as e:
        logger.error("Failed to grab quiz statistics due to: %s", str(e))
        return {'error': f'Failed to grab quiz statistics due to: {str(e)}'}

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
