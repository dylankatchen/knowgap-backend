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
        {"id": "student_demo_001_005", "name": "Jessica Martinez", "email": "jessica.m@ucf.edu", "sortable_name": "Martinez, Jessica", "enrollment_state": "active"},
        {"id": "student_demo_001_006", "name": "Ryan Thompson", "email": "ryan.t@ucf.edu", "sortable_name": "Thompson, Ryan", "enrollment_state": "active"},
        {"id": "student_demo_001_007", "name": "Ashley Brown", "email": "ashley.b@ucf.edu", "sortable_name": "Brown, Ashley", "enrollment_state": "active"},
        {"id": "student_demo_001_008", "name": "Kevin Wang", "email": "kevin.w@ucf.edu", "sortable_name": "Wang, Kevin", "enrollment_state": "active"},
        {"id": "student_demo_001_009", "name": "Amanda Davis", "email": "amanda.d@ucf.edu", "sortable_name": "Davis, Amanda", "enrollment_state": "active"},
        {"id": "student_demo_001_010", "name": "Tyler Jackson", "email": "tyler.j@ucf.edu", "sortable_name": "Jackson, Tyler", "enrollment_state": "active"},
        {"id": "student_demo_001_011", "name": "Melissa Garcia", "email": "melissa.g@ucf.edu", "sortable_name": "Garcia, Melissa", "enrollment_state": "active"},
        {"id": "student_demo_001_012", "name": "Brandon Lee", "email": "brandon.l@ucf.edu", "sortable_name": "Lee, Brandon", "enrollment_state": "active"},
        {"id": "student_demo_001_013", "name": "Rachel Wilson", "email": "rachel.w@ucf.edu", "sortable_name": "Wilson, Rachel", "enrollment_state": "active"},
        {"id": "student_demo_001_014", "name": "Jordan Smith", "email": "jordan.s@ucf.edu", "sortable_name": "Smith, Jordan", "enrollment_state": "active"},
        {"id": "student_demo_001_015", "name": "Stephanie Liu", "email": "stephanie.l@ucf.edu", "sortable_name": "Liu, Stephanie", "enrollment_state": "active"},
        {"id": "student_demo_001_016", "name": "Austin Miller", "email": "austin.m@ucf.edu", "sortable_name": "Miller, Austin", "enrollment_state": "active"},
        {"id": "student_demo_001_017", "name": "Nicole Anderson", "email": "nicole.a@ucf.edu", "sortable_name": "Anderson, Nicole", "enrollment_state": "active"},
        {"id": "student_demo_001_018", "name": "Justin Park", "email": "justin.p@ucf.edu", "sortable_name": "Park, Justin", "enrollment_state": "active"},
        {"id": "student_demo_001_019", "name": "Samantha Taylor", "email": "samantha.t@ucf.edu", "sortable_name": "Taylor, Samantha", "enrollment_state": "active"},
        {"id": "student_demo_001_020", "name": "Alex Johnson", "email": "alex.j@ucf.edu", "sortable_name": "Johnson, Alex", "enrollment_state": "active"},
        {"id": "student_demo_001_021", "name": "Lauren White", "email": "lauren.w@ucf.edu", "sortable_name": "White, Lauren", "enrollment_state": "active"},
        {"id": "student_demo_001_022", "name": "Connor Davis", "email": "connor.d@ucf.edu", "sortable_name": "Davis, Connor", "enrollment_state": "active"},
        {"id": "student_demo_001_023", "name": "Megan Lee", "email": "megan.l@ucf.edu", "sortable_name": "Lee, Megan", "enrollment_state": "active"},
        {"id": "student_demo_001_024", "name": "Ethan Brown", "email": "ethan.b@ucf.edu", "sortable_name": "Brown, Ethan", "enrollment_state": "active"},
        {"id": "student_demo_001_025", "name": "Olivia Martinez", "email": "olivia.m@ucf.edu", "sortable_name": "Martinez, Olivia", "enrollment_state": "active"}
    ],
    "demo_002": [
        {"id": "student_demo_002_001", "name": "Noah Wilson", "email": "noah.w@ucf.edu", "sortable_name": "Wilson, Noah", "enrollment_state": "active"},
        {"id": "student_demo_002_002", "name": "Emma Garcia", "email": "emma.g@ucf.edu", "sortable_name": "Garcia, Emma", "enrollment_state": "active"},
        {"id": "student_demo_002_003", "name": "Liam Taylor", "email": "liam.t@ucf.edu", "sortable_name": "Taylor, Liam", "enrollment_state": "active"},
        {"id": "student_demo_002_004", "name": "Ava Anderson", "email": "ava.a@ucf.edu", "sortable_name": "Anderson, Ava", "enrollment_state": "active"},
        {"id": "student_demo_002_005", "name": "William Thomas", "email": "william.t@ucf.edu", "sortable_name": "Thomas, William", "enrollment_state": "active"},
        {"id": "student_demo_002_006", "name": "Sophia Jackson", "email": "sophia.j@ucf.edu", "sortable_name": "Jackson, Sophia", "enrollment_state": "active"},
        {"id": "student_demo_002_007", "name": "James White", "email": "james.w@ucf.edu", "sortable_name": "White, James", "enrollment_state": "active"},
        {"id": "student_demo_002_008", "name": "Isabella Harris", "email": "isabella.h@ucf.edu", "sortable_name": "Harris, Isabella", "enrollment_state": "active"},
        {"id": "student_demo_002_009", "name": "Benjamin Clark", "email": "benjamin.c@ucf.edu", "sortable_name": "Clark, Benjamin", "enrollment_state": "active"},
        {"id": "student_demo_002_010", "name": "Mia Lewis", "email": "mia.l@ucf.edu", "sortable_name": "Lewis, Mia", "enrollment_state": "active"},
        {"id": "student_demo_002_011", "name": "Lucas Robinson", "email": "lucas.r@ucf.edu", "sortable_name": "Robinson, Lucas", "enrollment_state": "active"},
        {"id": "student_demo_002_012", "name": "Charlotte Walker", "email": "charlotte.w@ucf.edu", "sortable_name": "Walker, Charlotte", "enrollment_state": "active"},
        {"id": "student_demo_002_013", "name": "Mason Hall", "email": "mason.h@ucf.edu", "sortable_name": "Hall, Mason", "enrollment_state": "active"},
        {"id": "student_demo_002_014", "name": "Amelia Young", "email": "amelia.y@ucf.edu", "sortable_name": "Young, Amelia", "enrollment_state": "active"},
        {"id": "student_demo_002_015", "name": "Ethan King", "email": "ethan.k@ucf.edu", "sortable_name": "King, Ethan", "enrollment_state": "active"},
        {"id": "student_demo_002_016", "name": "Harper Wright", "email": "harper.w@ucf.edu", "sortable_name": "Wright, Harper", "enrollment_state": "active"},
        {"id": "student_demo_002_017", "name": "Alexander Green", "email": "alexander.g@ucf.edu", "sortable_name": "Green, Alexander", "enrollment_state": "active"},
        {"id": "student_demo_002_018", "name": "Evelyn Baker", "email": "evelyn.b@ucf.edu", "sortable_name": "Baker, Evelyn", "enrollment_state": "active"},
        {"id": "student_demo_002_019", "name": "Henry Adams", "email": "henry.a@ucf.edu", "sortable_name": "Adams, Henry", "enrollment_state": "active"},
        {"id": "student_demo_002_020", "name": "Abigail Nelson", "email": "abigail.n@ucf.edu", "sortable_name": "Nelson, Abigail", "enrollment_state": "active"},
        {"id": "student_demo_002_021", "name": "Sebastian Carter", "email": "sebastian.c@ucf.edu", "sortable_name": "Carter, Sebastian", "enrollment_state": "active"},
        {"id": "student_demo_002_022", "name": "Elizabeth Mitchell", "email": "elizabeth.m@ucf.edu", "sortable_name": "Mitchell, Elizabeth", "enrollment_state": "active"},
        {"id": "student_demo_002_023", "name": "Jack Perez", "email": "jack.p@ucf.edu", "sortable_name": "Perez, Jack", "enrollment_state": "active"},
        {"id": "student_demo_002_024", "name": "Sofia Roberts", "email": "sofia.r@ucf.edu", "sortable_name": "Roberts, Sofia", "enrollment_state": "active"},
        {"id": "student_demo_002_025", "name": "Owen Turner", "email": "owen.t@ucf.edu", "sortable_name": "Turner, Owen", "enrollment_state": "active"},
        {"id": "student_demo_002_026", "name": "Avery Phillips", "email": "avery.p@ucf.edu", "sortable_name": "Phillips, Avery", "enrollment_state": "active"},
        {"id": "student_demo_002_027", "name": "Daniel Campbell", "email": "daniel.c@ucf.edu", "sortable_name": "Campbell, Daniel", "enrollment_state": "active"},
        {"id": "student_demo_002_028", "name": "Ella Parker", "email": "ella.p@ucf.edu", "sortable_name": "Parker, Ella", "enrollment_state": "active"},
        {"id": "student_demo_002_029", "name": "Matthew Evans", "email": "matthew.e@ucf.edu", "sortable_name": "Evans, Matthew", "enrollment_state": "active"},
        {"id": "student_demo_002_030", "name": "Madison Edwards", "email": "madison.e@ucf.edu", "sortable_name": "Edwards, Madison", "enrollment_state": "active"}
    ],
    "demo_003": [
        {"id": "student_demo_003_001", "name": "David Collins", "email": "david.c@ucf.edu", "sortable_name": "Collins, David", "enrollment_state": "active"},
        {"id": "student_demo_003_002", "name": "Chloe Stewart", "email": "chloe.s@ucf.edu", "sortable_name": "Stewart, Chloe", "enrollment_state": "active"},
        {"id": "student_demo_003_003", "name": "Joseph Sanchez", "email": "joseph.s@ucf.edu", "sortable_name": "Sanchez, Joseph", "enrollment_state": "active"},
        {"id": "student_demo_003_004", "name": "Grace Morris", "email": "grace.m@ucf.edu", "sortable_name": "Morris, Grace", "enrollment_state": "active"},
        {"id": "student_demo_003_005", "name": "Christopher Rogers", "email": "christopher.r@ucf.edu", "sortable_name": "Rogers, Christopher", "enrollment_state": "active"},
        {"id": "student_demo_003_006", "name": "Victoria Reed", "email": "victoria.r@ucf.edu", "sortable_name": "Reed, Victoria", "enrollment_state": "active"},
        {"id": "student_demo_003_007", "name": "Andrew Cook", "email": "andrew.c@ucf.edu", "sortable_name": "Cook, Andrew", "enrollment_state": "active"},
        {"id": "student_demo_003_008", "name": "Riley Morgan", "email": "riley.m@ucf.edu", "sortable_name": "Morgan, Riley", "enrollment_state": "active"},
        {"id": "student_demo_003_009", "name": "Joshua Bell", "email": "joshua.b@ucf.edu", "sortable_name": "Bell, Joshua", "enrollment_state": "active"},
        {"id": "student_demo_003_010", "name": "Aria Murphy", "email": "aria.m@ucf.edu", "sortable_name": "Murphy, Aria", "enrollment_state": "active"},
        {"id": "student_demo_003_011", "name": "Ryan Bailey", "email": "ryan.b@ucf.edu", "sortable_name": "Bailey, Ryan", "enrollment_state": "active"},
        {"id": "student_demo_003_012", "name": "Lily Rivera", "email": "lily.r@ucf.edu", "sortable_name": "Rivera, Lily", "enrollment_state": "active"},
        {"id": "student_demo_003_013", "name": "Nathan Cooper", "email": "nathan.c@ucf.edu", "sortable_name": "Cooper, Nathan", "enrollment_state": "active"},
        {"id": "student_demo_003_014", "name": "Zoe Richardson", "email": "zoe.r@ucf.edu", "sortable_name": "Richardson, Zoe", "enrollment_state": "active"},
        {"id": "student_demo_003_015", "name": "Isaac Cox", "email": "isaac.c@ucf.edu", "sortable_name": "Cox, Isaac", "enrollment_state": "active"},
        {"id": "student_demo_003_016", "name": "Hannah Howard", "email": "hannah.h@ucf.edu", "sortable_name": "Howard, Hannah", "enrollment_state": "active"},
        {"id": "student_demo_003_017", "name": "Kyle Ward", "email": "kyle.w@ucf.edu", "sortable_name": "Ward, Kyle", "enrollment_state": "active"},
        {"id": "student_demo_003_018", "name": "Layla Torres", "email": "layla.t@ucf.edu", "sortable_name": "Torres, Layla", "enrollment_state": "active"},
        {"id": "student_demo_003_019", "name": "Kevin Peterson", "email": "kevin.p@ucf.edu", "sortable_name": "Peterson, Kevin", "enrollment_state": "active"},
        {"id": "student_demo_003_020", "name": "Scarlett Gray", "email": "scarlett.g@ucf.edu", "sortable_name": "Gray, Scarlett", "enrollment_state": "active"},
        {"id": "student_demo_003_021", "name": "Brian Ramirez", "email": "brian.r@ucf.edu", "sortable_name": "Ramirez, Brian", "enrollment_state": "active"},
        {"id": "student_demo_003_022", "name": "Violet James", "email": "violet.j@ucf.edu", "sortable_name": "James, Violet", "enrollment_state": "active"}
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