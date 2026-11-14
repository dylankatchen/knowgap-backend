# Services Directory

## Overview

The `services` directory is responsible for handling the core business logic and database interactions of the KnowGap Backend API. Each service file is organized around specific features or resources, separating core logic from routing. This modular approach enables easier maintenance, testing, and scalability.

## Service Files

### 1. `course_service.py`
- **Purpose**: Syncs quiz questions from Canvas into the `Quiz Questions` collection. The background sync calls it for every AchieveUp instructor, and AI skill-video suggestions read sample question text from that collection.
- **Key Functions**:
  - **`update_quiz_questions_per_course(course_id, access_token, link)`**: Pulls every quiz question for a course from Canvas and upserts it into the database.

### 2. `achieveup_auth_service.py`
- **Purpose**: AchieveUp account management: signup, login, JWT creation and verification, profile updates, and password changes.
- **Key Functions**:
  - **`achieveup_signup(...)`** / **`achieveup_login(email, password)`**: Create an account or log in, returning a JWT.
  - **`achieveup_verify_token(token)`**: Verifies a JWT and returns the user. Used by almost every AchieveUp service.
  - **`get_user_canvas_token(user_id)`**: Returns a user's decrypted Canvas API token.

### 3. `achieveup_canvas_service.py`
- **Purpose**: All Canvas API access for AchieveUp, including token validation and fetching courses, quizzes, questions, and students (Classic Quizzes and New Quizzes).
- **Key Functions**:
  - **`validate_canvas_token(...)`**: Validates a Canvas token.
  - **`get_instructor_courses(...)`**, **`get_instructor_course_quizzes(...)`**, **`get_instructor_quiz_questions(...)`**, **`get_course_students(...)`**: Instructor views of Canvas data.
  - **`is_new_quiz(...)`**: Checks whether a quiz is a New Quiz or a Classic Quiz.

### 4. `achieveup_service.py`
- **Purpose**: Core AchieveUp logic: skill matrices, course descriptions, skill assignment, student progress, instructor dashboard, AI analysis, and importing skill matrices between courses.
- **Key Functions**:
  - **`create_skill_matrix(...)`**, **`update_skill_matrix(...)`**, **`get_all_skill_matrices_by_course(...)`**, **`delete_skill_matrix(...)`**: Manage skill matrices.
  - **`assign_skills_to_questions(...)`** / **`get_assigned_skills(...)`**: Map quiz questions to skills. Mappings are saved by the question's content and the instructor, not the course, so a question with the same text and answers in a later course already has its skills. Questions identified by an embedded image, or with no text at all, get new IDs when Canvas copies a course, so they don't carry over.
  - **`suggest_course_skills_ai(...)`** / **`analyze_questions_with_ai(...)`**: AI skill suggestions for a course and for quiz questions.
  - **`import_matrices_from_course(...)`**: Copies skill matrices from one course to another.

### 5. `achieveup_ai_service.py`
- **Purpose**: Uses OpenAI to classify quiz questions into the skills of a skill matrix.
- **Key Functions**:
  - **`analyze_questions(questions_data, course_skills)`**: Analyzes questions in batches and returns suggested skills for each.

### 6. `canvas_submissions_service.py`
- **Purpose**: Fetches student quiz submissions from Canvas and turns them into skill mastery data.
- **Key Functions**:
  - **`sync_course_submissions_direct(canvas_token, course_id)`**: Syncs all quiz submissions for a course and updates student mastery. Used by the background sync and the instructor force-sync.

### 7. `mastery_service.py`
- **Purpose**: Calculates each student's mastery of each skill from their quiz submissions and awards badges.
- **Key Functions**:
  - **`update_student_mastery(submission_data)`**: Updates skill mastery from a processed submission.
  - **`check_and_award_badge(...)`**: Awards a badge when a student reaches a new tier.

### 8. `badge_service.py`
- **Purpose**: Creates badges and manages earned badges and public badge sharing.
- **Key Functions**:
  - **`create_badge_for_student(...)`**: Creates a badge for a student (called by `mastery_service.py`).
  - **`get_student_earned_badges(...)`**: Gets a student's earned badges with course information.
  - **`generate_badge_share_link(...)`**, **`get_public_badges_by_share(share_id)`**, **`set_badge_sharing_opt_out(...)`**, **`get_badge_share_status(...)`**: Public badge share links and the opt-out setting.

### 9. `skill_tiers.py`
- **Purpose**: Single source of truth for the mastery percentage needed for each badge tier.
- **Key Functions**:
  - **`tier_for_score(percentage)`**: Maps a 0-100 mastery percentage to a tier label.
  - **`is_mastered(percentage)`**: Whether a percentage counts as mastered.

### 10. `analytics_service.py`
- **Purpose**: Instructor analytics for AchieveUp.
- **Key Functions**:
  - **`get_course_students_analytics(token, course_id)`**: Per-student skill breakdown, risk level, and earned badges for a course.

### 11. `skill_video_service.py`
- **Purpose**: Manages the curated list of videos for each AchieveUp skill.
- **Key Functions**:
  - **`get_skill_videos(...)`**, **`add_skill_video(...)`**, **`remove_skill_video(...)`**: Manage a skill's video list.
  - **`generate_ai_video_recommendations(...)`** / **`verify_ai_video(...)`**: Add AI-suggested videos and mark them as reviewed.
  - **`find_relevant_moment(token, video_id)`**: Uses the video transcript to find the moment most relevant to the skill.
  - **`vote_skill_video(...)`**: Records whether a student found a video helpful.

## Async Flow and Database Interactions

All service functions utilize asynchronous programming with the `Motor` library for MongoDB interactions, which ensures non-blocking data access and efficient performance when working with the database.

- **MongoDB Collections**: Each service gets the shared database connection from `mongodb.py` (`get_db()`) and interacts with specific collections whose names are defined in `config.py`, such as `Quiz Questions` and the `AchieveUp_*` collections.
- **Data Validation and Error Handling**: Each function performs data validation and error handling to ensure reliable database interactions and minimize the risk of runtime issues.

## How Services are Used in Routes

The service functions are called by route handlers in the `routes` directory. This approach:
1. Keeps routes clean and focused on request-response handling.
2. Allows services to manage complex business logic and database interactions.

Example usage in a route:
```python
# Simplified example from skill_video_routes.py
from services.skill_video_service import get_skill_videos

@skill_video_bp.route('/achieveup/skill-videos/get', methods=['POST'])
async def get_skill_videos_route():
    token = _extract_token()
    data = await request.get_json()
    result = await get_skill_videos(token, data.get('course_id'), data.get('skill_name'), data.get('matrix_id'))
    return _result_response(result)
```

## Adding New Services

To add a new service:

1. **Create a new file** in the `services` directory with a descriptive name (e.g., `new_feature_service.py`).
2. **Define the necessary business logic and database functions** within this file.
3. **Import and call these functions** within the appropriate route file to make them accessible via the API.

## Benefits of Service Layer

- **Separation of Concerns**: By keeping business logic separate from route handlers, the codebase remains modular and easier to manage.
- **Reusability**: Service functions can be reused across different routes or even other services as needed.
- **Testability**: Each service function can be individually tested, making it easier to maintain and scale the application.

