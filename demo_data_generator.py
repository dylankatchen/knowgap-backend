#!/usr/bin/env python3
"""
AchieveUp Demo Data Generator
============================

This script generates comprehensive demo data for testing the AchieveUp Instructor Portal.
It creates sample instructor accounts, courses, quizzes, questions, students, skill matrices,
and progress data to demonstrate the full functionality of the system.

Usage:
    python demo_data_generator.py

Requirements:
    - MongoDB connection
    - Backend environment configured
    - OpenAI API key (optional, for AI features)
"""

import asyncio
import uuid
import bcrypt
import random
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

# Demo data configuration
DEMO_INSTRUCTOR_EMAIL = "demo.instructor@ucf.edu"
DEMO_INSTRUCTOR_PASSWORD = "AchieveUp2024!"
DEMO_CANVAS_TOKEN = "1234567890abcdef" * 4  # 64-character demo token

# Sample course data
DEMO_COURSES = [
    {
        "id": "demo_001",
        "name": "Web Development Fundamentals",
        "code": "COP3530",
        "description": "Introduction to web development with HTML, CSS, JavaScript, and modern frameworks",
        "enrollment": 25
    },
    {
        "id": "demo_002", 
        "name": "Database Management Systems",
        "code": "CIS4301",
        "description": "Relational database design, SQL, and database administration",
        "enrollment": 30
    },
    {
        "id": "demo_003",
        "name": "Computer Networks",
        "code": "CNT4007",
        "description": "Network protocols, security, and distributed systems",
        "enrollment": 22
    }
]

# Sample skills for each course
COURSE_SKILLS = {
    "demo_001": [
        "HTML/CSS Fundamentals", "JavaScript Programming", "Responsive Design",
        "DOM Manipulation", "Event Handling", "CSS Grid & Flexbox",
        "Web Accessibility", "Browser Developer Tools", "Version Control (Git)",
        "Frontend Frameworks", "API Integration", "Web Performance"
    ],
    "demo_002": [
        "SQL Query Writing", "Database Design", "Data Normalization",
        "Entity-Relationship Modeling", "Index Optimization", "Stored Procedures",
        "Database Security", "Backup & Recovery", "Transaction Management",
        "NoSQL Databases", "Data Analytics", "Database Administration"
    ],
    "demo_003": [
        "Network Protocols (TCP/IP)", "Network Security", "Routing & Switching",
        "Wireless Networks", "Network Troubleshooting", "Firewall Configuration",
        "VPN Setup", "Network Monitoring", "OSI Model", "Distributed Systems",
        "Cloud Networking", "Network Performance"
    ]
}

# Sample quiz questions for each course
DEMO_QUESTIONS = {
    "demo_001": [
        {
            "id": "q1_001",
            "text": "What is the difference between let and var in JavaScript?",
            "type": "multiple_choice",
            "points": 5,
            "skills": ["JavaScript Programming", "Variable Scoping"]
        },
        {
            "id": "q1_002", 
            "text": "How do you create a responsive grid layout using CSS Grid?",
            "type": "essay",
            "points": 10,
            "skills": ["CSS Grid & Flexbox", "Responsive Design"]
        },
        {
            "id": "q1_003",
            "text": "Explain the purpose of semantic HTML elements.",
            "type": "short_answer",
            "points": 8,
            "skills": ["HTML/CSS Fundamentals", "Web Accessibility"]
        },
        {
            "id": "q1_004",
            "text": "Write a JavaScript function that validates an email address.",
            "type": "coding",
            "points": 15,
            "skills": ["JavaScript Programming", "DOM Manipulation"]
        }
    ],
    "demo_002": [
        {
            "id": "q2_001",
            "text": "Write a SQL query to find the top 5 customers by total order value.",
            "type": "coding",
            "points": 12,
            "skills": ["SQL Query Writing", "Data Analytics"]
        },
        {
            "id": "q2_002",
            "text": "What is the difference between a clustered and non-clustered index?",
            "type": "essay",
            "points": 10,
            "skills": ["Index Optimization", "Database Design"]
        },
        {
            "id": "q2_003",
            "text": "Design a normalized database schema for a library management system.",
            "type": "design",
            "points": 20,
            "skills": ["Entity-Relationship Modeling", "Data Normalization"]
        }
    ],
    "demo_003": [
        {
            "id": "q3_001",
            "text": "Explain the OSI model and its seven layers.",
            "type": "essay",
            "points": 15,
            "skills": ["OSI Model", "Network Protocols (TCP/IP)"]
        },
        {
            "id": "q3_002",
            "text": "Configure a firewall rule to allow HTTP traffic on port 80.",
            "type": "practical",
            "points": 10,
            "skills": ["Firewall Configuration", "Network Security"]
        },
        {
            "id": "q3_003",
            "text": "Troubleshoot a network connectivity issue using ping and traceroute.",
            "type": "problem_solving",
            "points": 12,
            "skills": ["Network Troubleshooting", "Network Monitoring"]
        }
    ]
}

