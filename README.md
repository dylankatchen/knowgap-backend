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
   - Quiz questions are mapped to skills manually or with AI-assisted analysis, and matrices can be imported from another course. Skill mappings carry over to a later course on their own when a question's text and answers are unchanged.

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
 
Once the environment is set up, copy `demo.env` to `.env` and fill in real values — a full MongoDB connection string (`DB_CONNECTION_STRING`), an encryption key matching the rest of the team's if you're working against shared data, and any other required variables. The backend will refuse to start unless `DB_CONNECTION_STRING`, `HEX_ENCRYPTION_KEY`, `OPENAI_KEY`, `YOUTUBE_API_KEY`, and `ACHIEVEUP_JWT_SECRET` are all set. `ACHIEVEUP_JWT_SECRET` signs login tokens; locally any long random string works (for example, the output of `python -c "import secrets; print(secrets.token_hex(32))"`), but never reuse the production value. Running the backend outside Docker means it will need a MongoDB instance it can actually reach — either a local install or a shared Atlas cluster.
 
## Running with Docker
 
Docker is the recommended way to run the full stack (backend, frontend, and MongoDB together) without needing a local database or worrying about Python version conflicts.
 
**Folder structure**
 
`docker-compose.yml` lives in this repo. It expects the frontend repo to be cloned next to this one, in a folder named `frontend` (for example `seniordesign/backend` and `seniordesign/frontend`). If your frontend folder has a different name, such as the default `achieveup-frontend` from `git clone`, add `FRONTEND_DIR=../achieveup-frontend` to this folder's `.env`. If you used an older copy of the compose file kept outside the repos, switch to this one and delete the old copy: this one only opens its ports to your own computer (see below). Local MongoDB data from the old copy stays in its own Docker volume and won't show up in the new stack, so you start with an empty local database.
 
**Backend `.env` for Docker**
 
The MongoDB container does not support TLS, so when running via Docker, the ENVIRONMENT environment variable needs tobe set to development.
 
```
DB_CONNECTION_STRING=mongodb://mongo:27017
ENVIRONMENT=development
```
 
`mongo` here is the container's hostname on Docker's internal network, not `localhost` — it only resolves inside the Docker Compose network. TLS should still be enabled on deployed/production environments, where it connects to a real MongoDB instance instead of the local container.
 
**Starting the stack**
 
From this backend folder:
 
```
docker compose up --build
```
 
Once running, the backend is reachable at `http://localhost:5001` and the frontend at `http://localhost:3000`. This is also what to point tools like Postman at when testing backend endpoints directly — the containers need to stay running for the API to respond. The backend also runs a debugger on port 5678 that VS Code can attach to, and MongoDB is on port 27017 (for tools like Compass). All four ports only accept connections from your own computer, not from other devices on your network, because the debugger has no password and can run any code in the backend. Keep the `127.0.0.1:` prefix on the ports in `docker-compose.yml`.
 
To stop everything:
 
```
docker compose down
```
 
This stops and removes the containers but preserves MongoDB data in the named `mongo_data` volume, so test data persists between sessions.
 
## Troubleshooting
 
**`pip install` fails to build `pydantic_core`:** This is almost always a Python version mismatch rather than a real dependency problem — see the Local Setup section above for using Python 3.12 in a dedicated virtual environment.
 
**PowerShell blocks `venv\Scripts\activate`:** This is PowerShell's execution policy, unrelated to the project. Use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` for the current session, or activate via Command Prompt instead.
 
**`docker compose up` fails with a "file not found" error for `.env` or a build path:** Run it from this backend folder, make sure `.env` exists here, and check that the frontend repo is cloned next to this one in a folder named `frontend` (or that `FRONTEND_DIR` in `.env` points at it).

**The frontend doesn't pick up a newly added npm package:** The frontend container keeps its `node_modules` in a Docker volume that survives rebuilds. After frontend dependencies change, run `docker compose up --build -V` once to recreate it.
 
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
