# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SET_TIMER = 600
    # Database connection string
    DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING")
    
    # Encryption key
    HEX_ENCRYPTION_KEY = os.getenv("HEX_ENCRYPTION_KEY")
    
    # API keys
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

    # Environment-based database selection
    ENV = os.getenv("ENVIRONMENT", "production")
    DATABASE = "KnowGap_Dev" if ENV == "development" else "KnowGap"

    # Database collection names (no prefix needed - separate databases)
    QUIZZES_COLLECTION = "Quiz Questions"
    
    # AchieveUp collection names
    ACHIEVEUP_USERS_COLLECTION = "AchieveUp_Users"
    ACHIEVEUP_SKILL_MATRICES_COLLECTION = "AchieveUp_Skill_Matrices"
    ACHIEVEUP_SKILL_ASSIGNMENTS_COLLECTION = "AchieveUp_Skill_Assignments"
    ACHIEVEUP_QUESTION_SKILLS_COLLECTION = "AchieveUp_Question_Skills"
    ACHIEVEUP_STUDENT_SKILL_MASTERY_COLLECTION = "AchieveUp_Student_Skill_Mastery"
    ACHIEVEUP_USER_BADGES_COLLECTION = "AchieveUp_User_Badges"
    ACHIEVEUP_BADGE_SHARING_COLLECTION = "AchieveUp_Badge_Sharing"
    ACHIEVEUP_PROGRESS_COLLECTION = "AchieveUp_Progress"
    ACHIEVEUP_COURSE_DESCRIPTIONS_COLLECTION = "AchieveUp_Course_Descriptions"
    ACHIEVEUP_IMPORT_STATUS_COLLECTION = "AchieveUp_Import_Status"
    ACHIEVEUP_SKILL_VIDEOS_COLLECTION = "AchieveUp_Skill_Videos"
    ACHIEVEUP_SKILL_VIDEO_VOTES_COLLECTION = "AchieveUp_Skill_Video_Votes"
    ACHIEVEUP_COURSE_CHANNELS_COLLECTION = "AchieveUp_Course_Channels"
    
    # AchieveUp configuration
    # Signs every login token. Required at startup: a built-in default would be
    # public in this repo, letting anyone forge a token for any account.
    ACHIEVEUP_JWT_SECRET = os.getenv("ACHIEVEUP_JWT_SECRET")
    
    CANVAS_DOMAIN = os.getenv("CANVAS_DOMAIN", "canvas.instructure.com")
    CANVAS_API_URL = f"https://{CANVAS_DOMAIN}/api/v1"
    CANVAS_GRAPHQL_API_URL = f"https://{CANVAS_DOMAIN}/api/graphql"
    CANVAS_NEW_QUIZ_API_URL = f"https://{CANVAS_DOMAIN}/api/quiz/v1"

    # Public address of the AchieveUp frontend, used to build links people copy and share
    # (e.g. badge share links). Set to http://localhost:3000 in .env for local development.
    # Both are also the only sites allowed to call the API from a browser (CORS),
    # where they must match the browser's Origin exactly, so stray spaces and
    # empty values are cleaned up here.
    FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip().rstrip("/") or "https://achieveupapp.com"
    FRONTEND_HOSTING_URL = os.getenv("FRONTEND_HOSTING_URL", "").strip().rstrip("/") or FRONTEND_URL

    # True on Heroku, which sets DYNO on every dyno. Heroku's router passes on
    # the visitor's address and scheme in X-Forwarded-* headers; anywhere else
    # those headers come straight from the client, so they're ignored.
    BEHIND_PROXY = bool(os.getenv("DYNO"))

    # Canvas API Configuration

    #AI configuration
    # UCF AI gateway (Portkey), used for Gemma
    AI_API_KEY = os.getenv("AI_API_KEY")
    AI_API_URL = os.getenv("AI_API_URL")
    # Feature Flags
    ENABLE_SUBMISSION_CACHE = os.getenv("ENABLE_SUBMISSION_CACHE", "false").lower() == "true"  # Default to false to minimize storage

    MAX_COURSE_CHANNELS: int = 3
    MAX_CHANNEL_SEARCHES: int = 3

    @classmethod
    def check_config(cls):
        """Method to ensure all necessary config variables are set."""
        missing = [
            var for var in [
                "DB_CONNECTION_STRING", "HEX_ENCRYPTION_KEY", 
                "YOUTUBE_API_KEY", "AI_API_KEY", "AI_API_URL", "ACHIEVEUP_JWT_SECRET"
            ]
            if not getattr(cls, var)
        ]
        if missing:
            raise EnvironmentError(f"Missing environment variables: {', '.join(missing)}")

# Run configuration check at startup
Config.check_config()
