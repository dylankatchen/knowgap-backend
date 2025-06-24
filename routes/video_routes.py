# routes/video_routes.py

from quart import request, jsonify
from services.video_service import (
    get_assessment_videos, get_course_videos, update_course_videos,
    update_video_link, add_video, remove_video, update_videos_for_filter
)

def init_video_routes(app):
    @app.route('/get-assessment-videos', methods=['POST', 'OPTIONS'])
    async def get_assessment_videos_route():
        if request.method == 'OPTIONS':
            return '', 204

        # print("Received request for get-assessment-videos")
        data = await request.get_json()
        # print(f"Request data: {data}")

        if not all(k in data for k in ("student_id", "course_id")):
            # print("Missing student_id or course_id")
            return jsonify({"error": "Missing student_id or course_id"}), 400

        # Check if we have the required data for student creation
        if not all(k in data for k in ("access_token", "link")):
            # print("Missing access_token or link for student creation")
            return jsonify({"error": "Missing access_token or link for student creation"}), 400

        # First ensure the student exists in the database
        from services.course_service import update_student_quiz_data
        # print(f"Updating student data for student {data['student_id']} in course {data['course_id']}")
        db_result = await update_student_quiz_data(data['course_id'], data['access_token'], data['link'], data['student_id'])
        # print(f"Database update result: {db_result}")

        if db_result.get('status') == 'Error':
            # print(f"Error updating student data: {db_result.get('error')}")
            return jsonify({"error": f"Failed to update student data: {db_result.get('error')}"}), 500

        # Now get the assessment videos
        # print("Getting assessment videos")
        assessment_videos = await get_assessment_videos(data['student_id'], data['course_id'])
        # print(f"Assessment videos result: {assessment_videos}")
        
        if assessment_videos:
            return jsonify({"assessment_videos": assessment_videos}), 200
        else:
            return jsonify({"message": "No assessment videos found"}), 404

    @app.route('/get-course-videos', methods=['POST', 'OPTIONS'])
    async def get_course_videos_route():
        if request.method == 'OPTIONS':
            return '', 204
            
        try:
            # print("Received request for get-course-videos")
            data = await request.get_json()
            # print(f"Request data: {data}")
            
            if not data:
                # print("No JSON data received")
                return jsonify({"error": "No JSON data received"}), 400
                
            course_id = data.get("course_id")
            # print(f"Course ID: {course_id}")
            
            if not course_id:
                # print("Missing course_id")
                return jsonify({"error": "Missing course_id"}), 400
            
            # print("Calling get_course_videos service")
            course_videos = await get_course_videos(course_id)
            # print(f"Service response: {course_videos}")
            
            if course_videos:
                return jsonify({"course_videos": course_videos}), 200
            else:
                return jsonify({"message": "No videos found for this course"}), 404
        except Exception as e:
            # print(f"Error in get_course_videos_route: {str(e)}")
            # import traceback
            # print(f"Full traceback: {traceback.format_exc()}")
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    @app.route('/update-course-videos', methods=['POST'])
    async def update_course_videos_route():
        data = await request.get_json()
        course_id = data.get('course_id')
        
        if not course_id:
            return jsonify({'error': 'Missing Course ID'}), 400
        
        result = await update_course_videos(course_id)
        return jsonify(result), 200

    @app.route('/update-video-link', methods=['POST'])
    async def update_video_link_route():
        data = await request.get_json()
        if not all(k in data for k in ("quiz_id", "question_id", "new_link")):
            return jsonify({"error": "Missing required parameters"}), 400

        result = await update_video_link(data['quiz_id'], data['question_id'], data['new_link'])
        if result["success"]:
            return jsonify({"message": result["message"]}), 200
        else:
            return jsonify({"error": result["message"]}), 404

    @app.route('/add-video', methods=['POST'])
    async def add_video_route():
        data = await request.get_json()
        if not all(k in data for k in ("quiz_id", "question_id", "video_link")):
            return jsonify({"error": "Missing required parameters"}), 400

        result = await add_video(data['quiz_id'], data['question_id'], data['video_link'])
        if result["success"]:
            return jsonify({"message": result["message"]}), 200
        else:
            return jsonify({"error": result["message"]}), 409

    @app.route('/remove-video', methods=['POST'])
    async def remove_video_route():
        data = await request.get_json()
        if not all(k in data for k in ("quiz_id", "question_id")):
            return jsonify({"error": "Missing required parameters"}), 400

        result = await remove_video(data['quiz_id'], data['question_id'])
        if result["success"]:
            return jsonify({"message": result["message"]}), 200
        else:
            return jsonify({"error": result["message"]}), 404
        
    @app.route('/update-all-videos', methods=['POST'])
    async def update_all_videos_route():
        data = await request.get_json()
        result = await update_videos_for_filter()
        if result.get("message") == "success":
            return jsonify({"message": result["message"]}), 200
        else:
            return jsonify({"error": result["message"]}), 404

    @app.route('/set-video-watched', methods=['POST'])
    async def set_video_watched_route():
        data = await request.get_json()
        student_id = data.get('student_id')
        course_id = data.get('course_id')
        video_link = data.get('video_link')
        watched = data.get('watched')
        if not all([student_id, course_id, video_link, watched is not None]):
            return jsonify({'error': 'Missing required parameters'}), 400
        from services.video_service import set_video_watched
        result = await set_video_watched(student_id, course_id, video_link, watched)
        if result.get('success'):
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': result.get('error', 'Unknown error')}), 400