# Sample student names
STUDENT_NAMES = [
    "Emily Rodriguez", "Michael Chen", "Sarah Johnson", "David Kim",
    "Jessica Martinez", "Ryan Thompson", "Ashley Brown", "Kevin Wang",
    "Amanda Davis", "Tyler Jackson", "Melissa Garcia", "Brandon Lee",
    "Rachel Wilson", "Jordan Smith", "Stephanie Liu", "Austin Miller",
    "Nicole Anderson", "Justin Park", "Samantha Taylor", "Alex Johnson",
    "Lauren White", "Connor Davis", "Megan Lee", "Ethan Brown",
    "Olivia Martinez", "Noah Wilson", "Emma Garcia", "Liam Taylor"
]

async def setup_database():
    """Initialize database connection and collections."""
    print("🔗 Connecting to MongoDB...")
    
    client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
    db = client[Config.DATABASE]
    
    # Collections
    users_collection = db["AchieveUp_Users"]
    skill_matrices_collection = db["AchieveUp_Skill_Matrices"]
    question_skills_collection = db["AchieveUp_Question_Skills"]
    progress_collection = db["AchieveUp_Progress"]
    analytics_collection = db["AchieveUp_Analytics"]
    
    print("✅ Database connection established")
    return db, users_collection, skill_matrices_collection, question_skills_collection, progress_collection, analytics_collection

