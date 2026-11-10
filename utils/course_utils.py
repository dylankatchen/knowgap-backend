import aiohttp
import certifi
import ssl
from config import Config

def get_ssl_context():
    """SSL setting for Canvas requests: always verified, never disabled."""
    if Config.ENV == 'development':
        # Use certifi's certificate bundle, which works even where Python
        # can't find the computer's own certificates.
        return ssl.create_default_context(cafile=certifi.where())
    # Production: aiohttp's default verification against the system certificates
    return True

def create_canvas_session():
    """Create aiohttp ClientSession with appropriate SSL settings."""
    ssl_setting = get_ssl_context()
    if ssl_setting is True:
        # Production: use default SSL verification
        return aiohttp.ClientSession()
    else:
        # Development: use custom SSL context
        return aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_setting))

async def get_course_name(courseid, access_token, link):
    api_url = f'https://{link}/api/v1/courses/{courseid}'
    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        async with create_canvas_session() as session:
            async with session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    course_details = await response.json()
                    course_name = course_details.get("name", "Course name not found")
                    return course_name
                else:
                    print(f"Failed to retrieve course. Status code: {response.status}")
    except Exception as e:
        return {'error': str(e)}, 500
def clean_text(text):
    """Normalizes text and filters to keep only ASCII characters."""
    return ''.join(char for char in text if ord(char) < 128)
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
    async with create_canvas_session() as session:
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
    
    async with create_canvas_session() as session:
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


def course_id_filter(course_id) -> dict:
    """Mongo filter matching a course_id stored either as text or as a number."""
    values = [str(course_id)]
    # ASCII digits only: isdigit accepts "²" (which int() rejects), and isdecimal accepts
    # full-width digits like "１２" (which int() turns into 12).
    if str(course_id).isascii() and str(course_id).isdecimal():
        values.append(int(course_id))
    return {'course_id': {'$in': values}}
