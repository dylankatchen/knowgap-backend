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

    # Environment-based database selection
    ENV = os.getenv("ENVIRONMENT", "development")
    DATABASE = "KnowGap_Dev" if ENV == "development" else "KnowGap"

    # Database collection names (no prefix needed - separate databases)
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
    ACHIEVEUP_SKILL_ASSIGNMENTS_COLLECTION = "AchieveUp_Skill_Assignments"
    ACHIEVEUP_QUESTION_SKILLS_COLLECTION = "AchieveUp_Question_Skills"
    ACHIEVEUP_BADGES_COLLECTION = "AchieveUp_Badges"
    ACHIEVEUP_USER_BADGES_COLLECTION = "AchieveUp_User_Badges"
    ACHIEVEUP_BADGE_PROGRESS_COLLECTION = "AchieveUp_Badge_Progress"
    ACHIEVEUP_USER_PROGRESS_COLLECTION = "AchieveUp_User_Progress"
    ACHIEVEUP_PROGRESS_ANALYTICS_COLLECTION = "AchieveUp_Progress_Analytics"
    ACHIEVEUP_PROGRESS_COLLECTION = "AchieveUp_Progress"
    ACHIEVEUP_ANALYTICS_COLLECTION = "AchieveUp_Analytics"
    ACHIEVEUP_COURSE_ANALYTICS_COLLECTION = "AchieveUp_Course_Analytics"
    ACHIEVEUP_STUDENT_ANALYTICS_COLLECTION = "AchieveUp_Student_Analytics"
    ACHIEVEUP_SKILL_ANALYTICS_COLLECTION = "AchieveUp_Skill_Analytics"
    ACHIEVEUP_CANVAS_COURSES_COLLECTION = "AchieveUp_Canvas_Courses"
    ACHIEVEUP_CANVAS_QUIZZES_COLLECTION = "AchieveUp_Canvas_Quizzes"
    ACHIEVEUP_CANVAS_QUESTIONS_COLLECTION = "AchieveUp_Canvas_Questions"
    ACHIEVEUP_QUIZ_SUBMISSIONS_COLLECTION = "AchieveUp_Quiz_Submissions"
    
    # AchieveUp configuration
    ACHIEVEUP_JWT_SECRET = os.getenv("ACHIEVEUP_JWT_SECRET", "achieveup-secret-key-change-in-production")
    CANVAS_API_URL = os.getenv("CANVAS_API_URL", "https://webcourses.ucf.edu/api/v1")
    
    # Canvas API Configuration
    CANVAS_API_RATE_LIMIT = int(os.getenv("CANVAS_API_RATE_LIMIT", "100"))  # requests per minute
    SUBMISSION_CACHE_TTL = int(os.getenv("SUBMISSION_CACHE_TTL", "3600"))  # 1 hour in seconds

    #AI configuration
    OPENAI_API_KEY= os.getenv("OPENAI_KEY")
    # Feature Flags
    ENABLE_DEMO_MODE = os.getenv("ENABLE_DEMO_MODE", "true").lower() == "true"  # Default to true for backward compatibility
    ENABLE_SUBMISSION_CACHE = os.getenv("ENABLE_SUBMISSION_CACHE", "false").lower() == "true"  # Default to false to minimize storage

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