async def create_demo_instructor(users_collection):
    """Create a demo instructor account."""
    print("👨‍🏫 Creating demo instructor account...")
    
    # Check if demo instructor already exists
    existing_instructor = await users_collection.find_one({'email': DEMO_INSTRUCTOR_EMAIL})
    if existing_instructor:
        print(f"✅ Demo instructor already exists: {DEMO_INSTRUCTOR_EMAIL}")
        return existing_instructor['user_id']
    
    # Create new instructor
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(DEMO_INSTRUCTOR_PASSWORD.encode('utf-8'), salt)
    
    # Encrypt demo Canvas token
            from utils.encryption_utils import encrypt_token
        encrypted_token = encrypt_token(bytes.fromhex(Config.HEX_ENCRYPTION_KEY), DEMO_CANVAS_TOKEN)
    
    instructor_id = str(uuid.uuid4())
    instructor_doc = {
        'user_id': instructor_id,
        'name': 'Dr. Jane Smith',
        'email': DEMO_INSTRUCTOR_EMAIL,
        'password': hashed_password.decode('utf-8'),
        'role': 'instructor',
        'canvas_token_type': 'instructor',
        'canvas_api_token': encrypted_token,
        'canvas_token_created_at': datetime.utcnow(),
        'canvas_token_last_validated': datetime.utcnow(),
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    await users_collection.insert_one(instructor_doc)
    
    print(f"✅ Demo instructor created:")
    print(f"   📧 Email: {DEMO_INSTRUCTOR_EMAIL}")
    print(f"   🔑 Password: {DEMO_INSTRUCTOR_PASSWORD}")
    print(f"   🎯 Role: Instructor")
    
    return instructor_id

async def create_skill_matrices(skill_matrices_collection):
    """Create skill matrices for demo courses."""
    print("📊 Creating skill matrices...")
    
    matrices_created = 0
    for course in DEMO_COURSES:
        course_id = course["id"]
        
        # Check if matrix already exists
        existing_matrix = await skill_matrices_collection.find_one({'course_id': course_id})
        if existing_matrix:
            print(f"   ⚠️  Skill matrix already exists for {course['name']}")
            continue
        
        matrix_id = str(uuid.uuid4())
        matrix_doc = {
            '_id': matrix_id,
            'course_id': course_id,
            'matrix_name': f"{course['name']} Skills",
            'skills': COURSE_SKILLS[course_id],
            'description': f"AI-generated skills for {course['name']}",
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        await skill_matrices_collection.insert_one(matrix_doc)
        matrices_created += 1
        print(f"   ✅ Created skill matrix for {course['name']} ({len(COURSE_SKILLS[course_id])} skills)")
    
    print(f"✅ Created {matrices_created} skill matrices")

async def create_question_assignments(question_skills_collection):
    """Create question-skill assignments."""
    print("🔗 Creating question-skill assignments...")
    
    assignments_created = 0
    for course_id, questions in DEMO_QUESTIONS.items():
        for question in questions:
            # Check if assignment already exists
            existing_assignment = await question_skills_collection.find_one({'question_id': question['id']})
            if existing_assignment:
                continue
            
            assignment_doc = {
                'course_id': course_id,
                'question_id': question['id'],
                'quiz_id': f"quiz_{course_id}",
                'skills': question['skills'],
                'ai_generated': True,
                'human_reviewed': False,
                'assigned_by_instructor': True,
                'instructor_id': 'demo_instructor',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            await question_skills_collection.insert_one(assignment_doc)
            assignments_created += 1
    
    print(f"✅ Created {assignments_created} question-skill assignments")

async def create_demo_students_and_progress(progress_collection):
    """Create demo students and their progress data."""
    print("👥 Creating demo students and progress data...")
    
    progress_records_created = 0
    
    for course in DEMO_COURSES:
        course_id = course["id"]
        course_skills = COURSE_SKILLS[course_id]
        num_students = course["enrollment"]
        
        # Select random students for this course
        selected_students = random.sample(STUDENT_NAMES, min(num_students, len(STUDENT_NAMES)))
        
        for i, student_name in enumerate(selected_students):
            student_id = f"student_{course_id}_{i+1:03d}"
            
            # Create progress for each skill
            for skill in course_skills:
                # Check if progress already exists
                existing_progress = await progress_collection.find_one({
                    'student_id': student_id,
                    'course_id': course_id,
                    'skill': skill
                })
                if existing_progress:
                    continue
                
                # Generate realistic progress data
                base_performance = random.uniform(0.3, 0.95)  # Student's general ability
                skill_difficulty = random.uniform(0.8, 1.2)   # Skill difficulty modifier
                
                attempts = random.randint(1, 5)
                scores = []
                for attempt in range(attempts):
                    # Simulate improvement over time
                    improvement_factor = 1 + (attempt * 0.1)
                    noise = random.uniform(-0.1, 0.1)
                    score = min(100, max(0, (base_performance * skill_difficulty * improvement_factor + noise) * 100))
                    scores.append(round(score, 1))
                
                final_score = scores[-1]
                completed = final_score >= 70  # 70% threshold for completion
                
                # Random activity dates in the last 30 days
                days_ago = random.randint(1, 30)
                activity_date = datetime.utcnow() - timedelta(days=days_ago)
                
                progress_doc = {
                    'student_id': student_id,
                    'student_name': student_name,
                    'course_id': course_id,
                    'skill': skill,
                    'score': final_score,
                    'completed': completed,
                    'attempts': attempts,
                    'scores': scores,
                    'mastery_level': calculate_mastery_level(completed, attempts, final_score),
                    'created_at': activity_date,
                    'updated_at': activity_date
                }
                
                await progress_collection.insert_one(progress_doc)
                progress_records_created += 1
        
        print(f"   ✅ Created progress data for {len(selected_students)} students in {course['name']}")
    
    print(f"✅ Created {progress_records_created} progress records")

def calculate_mastery_level(completed: bool, attempts: int, score: float) -> str:
    """Calculate mastery level based on performance."""
    if not completed:
        return 'struggling' if attempts > 3 else 'beginner'
    elif score >= 90:
        return 'mastered'
    elif score >= 80:
        return 'developing'
    else:
        return 'beginner'

async def create_analytics_summary(analytics_collection, progress_collection):
    """Create analytics summary data."""
    print("📈 Generating analytics summary...")
    
    for course in DEMO_COURSES:
        course_id = course["id"]
        
        # Check if analytics already exist
        existing_analytics = await analytics_collection.find_one({'course_id': course_id})
        if existing_analytics:
            continue
        
        # Calculate course analytics
        progress_data = await progress_collection.find({'course_id': course_id}).to_list(length=None)
        
        if not progress_data:
            continue
        
        total_students = len(set([p['student_id'] for p in progress_data]))
        total_skills = len(COURSE_SKILLS[course_id])
        completed_count = len([p for p in progress_data if p['completed']])
        avg_score = sum([p['score'] for p in progress_data]) / len(progress_data)
        
        # Risk assessment
        high_risk = medium_risk = low_risk = 0
        student_performance = {}
        
        for record in progress_data:
            student_id = record['student_id']
            if student_id not in student_performance:
                student_performance[student_id] = []
            student_performance[student_id].append(record['score'])
        
        for student_id, scores in student_performance.items():
            avg_student_score = sum(scores) / len(scores)
            completion_rate = len([s for s in scores if s >= 70]) / len(scores)
            
            if avg_student_score < 60 or completion_rate < 0.4:
                high_risk += 1
            elif avg_student_score < 75 or completion_rate < 0.7:
                medium_risk += 1
            else:
                low_risk += 1
        
        analytics_doc = {
            'course_id': course_id,
            'course_name': course['name'],
            'total_students': total_students,
            'total_skills': total_skills,
            'completion_rate': round(completed_count / len(progress_data) * 100, 1),
            'average_score': round(avg_score, 1),
            'risk_distribution': {
                'high': high_risk,
                'medium': medium_risk,
                'low': low_risk
            },
            'generated_at': datetime.utcnow(),
            'last_updated': datetime.utcnow()
        }
        
        await analytics_collection.insert_one(analytics_doc)
        print(f"   ✅ Generated analytics for {course['name']}")
    
    print("✅ Analytics summary generated")

async def print_demo_summary():
    """Print summary of created demo data."""
    print("\n" + "="*60)
    print("🎯 ACHIEVEUP DEMO DATA GENERATION COMPLETE!")
    print("="*60)
    print()
    print("📊 DEMO DATA SUMMARY:")
    print(f"   👨‍🏫 Instructor Account: 1")
    print(f"   📚 Courses: {len(DEMO_COURSES)}")
    print(f"   📋 Skills per Course: {sum(len(skills) for skills in COURSE_SKILLS.values())}")
    print(f"   ❓ Questions: {sum(len(questions) for questions in DEMO_QUESTIONS.values())}")
    print(f"   👥 Students per Course: 22-30")
    print(f"   📈 Progress Records: Thousands")
    print()
    print("🔐 DEMO INSTRUCTOR LOGIN:")
    print(f"   📧 Email: {DEMO_INSTRUCTOR_EMAIL}")
    print(f"   🔑 Password: {DEMO_INSTRUCTOR_PASSWORD}")
    print(f"   🎯 Role: Instructor")
    print()
    print("🚀 DEMO FEATURES:")
    print("   ✅ AI Skill Suggestions (with fallback)")
    print("   ✅ Question Analysis & Complexity Assessment")
    print("   ✅ Student Progress Tracking")
    print("   ✅ Risk Assessment Analytics")
    print("   ✅ Interactive Dashboards")
    print("   ✅ Course & Student Management")
    print()
    print("🌐 ACCESS DEMO:")
    print("   Frontend: https://achieveup.netlify.app")
    print("   Backend: https://gen-ai-prime-3ddeabb35bd7.herokuapp.com")
    print()
    print("📖 DEMO COURSES:")
    for course in DEMO_COURSES:
        print(f"   📚 {course['name']} ({course['code']})")
        print(f"      Students: {course['enrollment']}, Skills: {len(COURSE_SKILLS[course['id']])}")
    print()
    print("🎉 Ready to demonstrate full AchieveUp functionality!")
    print("="*60)

async def main():
    """Main demo data generation function."""
    print("🎯 AchieveUp Demo Data Generator")
    print("=" * 50)
    print()
    
    try:
        # Setup database
        db, users_col, matrices_col, questions_col, progress_col, analytics_col = await setup_database()
        
        # Create demo data
        instructor_id = await create_demo_instructor(users_col)
        await create_skill_matrices(matrices_col)
        await create_question_assignments(questions_col)
        await create_demo_students_and_progress(progress_col)
        await create_analytics_summary(analytics_col, progress_col)
        
        # Print summary
        await print_demo_summary()
        
    except Exception as e:
        print(f"❌ Error generating demo data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 