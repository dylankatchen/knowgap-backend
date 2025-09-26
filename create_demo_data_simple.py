#!/usr/bin/env python3
"""
Create Demo Data (Simple Version)
================================
 *Old version of the script*
This script creates comprehensive demo data for the KnowGap system
without requiring environment variables to be set locally.
*New version must have environment variables set locally everything else the same*

Usage:
    python3 create_demo_data_simple.py
"""

import asyncio
import dotenv
import os
import uuid
import bcrypt
import random
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient


# Production database connection
PRODUCTION_DB_URI = os.getenv("PRODUCTION_DB_URI")
DATABASE_NAME = "KnowGap"

# Demo data configuration
DEMO_INSTRUCTOR_EMAIL = "demo.instructor3@ucf.edu"
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

# Sample skill matrices for each course
COURSE_SKILLS = {
    "demo_001": [
        "HTML/CSS Fundamentals",
        "JavaScript Programming", 
        "DOM Manipulation",
        "Responsive Design",
        "Form Handling",
        "AJAX/Fetch API",
        "Web Accessibility",
        "Browser Developer Tools",
        "Version Control (Git)",
        "Web Security Basics"
    ],
    "demo_002": [
        "SQL Fundamentals",
        "Database Design",
        "Data Normalization",
        "Query Optimization",
        "Stored Procedures",
        "Database Security",
        "Data Modeling",
        "ERD Creation",
        "Index Management",
        "Backup and Recovery"
    ],
    "demo_003": [
        "Network Protocols (TCP/IP)",
        "Network Security",
        "Routing & Switching",
        "Wireless Networks",
        "Network Troubleshooting",
        "Firewall Configuration",
        "Network Monitoring",
        "VPN Technologies",
        "Network Architecture",
        "Protocol Analysis"
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
    
    # For demo purposes, use simple encryption
    encrypted_token = DEMO_CANVAS_TOKEN
    
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
                    'mastery_level': 'advanced' if final_score >= 80 else 'intermediate' if final_score >= 60 else 'beginner',
                    'created_at': activity_date,
                    'updated_at': activity_date
                }
                
                await progress_collection.insert_one(progress_doc)
                progress_records_created += 1
        
        print(f"   ✅ Created progress data for {len(selected_students)} students in {course['name']}")
    
    print(f"✅ Created {progress_records_created} progress records")

async def create_question_assignments(question_skills_collection):
    """Create question-skill assignments."""
    print("🔗 Creating question-skill assignments...")
    
    # Sample questions for each course
    demo_questions = {
        "demo_001": [
            {"id": "q1_001", "text": "What does HTML stand for?", "skills": ["HTML/CSS Fundamentals"]},
            {"id": "q1_002", "text": "How do you select an element by ID in CSS?", "skills": ["HTML/CSS Fundamentals", "DOM Manipulation"]},
            {"id": "q1_003", "text": "What is the difference between let and var in JavaScript?", "skills": ["JavaScript Programming"]},
            {"id": "q1_004", "text": "Explain responsive design principles.", "skills": ["Responsive Design"]},
            {"id": "q1_005", "text": "How do you make an AJAX request?", "skills": ["AJAX/Fetch API"]}
        ],
        "demo_002": [
            {"id": "q2_001", "text": "What is a primary key?", "skills": ["Database Design"]},
            {"id": "q2_002", "text": "Explain database normalization.", "skills": ["Data Normalization"]},
            {"id": "q2_003", "text": "Write a SELECT statement with JOIN.", "skills": ["SQL Fundamentals"]},
            {"id": "q2_004", "text": "How do you optimize a slow query?", "skills": ["Query Optimization"]},
            {"id": "q2_005", "text": "What are stored procedures?", "skills": ["Stored Procedures"]}
        ],
        "demo_003": [
            {"id": "q3_001", "text": "Explain the OSI model and its seven layers.", "skills": ["Network Protocols (TCP/IP)"]},
            {"id": "q3_002", "text": "Configure a firewall rule to allow HTTP traffic.", "skills": ["Firewall Configuration", "Network Security"]},
            {"id": "q3_003", "text": "Troubleshoot a network connectivity issue.", "skills": ["Network Troubleshooting"]},
            {"id": "q3_004", "text": "Explain wireless network security protocols.", "skills": ["Wireless Networks", "Network Security"]},
            {"id": "q3_005", "text": "How do you monitor network performance?", "skills": ["Network Monitoring"]}
        ]
    }
    
    assignments_created = 0
    for course_id, questions in demo_questions.items():
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

async def main():
    """Main demo data generation function."""
    print("🎯 AchieveUp Demo Data Generator (Simple Version)")
    print("=" * 60)
    print()
    
    try:
        # Connect to database
        print("🔗 Connecting to MongoDB...")
        client = AsyncIOMotorClient(PRODUCTION_DB_URI, tlsAllowInvalidCertificates=True)
        db = client[DATABASE_NAME]
        
        # Collections
        users_collection = db["AchieveUp_Users"]
        skill_matrices_collection = db["AchieveUp_Skill_Matrices"]
        question_skills_collection = db["AchieveUp_Question_Skills"]
        progress_collection = db["AchieveUp_Progress"]
        
        print("✅ Database connection established")
        
        # Create demo data
        instructor_id = await create_demo_instructor(users_collection)
        await create_skill_matrices(skill_matrices_collection)
        await create_question_assignments(question_skills_collection)
        await create_demo_students_and_progress(progress_collection)
        
        # Print summary
        print()
        print("🎉 Demo data generation complete!")
        print("=" * 50)
        print("✅ Demo instructor account created")
        print("✅ Skill matrices created for all courses")
        print("✅ Question-skill assignments created")
        print("✅ Student progress data generated")
        print()
        print("You can now log in to the frontend using:")
        print(f"   Email: {DEMO_INSTRUCTOR_EMAIL}")
        print(f"   Password: {DEMO_INSTRUCTOR_PASSWORD}")
        print()
        print("The demo data includes:")
        print(f"   📚 {len(DEMO_COURSES)} courses with skill matrices")
        print(f"   👥 {sum(course['enrollment'] for course in DEMO_COURSES)} total students")
        print(f"   📊 Progress data for all students and skills")
        print(f"   🔗 Question-skill assignments for quizzes")
        
    except Exception as e:
        print(f"❌ Error generating demo data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 