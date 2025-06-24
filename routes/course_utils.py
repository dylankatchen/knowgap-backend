import asyncio
import aiohttp
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from config import Config
async def get_course_name(courseid, access_token, link):
    api_url = f'https://{link}/api/v1/courses/{courseid}'
    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    course_details = await response.json()
                    course_name = course_details.get("name", "Course name not found")
                    return course_name
                else:
                    print(f"Failed to retrieve course. Status code: {response.status}")
    except Exception as e:
        return {'error': str(e)}, 500
def parse_date(date_str):
    """Parses a date string to UTC datetime."""
    if date_str:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
        return dt.astimezone(timezone.utc)  # Normalize to UTC
    return None
def clean_text(text):
    """Normalizes text and filters to keep only ASCII characters."""
    return ''.join(char for char in text if ord(char) < 128)
def get_incorrect_user_ids(question, no_answer_set, answer_set):
    """Extracts user IDs for incorrect answers based on question type."""
    incorrect_user_ids = []
    if question["question_type"] in no_answer_set:
        incorrect_user_ids = extract_no_answer_user_ids(question["answers"])
    elif question["question_type"] in answer_set:
        incorrect_user_ids = extract_answer_set_user_ids(question["answer_sets"])
    return incorrect_user_ids if incorrect_user_ids else [-1]
def extract_no_answer_user_ids(answers):
    """Helper to gather user IDs from questions without answer sets."""
    return [user_id for answer in answers if not answer["correct"]
            for user_id in (answer.get("user_ids") or [-1])]
def extract_answer_set_user_ids(answer_sets):
    """Helper to gather user IDs from questions with answer sets."""
    user_ids = []
    for answer_set in answer_sets:
        user_ids.extend(user_id for answer in answer_set["answers"] if not answer["correct"]
                        for user_id in (answer.get("user_ids") or [-1]))
    return user_ids
async def get_quizzes(course_id, access_token, link):
    """Fetch all quizzes for a course, handling pagination."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    clean_link = link.replace("https://", "").replace("http://", "")
    url = f"https://{clean_link}/api/v1/courses/{course_id}/quizzes"
    quiz_list = []
    quiz_names = {}
    async with aiohttp.ClientSession() as session:
        while url:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    quizzes = await response.json()
                    for quiz in quizzes:
                        quiz_id = str(quiz['id'])
                        quiz_list.append(quiz_id)
                        quiz_names[quiz_id] = quiz['title']
                    # Handle pagination
                    link_header = response.headers.get('Link')
                    if link_header and 'rel="next"' in link_header:
                        import re
                        match = re.search(r'<([^>]+)>; rel="next"', link_header)
                        url = match.group(1) if match else None
                    else:
                        url = None
                else:
                    raise Exception(f"Failed to fetch quizzes: {response.status}")
    return quiz_list, quiz_names

async def get_quiz_questions(course_id, quiz_id, access_token, link):
    """Fetch questions for a specific quiz."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Clean the link to remove protocol
    clean_link = link.replace("https://", "").replace("http://", "")
    
    url = f"https://{clean_link}/api/v1/courses/{course_id}/quizzes/{quiz_id}/questions"
    
    #print(f"Attempting to fetch questions from: {url}")
    #print(f"Using headers: {headers}")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            #print(f"Response status: {response.status}")
            #print(f"Response headers: {dict(response.headers)}")
            
            if response.status == 200:
                questions = await response.json()
                #print(f"Successfully fetched {len(questions)} questions for quiz {quiz_id}")
                return questions
            elif response.status == 403:
                error_text = await response.text()
                #print(f"403 Forbidden error for quiz {quiz_id}. Response: {error_text}")
                #print(f"This likely means the access token doesn't have permission to view quiz questions")
                #print(f"or the quiz is unpublished/restricted")
                raise Exception(f"403 Forbidden - No permission to access quiz questions. Response: {error_text}")
            else:
                error_text = await response.text()
                #print(f"Failed to fetch questions for quiz {quiz_id}. Status: {response.status}, Response: {error_text}")
                raise Exception(f"Failed to fetch questions: {response.status} - {error_text}")

async def get_incorrect_question_data(course_id, quiz_id, link):
    """Fetch incorrect question data for a specific quiz."""
    try:
        # Get the quiz document from the database
        quiz_doc = await quizzes_collection.find_one({
            "course_id": course_id,
            "quiz_id": quiz_id
        })
        
        if not quiz_doc:
            raise Exception(f"No quiz found for course_id: {course_id} and quiz_id: {quiz_id}")
        
        # Extract the questions data
        questions = quiz_doc.get('questions', [])
        
        # Filter for questions with incorrect answers
        incorrect_questions = []
        for question in questions:
            if question.get('incorrect_answers'):
                incorrect_questions.append({
                    'question_id': question.get('question_id'),
                    'question_text': question.get('question_text'),
                    'incorrect_answers': question.get('incorrect_answers'),
                    'correct_answer': question.get('correct_answer')
                })
        
        return incorrect_questions
    except Exception as e:
        print(f"Error in get_incorrect_question_data: {e}")
        raise e
