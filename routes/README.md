# Routes Directory

## Overview

The `routes` directory contains all route definitions for the KnowGap Backend API. Each route file is organized by functionality to handle different aspects of the application, such as authentication, Canvas data, skill matrices, badges, and videos. Routes are registered with the main application instance in `app.py` in one of two ways:

- **`base_routes.py`** uses an initialization function (`init_base_routes`) that registers its routes directly on the app.
- **AchieveUp routes** are defined on a Quart `Blueprint` (e.g. `auth_bp`) that is registered with `app.register_blueprint(...)`.

Unless noted otherwise, AchieveUp endpoints require an `Authorization: Bearer <JWT>` header obtained from `/auth/login` or `/auth/signup`.

## Route Files

### 1. `base_routes.py`
- **Purpose**: Contains foundational routes, including the root (`/`) endpoint for a welcome or health check message, and the CORS preflight (`OPTIONS`) handler.
- **Main Endpoint**:
  - `GET /` - Returns a welcome message to indicate that the API is active.

### 2. `auth_routes.py` (`auth_bp`)
- **Purpose**: Handles AchieveUp account authentication and profile management.
- **Key Endpoints**:
  - `POST /auth/signup` - Registers a user with email, password, and Canvas API token. Returns a JWT and user object.
  - `POST /auth/login` - Logs in with email and password. Returns a JWT and user object.
  - `GET /auth/me` - Returns the current user's information.
  - `PUT /auth/profile` - Updates the user's profile, including their Canvas API token.
  - `PUT /auth/password` - Changes the user's password.
  - `POST /auth/validate-canvas-token` - Validates a Canvas API token with Canvas before it is stored.

### 3. `canvas_routes.py` (`canvas_bp`)
- **Purpose**: Retrieves Canvas courses, quizzes, and questions using the user's stored Canvas API token.
- **Key Endpoints**:
  - `GET /canvas/courses` - Gets the user's Canvas courses.
  - `GET /canvas/courses/<course_id>/quizzes` - Gets quizzes for a course.
  - `GET /canvas/quizzes/<quiz_id>/questions` - Gets questions for a quiz.
  - `GET /canvas/test-connection` - Tests whether the stored Canvas API token is still valid.
  - `GET /canvas/instructor/courses` - Gets all courses taught by the instructor.
  - `GET /canvas/instructor/courses/<course_id>/quizzes` - Gets all quizzes in a course (instructor view).
  - `GET /canvas/instructor/courses/<course_id>/quizzes/<quiz_id>/questions` - Gets all questions in a quiz (instructor view).

### 4. `achieveup_routes.py` (`achieveup_bp`)
- **Purpose**: Core AchieveUp functionality: skill matrices, skill assignment, AI suggestions, progress, badges, and instructor analytics.
- **Key Endpoints**:
  - Skill matrices:
    - `POST /achieveup/matrix/create` - Creates a skill matrix for a course.
    - `PUT /achieveup/matrix/<matrix_id>` - Updates a skill matrix.
    - `GET /achieveup/matrix/course/<course_id>` - Gets all skill matrices for a course.
    - `DELETE /achieveup/matrix/delete/<matrix_id>` - Deletes a skill matrix.
    - `POST /achieveup/matrix/import` - Imports all skill matrices from a source course into a target course.
  - Course descriptions:
    - `GET /achieveup/course-description/<course_id>` - Gets the instructor's saved course description.
    - `PUT /achieveup/course-description/<course_id>` - Saves the instructor's course description (used as AI context).
  - Skill assignment:
    - `POST /achieveup/skills/assign` - Assigns skills to quiz questions.
    - `GET /achieveup/skills/assignments` - Gets the skills assigned to questions in a course.
    - `POST /achieveup/skills/import` - Imports skill assignments from a source course into a target course.
    - `GET /achieveup/import-status/<course_id>` - Gets whether matrices and assignments have been imported into a course.
  - AI:
    - `POST /achieveup/ai/suggest-skills` - Suggests skills for a course.
    - `POST /achieveup/ai/analyze-questions` - Analyzes quiz questions and suggests skills for each.
  - Progress:
    - `GET /achieveup/progress/<student_id>/<course_id>` - Gets a student's skill progress in a course.
  - Badges:
    - `GET /achieveup/badges/student/<student_id>/earned` - Gets a student's earned badges with course information: all of them for the student themself, or one course's (`?course_id=`, required) for an instructor of that course.
    - `POST /achieveup/badges/share-profile` - Gets or creates a badge share link, for the caller or for a student an instructor teaches.
    - `GET /achieveup/badges/share-status` - Gets the caller's current share link and opt-out preference.
    - `POST /achieveup/badges/opt-out` - Turns off badge sharing for the caller.
    - `POST /achieveup/badges/opt-in` - Turns badge sharing back on for the caller.
    - `GET /achieveup/public/badges/share/<share_id>/earned` - Gets the badges on a public share link (no login required).
  - Instructor:
    - `GET /achieveup/instructor/dashboard` - Gets instructor dashboard data.
    - `GET /achieveup/instructor/courses/<course_id>/student-analytics` - Gets per-student skill analytics for a course.
    - `POST /achieveup/instructor/course/<course_id>/force-sync` - Forces a Canvas data and mastery sync for a course.

### 5. `skill_video_routes.py` (`skill_video_bp`)
- **Purpose**: Manages the curated list of videos for each skill in AchieveUp.
- **Key Endpoints**:
  - `POST /achieveup/skill-videos/get` - Gets the curated video list for a skill.
  - `POST /achieveup/skill-videos` - Instructor adds a YouTube video to a skill.
  - `DELETE /achieveup/skill-videos/<video_id>` - Instructor removes a video.
  - `POST /achieveup/skill-videos/suggest` - Instructor requests AI-suggested videos for a skill.
  - `POST /achieveup/skill-videos/<video_id>/find-moment` - Instructor finds the transcript moment most relevant to a video.
  - `POST /achieveup/skill-videos/<video_id>/verify` - Instructor marks an AI-suggested video as reviewed.
  - `POST /achieveup/skill-videos/vote` - Student rates whether a video was helpful.

## Route Initialization

`base_routes.py` contains an initialization function that registers its routes with the main `app` instance in `app.py`, and each AchieveUp route file exposes a Blueprint that `app.py` registers. This approach keeps route definitions modular, making it easy to maintain and expand the API.

### Example Initialization in `app.py`

```python
from quart import Quart
from routes.base_routes import init_base_routes
from routes.auth_routes import auth_bp
from routes.achieveup_routes import achieveup_bp

app = Quart(__name__)

# Registering base routes
init_base_routes(app)

# Registering AchieveUp blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(achieveup_bp)
```
## Route Conventions

### Error Handling
Each route validates request data and returns a JSON error response if required fields are missing.

### Response Structure
AchieveUp routes return errors as JSON with `error`, `message`, and `statusCode` fields, using the same HTTP status code as `statusCode`.

## Extending Routes

To add new routes, create a new file in the `routes` directory and follow these steps:

1. **Define the required endpoints and their corresponding handler functions.**
2. **Either create an initialization function (`init_<your_route_name>_routes`) to register the routes, or define them on a `Blueprint`.**
3. **Import and call this initialization function (or `app.register_blueprint(...)`) in `app.py` to activate the new routes.**
