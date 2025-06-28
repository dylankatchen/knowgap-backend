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
    OPENAI_KEY = os.getenv("OPENAI_KEY")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    # URLs
    YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"

    # Database collection names
    DATABASE = "KnowGap"
    TOKENS_COLLECTION = "Tokens"
    QUIZZES_COLLECTION = "Quiz Questions"
    STUDENTS_COLLECTION = "Students"
    COURSES_COLLECTION = "Courses"
    CONTEXTS_COLLECTION = "Course Contexts"
    
    # AchieveUp collection names
    ACHIEVEUP_DATA_COLLECTION = "AchieveUp_Data"
    SKILL_MATRICES_COLLECTION = "Skill_Matrices"
    BADGES_COLLECTION = "Badges"
    SKILL_PROGRESS_COLLECTION = "Skill_Progress"
    ACHIEVEUP_USERS_COLLECTION = "AchieveUp_Users"
    ACHIEVEUP_SKILL_MATRICES_COLLECTION = "AchieveUp_Skill_Matrices"
    ACHIEVEUP_QUESTION_SKILLS_COLLECTION = "AchieveUp_Question_Skills"
    ACHIEVEUP_BADGES_COLLECTION = "AchieveUp_Badges"
    ACHIEVEUP_PROGRESS_COLLECTION = "AchieveUp_Progress"
    ACHIEVEUP_ANALYTICS_COLLECTION = "AchieveUp_Analytics"
    ACHIEVEUP_CANVAS_COURSES_COLLECTION = "AchieveUp_Canvas_Courses"
    ACHIEVEUP_CANVAS_QUIZZES_COLLECTION = "AchieveUp_Canvas_Quizzes"
    ACHIEVEUP_CANVAS_QUESTIONS_COLLECTION = "AchieveUp_Canvas_Questions"
    
    # AchieveUp configuration
    ACHIEVEUP_JWT_SECRET = os.getenv("ACHIEVEUP_JWT_SECRET", "achieveup-secret-key-change-in-production")
    CANVAS_API_URL = os.getenv("CANVAS_API_URL", "https://webcourses.ucf.edu/api/v1")

    @classmethod
    def check_config(cls):
        """Method to ensure all necessary config variables are set."""
        missing = [
            var for var in [
                "DB_CONNECTION_STRING", "HEX_ENCRYPTION_KEY", 
                "OPENAI_KEY", "YOUTUBE_API_KEY"
            ]
            if not getattr(cls, var)
        ]
        if missing:
            raise EnvironmentError(f"Missing environment variables: {', '.join(missing)}")

# Run configuration check at startup
Config.check_config()
