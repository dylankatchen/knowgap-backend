# services/video_service.py

import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from utils.youtube_utils import fetch_video_for_topic, extract_video_id, get_video_metadata
from utils.ai_utils import generate_core_topic
from utils.db_utils import find_documents_by_field
from config import Config

# MongoDB async connection
mongo_client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)

db = mongo_client[Config.DATABASE]
students_collection = db[Config.STUDENTS_COLLECTION]
quizzes_collection = db[Config.QUIZZES_COLLECTION]
contexts_collection = db[Config.CONTEXTS_COLLECTION]  # For course context data

async def get_assessment_videos(student_id, course_id):
    """Retrieve incorrect questions and associated video links for assessments."""
    student_record = await students_collection.find_one({"_id": student_id})
    if not student_record:
        return {"error": "Student not found"}

    quizzes = student_record.get(course_id, [])
    used_video_links = set()
    video_data_new = {}

    res = []

    for quiz in quizzes:
        quiz_name = quiz.get('quiz_name', 'Unknown Quiz')
        quiz_id = quiz.get('quiz_id')
        incorrect_questions = quiz.get('questions', [])

        for question in incorrect_questions:
            question_data = await quizzes_collection.find_one({"quiz_id": quiz_id, "question_id": question.get("question_id")})
            if question_data:
                core_topic = question_data.get("core_topic", "No topic found")
                video_data = question_data.get('video_data')  # Expecting a single video dictionary, not a list
            
                matching_core_topic_data = find_documents_by_field("Quiz Questions", "core_topic", core_topic)
                for doc in matching_core_topic_data:
                    matching_video_data = doc.get("video_data")
                    if matching_video_data:
                        video_data = matching_video_data
                        break

                if isinstance(video_data, list) and len(video_data) > 0:
                    video_data = video_data[0]  # Extract the first video dictionary from the list

                if video_data and video_data['link'] not in used_video_links:
                    used_video_links.add(video_data['link'])
                    res.append({
                        "quiz_name": quiz_name,
                        "question_id": question_data.get("question_id"),
                        "question_text": question_data.get("question_text"),
                        "topic": core_topic,
                        "video": video_data  # Store a single video dictionary
                    })

    return res

async def get_course_videos(course_id):
    """Fetch all video data associated with a specific course ID."""
    try:
        print(f"Starting get_course_videos for course_id: {course_id}")
        # Add index hint and limit the fields we're retrieving
        projection = {
            'video_data': 1,
            'core_topic': 1,
            'question_text': 1,
            'quiz_id': 1,
            'question_id': 1,
            '_id': 0  # Exclude _id field
        }
        
        # Use find().to_list() instead of async for to get all results at once
        quizzes = await quizzes_collection.find(
            {"course_id": course_id},
            projection=projection
        ).to_list(length=None)
        
        print(f"Found {len(quizzes)} quizzes for course {course_id}")
        
        course_videos = []
        for quiz in quizzes:
            video_data = quiz.get('video_data')
            if video_data:  # Only add if there's video data
                course_videos.append({
                    'quiz_id': quiz.get('quiz_id'),
                    'question_id': quiz.get('question_id'),
                    'core_topic': quiz.get('core_topic'),
                    'question_text': quiz.get('question_text'),
                    'video_data': video_data
                })
        
        print(f"Returning {len(course_videos)} videos")
        return course_videos
    except Exception as e:
        print(f"Error in get_course_videos: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return []

async def update_videos_for_filter(filter_criteria=None):
    """Update videos for all questions that match the filter criteria. Updates all videos in DB if no criteria provided."""
    query = filter_criteria if filter_criteria else {}
    async for question in quizzes_collection.find(query):
        question_text = question.get('question_text')
        if not question_text or question.get('video_data'):
            continue

        course_id = question.get('course_id')
        course_name = question.get('course_name', "")

        # Fetch context data and core topic
        course_context_data = await contexts_collection.find_one({'course_id': course_id})
        course_context = course_context_data.get('course_context', "") if course_context_data else ""
        
        core_topic_obj = await generate_core_topic(question_text, course_name, course_context)
        core_topic = core_topic_obj["core_topic"]
        # Fetch or update video data for the topic
        video_data = await fetch_video_for_topic(core_topic)

        await quizzes_collection.update_one(
            {'question_id': question.get("question_id")},
            {'$set': {'core_topic': core_topic, 'video_data': video_data}},
            upsert=True
        )

    return {"message": "success"}

async def update_course_videos(course_id):
    """Updates videos for all questions within a specific course ID."""
    filter_criteria = {'course_id': course_id}
    return await update_videos_for_filter(filter_criteria)

async def update_video_link(quiz_id, question_id, new_video_url):
    """Updates a specific video link within the video's data for a question."""
    # Fetch document
    document = await quizzes_collection.find_one({"quiz_id": quiz_id, "question_id": question_id})
    
    if not document:
        return {"message": "Document not found", "success": False}

    # Create updated video metadata using new link
    new_video_metadata = await get_video_metadata(new_video_url)
    if "error" in new_video_metadata:
        return {"message": "Failed to fetch new metadata for the new video", "success": False}

    # Update database
    update_result = await quizzes_collection.update_one(
        {"quiz_id": quiz_id, "question_id": question_id},
        {"$set": {"video_data": new_video_metadata}}
    )

    return {
        "message": "Video successfully updated" if update_result.modified_count > 0 else "Failed to update video_data",
        "success": update_result.modified_count > 0
    }

async def add_video(quiz_id, question_id, video_link):
    """Adds a new video link and metadata to a question, avoiding duplicates."""
    document = await quizzes_collection.find_one({"quiz_id": quiz_id, "question_id": question_id})
    
    if not document:
        return {"message": "Document not found", "success": False}

    video_data = document.get('video_data', {})

    if video_data["link"] == video_link:
         return {"message": "Link already exists for this question.", "success": True}
    
    # Add new video metadata
    new_video_metadata = await get_video_metadata(video_link)
    if "error" in new_video_metadata:
        return {"message": "Failed to fetch metadata for the video", "success": False}

    # Update document
    await quizzes_collection.update_one(
        {"quiz_id": quiz_id, "question_id": question_id},
        {"$set": {"video_data": new_video_metadata}}
    )
    
    return {"message": "Video added successfully", "success": True}

async def remove_video(quiz_id, question_id):
    """Removes a specific video by link from a question's video data."""
    document = await quizzes_collection.find_one({"quiz_id": quiz_id, "question_id": question_id})
    
    if not document:
        return {"message": "Document not found", "success": False}

    await quizzes_collection.update_one(
        {"quiz_id": quiz_id, "question_id": question_id},
        {"$set": {"video_data": {}}}
    )
    
    return {"message": "Video successfully removed", "success": True}
