# services/achieveup_canvas_demo_service.py

"""
Canvas Demo Service for AchieveUp
=================================

This service provides mock Canvas API responses for demo purposes.
It simulates real Canvas data for the demo instructor account,
allowing full demonstration of AchieveUp features without requiring
actual Canvas API access.

Used when:
- Demo Canvas token is detected
- Canvas API is unavailable
- Testing environment
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Demo Canvas token identifier
DEMO_CANVAS_TOKEN = "1234567890abcdef" * 4

# Mock Canvas courses for demo instructor
DEMO_CANVAS_COURSES = [
    {
        "id": "demo_001",
        "name": "Web Development Fundamentals",
        "course_code": "COP3530",
        "sis_course_id": "COP3530-001-Fall2024",
        "start_at": "2024-08-26T00:00:00Z",
        "end_at": "2024-12-15T23:59:59Z",
        "enrollment_term_id": 12345,
        "total_students": 25,
        "workflow_state": "available",
        "public_description": "Introduction to web development with HTML, CSS, JavaScript, and modern frameworks. Students will learn to create responsive, accessible web applications.",
        "syllabus_body": "<h2>Course Description</h2><p>This course covers fundamental web development technologies...</p>",
        "default_view": "modules",
        "apply_assignment_group_weights": True,
        "calendar": {
            "ics": "https://canvas.instructure.com/feeds/calendars/course_12345.ics"
        },
        "permissions": {
            "create_discussion_topic": True,
            "create_announcement": True
        }
    },
    {
        "id": "demo_002",
        "name": "Database Management Systems",
        "course_code": "CIS4301",
        "sis_course_id": "CIS4301-001-Fall2024",
        "start_at": "2024-08-26T00:00:00Z",
        "end_at": "2024-12-15T23:59:59Z",
        "enrollment_term_id": 12345,
        "total_students": 30,
        "workflow_state": "available",
        "public_description": "Comprehensive coverage of relational database design, SQL programming, and database administration.",
        "syllabus_body": "<h2>Course Objectives</h2><p>Students will master database design principles...</p>",
        "default_view": "assignments",
        "apply_assignment_group_weights": True
    },
    {
        "id": "demo_003",
        "name": "Computer Networks",
        "course_code": "CNT4007",
        "sis_course_id": "CNT4007-001-Fall2024",
        "start_at": "2024-08-26T00:00:00Z",
        "end_at": "2024-12-15T23:59:59Z",
        "enrollment_term_id": 12345,
        "total_students": 22,
        "workflow_state": "available",
        "public_description": "Study of network protocols, security, and distributed systems architecture.",
        "syllabus_body": "<h2>Learning Outcomes</h2><p>Understand network protocols and security...</p>",
        "default_view": "wiki"
    }
]

# Mock quizzes for each course
DEMO_CANVAS_QUIZZES = {
    "demo_001": [
        {
            "id": "quiz_demo_001_1",
            "title": "HTML & CSS Fundamentals Quiz",
            "html_url": "https://canvas.instructure.com/courses/demo_001/quizzes/quiz_demo_001_1",
            "mobile_url": "https://canvas.instructure.com/courses/demo_001/quizzes/quiz_demo_001_1?force_user=1&persist_headless=1",
            "description": "<p>Test your understanding of HTML elements and CSS styling.</p>",
            "quiz_type": "assignment",
            "assignment_group_id": 12345,
            "time_limit": 60,
            "shuffle_answers": True,
            "hide_results": None,
            "show_correct_answers": True,
            "show_correct_answers_at": "2024-10-15T23:59:59Z",
            "hide_correct_answers_at": "2024-10-20T23:59:59Z",
            "allowed_attempts": 2,
            "scoring_policy": "keep_highest",
            "one_question_at_a_time": False,
            "cant_go_back": False,
            "access_code": None,
            "ip_filter": None,
            "due_at": "2024-10-15T23:59:59Z",
            "lock_at": "2024-10-16T23:59:59Z",
            "unlock_at": "2024-10-01T00:00:00Z",
            "published": True,
            "unpublishable": False,
            "locked_for_user": False,
            "question_count": 4,
            "points_possible": 38,
            "question_types": ["multiple_choice_question", "essay_question", "short_answer_question", "file_upload_question"]
        },
        {
            "id": "quiz_demo_001_2",
            "title": "JavaScript Programming Quiz",
            "description": "<p>Assess your JavaScript knowledge and programming skills.</p>",
            "quiz_type": "assignment",
            "time_limit": 90,
            "allowed_attempts": 1,
            "scoring_policy": "keep_highest",
            "due_at": "2024-11-01T23:59:59Z",
            "published": True,
            "question_count": 6,
            "points_possible": 45
        }
    ],
    "demo_002": [
        {
            "id": "quiz_demo_002_1",
            "title": "SQL Basics Quiz",
            "description": "<p>Test your SQL query writing and database design skills.</p>",
            "quiz_type": "assignment",
            "time_limit": 75,
            "allowed_attempts": 2,
            "scoring_policy": "keep_highest",
            "due_at": "2024-10-20T23:59:59Z",
            "published": True,
            "question_count": 3,
            "points_possible": 42
        }
    ],
    "demo_003": [
        {
            "id": "quiz_demo_003_1",
            "title": "Network Protocols Quiz",
            "description": "<p>Evaluate your understanding of network protocols and OSI model.</p>",
            "quiz_type": "assignment",
            "time_limit": 60,
            "allowed_attempts": 1,
            "scoring_policy": "keep_highest",
            "due_at": "2024-10-25T23:59:59Z",
            "published": True,
            "question_count": 3,
            "points_possible": 37
        }
    ]
}

# Mock quiz questions
DEMO_CANVAS_QUESTIONS = {
    "quiz_demo_001_1": [
        {
            "id": "q1_001",
            "quiz_id": "quiz_demo_001_1",
            "position": 1,
            "question_name": "JavaScript Variables",
            "question_type": "multiple_choice_question",
            "question_text": "<p>What is the difference between <code>let</code> and <code>var</code> in JavaScript?</p>",
            "points_possible": 5,
            "correct_comments": "<p>Correct! <code>let</code> has block scope while <code>var</code> has function scope.</p>",
            "incorrect_comments": "<p>Review the scope differences between let and var declarations.</p>",
            "answers": [
                {
                    "id": "a1",
                    "text": "let has block scope, var has function scope",
                    "weight": 100,
                    "comments": "Correct understanding of scope differences"
                },
                {
                    "id": "a2", 
                    "text": "let has function scope, var has block scope",
                    "weight": 0,
                    "comments": "Incorrect - this is backwards"
                },
                {
                    "id": "a3",
                    "text": "There is no difference",
                    "weight": 0,
                    "comments": "Incorrect - there are significant differences"
                }
            ]
        },
        {
            "id": "q1_002",
            "quiz_id": "quiz_demo_001_1", 
            "position": 2,
            "question_name": "CSS Grid Layout",
            "question_type": "essay_question",
            "question_text": "<p>How do you create a responsive grid layout using CSS Grid? Provide a detailed explanation with code examples.</p>",
            "points_possible": 10,
            "correct_comments": "<p>Excellent explanation of CSS Grid properties and responsive design!</p>",
            "incorrect_comments": "<p>Review CSS Grid properties like grid-template-columns and auto-fit.</p>"
        },
        {
            "id": "q1_003",
            "quiz_id": "quiz_demo_001_1",
            "position": 3, 
            "question_name": "Semantic HTML",
            "question_type": "short_answer_question",
            "question_text": "<p>Explain the purpose of semantic HTML elements like &lt;header&gt;, &lt;nav&gt;, &lt;main&gt;, and &lt;footer&gt;.</p>",
            "points_possible": 8,
            "correct_comments": "<p>Good understanding of semantic HTML structure!</p>",
            "incorrect_comments": "<p>Review how semantic elements improve accessibility and SEO.</p>"
        },
        {
            "id": "q1_004",
            "quiz_id": "quiz_demo_001_1",
            "position": 4,
            "question_name": "Email Validation Function",
            "question_type": "file_upload_question", 
            "question_text": "<p>Write a JavaScript function that validates an email address using regular expressions. Upload your solution as a .js file.</p>",
            "points_possible": 15,
            "correct_comments": "<p>Excellent implementation of email validation!</p>",
            "incorrect_comments": "<p>Review regular expression patterns for email validation.</p>"
        }
    ],
    "quiz_demo_002_1": [
        {
            "id": "q2_001",
            "quiz_id": "quiz_demo_002_1",
            "position": 1,
            "question_name": "SQL Top Customers Query",
            "question_type": "file_upload_question",
            "question_text": "<p>Write a SQL query to find the top 5 customers by total order value. Use the tables: customers, orders, order_items.</p>",
            "points_possible": 12,
            "correct_comments": "<p>Excellent SQL query with proper joins and aggregation!</p>",
            "incorrect_comments": "<p>Review JOIN operations and GROUP BY with aggregate functions.</p>"
        },
        {
            "id": "q2_002",
            "quiz_id": "quiz_demo_002_1",
            "position": 2,
            "question_name": "Database Indexes",
            "question_type": "essay_question",
            "question_text": "<p>What is the difference between a clustered and non-clustered index? When would you use each type?</p>",
            "points_possible": 10,
            "correct_comments": "<p>Great explanation of index types and their use cases!</p>",
            "incorrect_comments": "<p>Review how clustered indexes affect physical data storage.</p>"
        },
        {
            "id": "q2_003",
            "quiz_id": "quiz_demo_002_1",
            "position": 3,
            "question_name": "Library Database Design",
            "question_type": "essay_question",
            "question_text": "<p>Design a normalized database schema for a library management system. Include entities, relationships, and explain your normalization decisions.</p>",
            "points_possible": 20,
            "correct_comments": "<p>Excellent database design with proper normalization!</p>",
            "incorrect_comments": "<p>Review normalization forms and entity relationship modeling.</p>"
        }
    ],
    "quiz_demo_003_1": [
        {
            "id": "q3_001",
            "quiz_id": "quiz_demo_003_1",
            "position": 1,
            "question_name": "OSI Model Layers",
            "question_type": "essay_question",
            "question_text": "<p>Explain the OSI model and describe the function of each of its seven layers. Provide examples of protocols at each layer.</p>",
            "points_possible": 15,
            "correct_comments": "<p>Comprehensive understanding of the OSI model!</p>",
            "incorrect_comments": "<p>Review the seven layers and their specific functions.</p>"
        },
        {
            "id": "q3_002",
            "quiz_id": "quiz_demo_003_1",
            "position": 2,
            "question_name": "Firewall Configuration",
            "question_type": "short_answer_question",
            "question_text": "<p>Configure a firewall rule to allow HTTP traffic on port 80 while blocking all other incoming traffic. Provide the command or configuration syntax.</p>",
            "points_possible": 10,
            "correct_comments": "<p>Correct firewall rule configuration!</p>",
            "incorrect_comments": "<p>Review firewall syntax and port configuration.</p>"
        },
        {
            "id": "q3_003",
            "quiz_id": "quiz_demo_003_1",
            "position": 3,
            "question_name": "Network Troubleshooting",
            "question_type": "essay_question",
            "question_text": "<p>A user reports they cannot access a website. Describe the troubleshooting steps you would take using tools like ping, traceroute, and nslookup.</p>",
            "points_possible": 12,
            "correct_comments": "<p>Systematic approach to network troubleshooting!</p>",
            "incorrect_comments": "<p>Review network diagnostic tools and troubleshooting methodology.</p>"
        }
    ]
}

# Mock student enrollments
DEMO_CANVAS_STUDENTS = {
    "demo_001": [
        {"id": "student_demo_001_001", "name": "Emily Rodriguez", "email": "emily.r@ucf.edu", "sortable_name": "Rodriguez, Emily", "enrollment_state": "active"},
        {"id": "student_demo_001_002", "name": "Michael Chen", "email": "michael.c@ucf.edu", "sortable_name": "Chen, Michael", "enrollment_state": "active"},
        {"id": "student_demo_001_003", "name": "Sarah Johnson", "email": "sarah.j@ucf.edu", "sortable_name": "Johnson, Sarah", "enrollment_state": "active"},
        {"id": "student_demo_001_004", "name": "David Kim", "email": "david.k@ucf.edu", "sortable_name": "Kim, David", "enrollment_state": "active"},
        {"id": "student_demo_001_005", "name": "Jessica Martinez", "email": "jessica.m@ucf.edu", "sortable_name": "Martinez, Jessica", "enrollment_state": "active"}
        # ... additional students would be here
    ],
    "demo_002": [
        {"id": "student_demo_002_001", "name": "Ryan Thompson", "email": "ryan.t@ucf.edu", "sortable_name": "Thompson, Ryan", "enrollment_state": "active"},
        {"id": "student_demo_002_002", "name": "Ashley Brown", "email": "ashley.b@ucf.edu", "sortable_name": "Brown, Ashley", "enrollment_state": "active"},
        {"id": "student_demo_002_003", "name": "Kevin Wang", "email": "kevin.w@ucf.edu", "sortable_name": "Wang, Kevin", "enrollment_state": "active"},
        {"id": "student_demo_002_004", "name": "Amanda Davis", "email": "amanda.d@ucf.edu", "sortable_name": "Davis, Amanda", "enrollment_state": "active"},
        {"id": "student_demo_002_005", "name": "Tyler Jackson", "email": "tyler.j@ucf.edu", "sortable_name": "Jackson, Tyler", "enrollment_state": "active"}
        # ... additional students would be here
    ],
    "demo_003": [
        {"id": "student_demo_003_001", "name": "Melissa Garcia", "email": "melissa.g@ucf.edu", "sortable_name": "Garcia, Melissa", "enrollment_state": "active"},
        {"id": "student_demo_003_002", "name": "Brandon Lee", "email": "brandon.l@ucf.edu", "sortable_name": "Lee, Brandon", "enrollment_state": "active"},
        {"id": "student_demo_003_003", "name": "Rachel Wilson", "email": "rachel.w@ucf.edu", "sortable_name": "Wilson, Rachel", "enrollment_state": "active"},
        {"id": "student_demo_003_004", "name": "Jordan Smith", "email": "jordan.s@ucf.edu", "sortable_name": "Smith, Jordan", "enrollment_state": "active"},
        {"id": "student_demo_003_005", "name": "Stephanie Liu", "email": "stephanie.l@ucf.edu", "sortable_name": "Liu, Stephanie", "enrollment_state": "active"}
        # ... additional students would be here
    ]
}

def is_demo_token(canvas_token: str) -> bool:
    """Check if the provided Canvas token is the demo token."""
    return canvas_token == DEMO_CANVAS_TOKEN

async def get_demo_instructor_courses() -> list:
    """Return mock Canvas courses for demo instructor."""
    logger.info("Returning demo Canvas courses")
    return DEMO_CANVAS_COURSES

async def get_demo_course_details(course_id: str) -> dict:
    """Return detailed course information for demo course."""
    for course in DEMO_CANVAS_COURSES:
        if course["id"] == course_id:
            logger.info(f"Returning demo course details for {course_id}")
            return course
    
    return {
        'error': f'Demo course {course_id} not found',
        'statusCode': 404
    }

async def get_demo_course_quizzes(course_id: str) -> list:
    """Return mock quizzes for demo course."""
    if course_id in DEMO_CANVAS_QUIZZES:
        logger.info(f"Returning demo quizzes for course {course_id}")
        return DEMO_CANVAS_QUIZZES[course_id]
    
    return []

async def get_demo_quiz_questions(quiz_id: str) -> list:
    """Return mock questions for demo quiz."""
    if quiz_id in DEMO_CANVAS_QUESTIONS:
        logger.info(f"Returning demo questions for quiz {quiz_id}")
        return DEMO_CANVAS_QUESTIONS[quiz_id]
    
    return []

async def get_demo_course_students(course_id: str) -> list:
    """Return mock students for demo course."""
    if course_id in DEMO_CANVAS_STUDENTS:
        logger.info(f"Returning demo students for course {course_id}")
        return DEMO_CANVAS_STUDENTS[course_id]
    
    return []

async def validate_demo_canvas_token(canvas_token: str, canvas_token_type: str = 'instructor') -> dict:
    """Validate demo Canvas token."""
    if canvas_token == DEMO_CANVAS_TOKEN and canvas_token_type == 'instructor':
        logger.info("Demo Canvas token validated successfully")
        return {
            'valid': True,
            'message': 'Demo Canvas token is valid',
            'user_info': {
                'id': 'demo_instructor_canvas_id',
                'name': 'Dr. Jane Smith',
                'email': 'demo.instructor@ucf.edu',
                'login_id': 'jsmith@ucf.edu'
            },
            'permissions': {
                'can_create_courses': True,
                'can_manage_students': True,
                'can_create_assignments': True,
                'can_grade': True
            }
        }
    
    return {
        'valid': False,
        'message': 'Invalid demo Canvas token'
    } 