from quart import request, jsonify
from services.course_service import update_context, update_student_quiz_data, get_incorrect_question_data, get_questions_by_course, update_quiz_reccs, update_quiz_questions_per_course, get_student_grade, get_student_profile, sync_all_quizzes_questions
from services.video_service import update_course_videos
from utils.course_utils import get_quizzes 
from quart_cors import cors

def init_course_routes(app):
    @app.route('/update-course-context', methods=['POST'])
    async def update_course_context_route():
        """Route to update course context and trigger video updates."""
        data = await request.get_json()
        course_id = data.get('course_id')
        course_context = data.get('course_context')

        # Log the request data for debugging
        print(f"Received data for course context update: {data}")

        # Validate required fields
        if not course_id or not course_context:
            return jsonify({'error': 'Missing course_id or course_context'}), 400

        # Attempt to update the course context
        context_result = await update_context(course_id, course_context)
        print(f"Context update result: {context_result}")

        # Handle context update response based on the status
        if context_result['status'] == 'Success':
            # Trigger video updates if context update is successful
            videos_result = await update_course_videos(course_id)
            return jsonify({
                'context_update': context_result,
                'videos_update': videos_result
            }), 200
        elif context_result['status'] == 'No changes made':
            return jsonify({
                'status': 'No changes made',
                'message': context_result['message']
            }), 200
        else:
            return jsonify({
                'status': 'Error',
                'message': 'Unexpected result from update operation',
                'error': context_result
            }), 500

    @app.route('/update-course-db', methods=['POST'])
    async def update_course_db_route():
        """Route to update database with course quiz information and student data."""
        data = await request.get_json()
        course_id = data.get('course_id')
        access_token = data.get('access_token')
        link = data.get('link')
        student_id = data.get('student_id')

        print(f"Received data for course DB update: {data}")

        # Validate required fields
        if not course_id or not access_token or not link:
            print("Missing required fields in request")
            return jsonify({'error': 'Missing course_id, access_token, or link'}), 400

        print(f"Starting database update for course {course_id}")
        # Attempt to update the course database
        if student_id:
            db_result = await update_student_quiz_data(course_id, access_token, link, student_id)
        else:
            db_result = await update_student_quiz_data(course_id, access_token, link)
            # After updating student quiz data, ensure all quizzes/questions are in the DB (instructor mode)
            #await update_quiz_questions_per_course(course_id, access_token, link)
        print(f"Database update result: {db_result}")

        if db_result.get('status') == 'Error':
            print(f"Error updating database: {db_result.get('error')}")
            return jsonify({'status': 'Error', 'message': db_result.get('error')}), 500

        '''
        print(f"Starting quiz questions update for course {course_id}")
        # Update quiz questions
        quiz_result = await update_quiz_questions_per_course(course_id, access_token, link)
        print(f"Quiz update result: {quiz_result}")

        if quiz_result.get('status') == 'Success':
            print(f"Successfully updated course {course_id}")
            return jsonify({'status': 'Success', 'message': 'Course database updated successfully'}), 200
        else:
            print(f"Failed to update quiz questions for course {course_id}")
            return jsonify({'status': 'Error', 'message': quiz_result.get('error', 'Failed to update quiz questions')}), 500
        '''

    @app.route('/get-course-quizzes', methods=['POST'])
    async def get_course_quizzes_route():
        """Route to fetch quizzes for a course."""
        data = await request.get_json()
        course_id = data.get('course_id')
        link = data.get('link')
        access_token = data.get('access_token')

        # Log the request data for debugging
        print(f"Received data for fetching course quizzes: {data}")

        if not course_id or not link or not access_token:
            return jsonify({'error': 'Missing course_id or link'}), 400

        try:
            quiz_list, quiz_names = await get_quizzes(course_id, access_token, link)
            return jsonify({'status': 'Success', 'quizzes': quiz_names}), 200
        except Exception as e:
            print(f"Error fetching quizzes: {e}")
            return jsonify({'status': 'Error', 'message': str(e)}), 500

    @app.route('/get-incorrect-questions', methods=['POST'])
    async def get_incorrect_questions_route():
        """Route to fetch incorrect question data for a specific quiz."""
        data = await request.get_json()
        course_id = data.get('course_id')
        quiz_id = data.get('quiz_id')
        link = data.get('link')

        print(f"Received data for fetching incorrect questions: {data}")

        if not course_id or not quiz_id or not link:
            return jsonify({'error': 'Missing course_id, quiz_id, or link'}), 400

        try:
            question_data = await get_incorrect_question_data(course_id, quiz_id, link)
            return jsonify({'status': 'Success', 'data': question_data}), 200
        except Exception as e:
            print(f"Error fetching incorrect questions: {e}")
            return jsonify({'status': 'Error', 'message': str(e)}), 500


    @app.route('/get-questions-by-course/<course_id>', methods=['POST'])
    async def get_questions_by_course_route(course_id):
        """Route to fetch questions for a specific course."""
        try:
            question_data = await get_questions_by_course(course_id)
            
            if "error" in question_data:
                return jsonify(question_data), 404

            return jsonify({"status": "Success", "data": question_data}), 200
        except Exception as e:
            print(f"Error fetching questions for course {course_id}: {e}")
            return jsonify({"status": "Error", "message": str(e)}), 500

    @app.route('/get-student-grade', methods=['POST'])
    async def get_student_grade_route():
        """Route to fetch a student's grade for a course."""
        data = await request.get_json()
        course_id = data.get('course_id')
        user_id = data.get('user_id')
        access_token = data.get('access_token')
        canvas_domain = data.get('canvas_domain')

        if not course_id or not user_id or not access_token or not canvas_domain:
            return jsonify({'error': 'Missing course_id, user_id, access_token, or canvas_domain'}), 400

        grade = await get_student_grade(course_id, user_id, access_token, canvas_domain)
        if grade is None:
            return jsonify({'status': 'Error', 'message': 'Could not fetch grade'}), 500
        return jsonify({'status': 'Success', 'grade': grade}), 200

    @app.route('/get-student-profile', methods=['POST'])
    async def get_student_profile_route():
        """Route to fetch the Canvas user profile for the current user."""
        data = await request.get_json()
        access_token = data.get('access_token')
        canvas_domain = data.get('canvas_domain')

        if not access_token or not canvas_domain:
            return jsonify({'error': 'Missing access_token or canvas_domain'}), 400

        profile = await get_student_profile(access_token, canvas_domain)
        if profile is None:
            return jsonify({'status': 'Error', 'message': 'Could not fetch user profile'}), 500
        return jsonify({'status': 'Success', 'profile': profile}), 200

    @app.route('/sync-all-quizzes-questions', methods=['POST'])
    async def sync_all_quizzes_questions_route():
        """Route to perform a deep sync of all quizzes and questions for a course (instructor-only, heavy operation).
        Accepts course_id, access_token, and link in the JSON body."""
        data = await request.get_json()
        course_id = data.get('course_id')
        access_token = data.get('access_token')
        link = data.get('link')
        if not course_id or not access_token or not link:
            return jsonify({'error': 'Missing course_id, access_token, or link'}), 400
        result = await sync_all_quizzes_questions(course_id, access_token, link)
        return jsonify(result), 200
