# KnowGap Backend (AchieveUp API)

## Overview

This backend powers **AchieveUp**, the web app where instructors build skill matrices for their Canvas courses and map quiz questions to skills, and students track their skill mastery and earn badges.

The project and its database keep the **KnowGap** name from the original KnowGap Chrome extension, which has been retired. The extension's routes and services were removed from this backend.

## Features

1. **Integration with Canvas**
   - Uses course and quiz data from Canvas (both Classic Quizzes and New Quizzes) to calculate student skill mastery.
   - Runs a background sync on startup and every 10 minutes (`Config.SET_TIMER`) that pulls quiz questions and updates student skill mastery for every course taught by an AchieveUp instructor.

2. **Skill Matrices and Skill Assignment (AchieveUp)**
   - Instructors create one or more skill matrices per course, with AI-suggested skills based on the course description.
   - Quiz questions are mapped to skills manually or with AI-assisted analysis, and matrices and assignments can be imported from another course.

3. **Skill Mastery and Badges (AchieveUp)**
   - Student mastery per skill is calculated from Canvas quiz submissions and awarded as tiered badges.
   - Students can share their earned badges through a public share link, or opt out of sharing.

4. **Skill Video Curation (AchieveUp)**
   - Instructors curate YouTube videos per skill, add AI-suggested videos, and can jump to the most relevant moment of a video using its transcript.
   - Students vote on whether a video was helpful.

5. **Instructor Analytics (AchieveUp)**
   - Course dashboard and per-student skill breakdowns, risk levels, and earned badges for each course an instructor teaches.

## Tech Stack
 
The backend is a Python application built on the **Quart** framework (an async-capable counterpart to Flask), served in production via **Hypercorn**. Data is stored in **MongoDB**. Configuration is managed through environment variables loaded via `python-dotenv`. The companion frontend is a **React/TypeScript** single-page application that communicates with the backend over HTTP by calling its REST API.
 
## Local Setup (Without Docker)
 
If you want to run the backend directly on your machine, you may need a Python virtual environment and a `.env` file.
 
Python 3.12 is recommended. Some dependencies in `requirements.txt` (notably `pydantic_core`, which relies on prebuilt wheels) may not have published wheels yet for very new Python releases such as 3.14, which will cause `pip install` to fail while trying to compile from source. If you already have a newer Python version installed, you don't need to remove it. You can just install 3.12 alongside it and point your virtual environment at that version specifically.
 
To set up:
 
```
cd knowgap-backend
py -3.12 -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux
pip install --upgrade pip
pip install -r requirements.txt
```
 
On Windows, if `venv\Scripts\activate` fails in PowerShell with a "running scripts is disabled" error, this is PowerShell's default execution policy, not an issue with the project. Either run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal session before activating, or activate via Command Prompt instead using `venv\Scripts\activate.bat`.
 
Once the environment is set up, copy `demo.env` to `.env` and fill in real values — a full MongoDB connection string (`DB_CONNECTION_STRING`), an encryption key matching the rest of the team's if you're working against shared data, and any other required variables. The backend will refuse to start unless `DB_CONNECTION_STRING`, `HEX_ENCRYPTION_KEY`, `AI_API_KEY`, `AI_API_URL`, and `YOUTUBE_API_KEY` are all set. Running the backend outside Docker means it will need a MongoDB instance it can actually reach — either a local install or a shared Atlas cluster.
 
## Running with Docker
 
Docker is the recommended way to run the full stack (backend, frontend, and MongoDB together) without needing a local database or worrying about Python version conflicts.
 
**Folder structure**
 
The provided `docker-compose.yml` expects `backend` and `frontend` as folders. The docker-compose.yml file should be inside a Docker folder inside the parent directory of both the frontend and backend folder. Check the paths in the compose file against your actual folder layout before running it, and adjust if you get a "file not found" error pointing at the wrong location.
 
**Backend `.env` for Docker**
 
The MongoDB container does not support TLS, so when running via Docker, the ENVIRONMENT environment variable needs tobe set to development.
 
```
DB_CONNECTION_STRING=mongodb://mongo:27017
ENVIRONMENT=development
```
 
`mongo` here is the container's hostname on Docker's internal network, not `localhost` — it only resolves inside the Docker Compose network. TLS should still be enabled on deployed/production environments, where it connects to a real MongoDB instance instead of the local container.
 
**Starting the stack**
 
From the folder containing `docker-compose.yml`:
 
```
docker compose up --build
```
 
Once running, the backend is reachable at `http://localhost:5001` and the frontend at `http://localhost:3000`. This is also what to point tools like Postman at when testing backend endpoints directly — the containers need to stay running for the API to respond.
 
To stop everything:
 
```
docker compose down
```
 
This stops and removes the containers but preserves MongoDB data in the named `mongo_data` volume, so test data persists between sessions.
 
## Troubleshooting
 
**`pip install` fails to build `pydantic_core`:** This is almost always a Python version mismatch rather than a real dependency problem — see the Local Setup section above for using Python 3.12 in a dedicated virtual environment.
 
**PowerShell blocks `venv\Scripts\activate`:** This is PowerShell's execution policy, unrelated to the project. Use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` for the current session, or activate via Command Prompt instead.
 
**`docker compose up` fails with a "file not found" error for `.env` or a build path:** The compose file's relative paths don't match your actual folder layout. Confirm whether `docker-compose.yml` sits alongside `backend`/`frontend` or in its own subfolder, and adjust `./` vs `../` in the compose file accordingly.
 
**Docker error: "Docker Desktop is manually paused":** Resume Docker Desktop from the whale icon in the system tray, or open the Docker Desktop app directly and look for a resume option.
 
**VS Code notification about "terminal environment injection is disabled":** This only affects whether `.env` values are manually injected into VS Code's integrated terminal for convenience — it has no effect on the app itself, which loads its own `.env` file via `python-dotenv` at startup. Safe to dismiss.

## Backend Directory Structure

The backend is organized into modular subdirectories to keep the codebase maintainable and scalable.

### 1. `routes/`
Defines the API endpoints, organized by feature area: `base_routes.py`, `auth_routes.py`, `canvas_routes.py`, `achieveup_routes.py`, and `skill_video_routes.py`. Each route file registers its endpoints with the main app instance in `app.py`. See `routes/README.md` for the full list of endpoints.

### 2. `services/`
Contains the core business logic and database interactions, separated from the routing layer. Key files include `course_service.py`, `badge_service.py`, `analytics_service.py`, `mastery_service.py`, `skill_video_service.py`, `canvas_submissions_service.py`, `skill_tiers.py`, and several `achieveup_*_service.py` files handling AI, auth, and Canvas-specific logic. See `services/README.md` for details.

### 3. `utils/`
Shared helper functions: `encryption_utils.py` (token encryption/decryption), `youtube_utils.py` (YouTube API helpers), `ai_utils.py` (AI-generated video search phrases), `course_utils.py` (Canvas course and quiz fetching), and `text_utils.py` (question text normalization and hashing).

### 4. `tests/`
Automated tests, written with `unittest`. Run them with `python -m unittest discover tests` from the backend folder (the same `.env` variables are required).

### Root files
`app.py` creates the Quart app, registers all routes, creates MongoDB indexes, and starts the background sync. `config.py` holds configuration and collection names, and `mongodb.py` provides the shared MongoDB client used by every service.
