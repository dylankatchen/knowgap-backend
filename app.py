import logging
import asyncio
from quart import Quart, request
from quart_cors import cors
from dotenv import load_dotenv
from utils.encryption_utils import decrypt_token

from services.canvas_submissions_service import sync_course_submissions_direct
from services.course_service import update_quiz_questions_per_course

from routes.base_routes import init_base_routes
from routes.auth_routes import auth_bp
from routes.canvas_routes import canvas_bp
from routes.achieveup_routes import achieveup_bp
from routes.skill_video_routes import skill_video_bp
from mongodb import get_db
from utils.security_utils import init_security
from utils.rate_limits import init_rate_limits

from config import Config

# Set up logging
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Quart app
app = Quart(__name__)

# Configure CORS. Only these sites may call the API from a browser; the
# frontend sends its login token in the Authorization header, not a cookie,
# so credentials aren't allowed.
app = cors(app,
    allow_origin=[
        "http://localhost:3000",  # Allow AchieveUp frontend development
        "http://localhost:5001",  # Allow local API testing
        "http://127.0.0.1:5001",  # Allow local API testing (IP)
        Config.FRONTEND_URL,
        Config.FRONTEND_HOSTING_URL
    ],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    expose_headers=["Retry-After"],  # how long a rate-limited caller should wait
    allow_credentials=False,
    max_age=3600
)

# Log incoming requests
@app.before_request
async def log_request():
    logger.info("%s %s", request.method, request.path)

# HTTPS redirect and security headers first, so a plain-HTTP request is
# redirected before the rate limiter counts it.
init_security(app)
init_rate_limits(app)

# Initialize routes first
init_base_routes(app)

# Register AchieveUp blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(canvas_bp)
app.register_blueprint(achieveup_bp)
app.register_blueprint(skill_video_bp)

# Apply CORS after routes are initialized

# MongoDB setup
HEX_ENCRYPTION_KEY = Config.HEX_ENCRYPTION_KEY
encryption_key = bytes.fromhex(HEX_ENCRYPTION_KEY)

# Configure MongoDB client
# Only bypass SSL verification in development
db = get_db()

quizzes_collection = db[Config.QUIZZES_COLLECTION]

# Create indexes
async def create_indexes():
    try:
        logger.info("Attempting to create MongoDB indexes...")
        await quizzes_collection.create_index("course_id")
        course_descriptions_collection = db[Config.ACHIEVEUP_COURSE_DESCRIPTIONS_COLLECTION]
        await course_descriptions_collection.create_index(
            [("course_id", 1), ("instructor_id", 1)],
            unique=True,
            name="course_instructor_unique_idx"
        )
        badge_sharing_collection = db[Config.ACHIEVEUP_BADGE_SHARING_COLLECTION]
        await badge_sharing_collection.create_index(
            "canvas_student_id",
            unique=True,
            name="badge_sharing_canvas_student_id_unique_idx"
        )
        logger.info("Successfully created MongoDB indexes")
    except Exception as e:
        logger.error(f"Failed to create MongoDB indexes: {str(e)}")
        # Don't raise the exception - allow the app to continue running
        # The indexes will be created when MongoDB is available

    # Separate block so a failure here can't skip the indexes above.
    try:
        course_channels_collection = db[
            Config.ACHIEVEUP_COURSE_CHANNELS_COLLECTION]
        await course_channels_collection.create_index(
            [("course_id", 1), ("instructor_id", 1)],
            unique=True,
            name="course_instructor_unique_idx"
        )
    except Exception as e:
        logger.error(f"Failed to create course channels index: {str(e)}")

async def scheduled_update():
    logger.info("Scheduled update started")
    try:
        # Test MongoDB connection first
        await db.command('ping')
        logger.info("MongoDB connection successful")
        
        # Process AchieveUp Users (Instructors with Canvas Tokens)
        achieveup_users = db[Config.ACHIEVEUP_USERS_COLLECTION]
        link = Config.CANVAS_DOMAIN # Default link for AchieveUp users
        
        async for user in achieveup_users.find({"role": "instructor", "canvas_api_token": {"$exists": True, "$ne": None}}):
            try:
                # Decrypt token
                access_token = decrypt_token(encryption_key, user.get('canvas_api_token'))
                if not access_token:
                    continue
                    
                # Fetch courses for this user (we don't store course_ids in user doc, need to fetch)
                from services.achieveup_canvas_service import get_instructor_courses, official_course_name
                courses = await get_instructor_courses(access_token)
                
                if isinstance(courses, list):
                    for course in courses:
                        course_id = str(course.get('id'))
                        logger.info("Processing AchieveUp course ID: %s for user_id %s", course_id, user.get('user_id'))
                        
                        try:
                            # Sync data
                            await update_quiz_questions_per_course(course_id, access_token, link)
                            
                            # Update mastery
                            await sync_course_submissions_direct(access_token, course_id, official_course_name(course))
                            
                        except Exception as course_error:
                            logger.error("Error processing course ID %s: %s", course_id, course_error)
                        
                        # Rate limit safeguard: pause between courses
                        await asyncio.sleep(1)
            except Exception as user_error:
                logger.error("Error processing user_id %s: %s", user.get('user_id'), user_error)
            
            # Rate limit safeguard: pause between teachers
            await asyncio.sleep(2)

    except Exception as e:
        logger.error("Error in scheduled update: %s", str(e))
        logger.error("Full error details:", exc_info=True)

async def schedule_updates():
    while True:
        try:
            await scheduled_update()
        except Exception as e:
            logger.error(f"Error in schedule_updates: {str(e)}")
        await asyncio.sleep(Config.SET_TIMER)

@app.before_serving
async def startup():
    logger.info("Starting application...")
    try:
        # Try to create indexes, but don't fail if it doesn't work
        await create_indexes()
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
    
    # Start the update loop in the background
    asyncio.create_task(schedule_updates())
    logger.info("Application startup complete")

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5001)
