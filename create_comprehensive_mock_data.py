#!/usr/bin/env python3
"""
Create Comprehensive Mock Data for AchieveUp
===========================================

This script creates the complete data chain needed for the Student Progress feature:
1. Skill assignments to quiz questions
2. Student quiz attempts/responses  
3. Calculated skill progress data

Usage:
    python3 create_comprehensive_mock_data.py
"""

import asyncio
import dotenv
import os
import uuid
import random
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

dotenv.load_dotenv()

# Production database connection
PRODUCTION_DB_URI = os.getenv("PRODUCTION_DB_URI")
DATABASE_NAME = "KnowGap"

# Demo courses and their skills
DEMO_COURSES = {
    "demo_001": {
        "name": "Web Development Fundamentals",
        "code": "COP3530",
        "skills": ["HTML/CSS Fundamentals", "JavaScript Programming", "DOM Manipulation", "Responsive Design", "Web APIs"]
    },
    "demo_002": {
        "name": "Database Management Systems", 
        "code": "CIS4301",
        "skills": ["SQL Fundamentals", "Database Design", "Data Normalization", "Query Optimization", "Stored Procedures"]
    },
    "demo_003": {
        "name": "Computer Networks",
        "code": "CNT4007", 
        "skills": ["Network Protocols (TCP/IP)", "Network Security", "Routing & Switching", "Wireless Networks", "Network Troubleshooting"]
    }
}

# Mock quiz questions for each course
COURSE_QUIZ_QUESTIONS = {
    "demo_001": [
        {
            "quiz_id": "quiz_demo_001_001",
            "quiz_name": "Web Development Fundamentals Quiz",
            "questions": [
                {"id": "q001_001", "text": "What does HTML stand for?", "max_points": 20, "skills": ["HTML/CSS Fundamentals"]},
                {"id": "q001_002", "text": "How do you select an element by ID in CSS?", "max_points": 20, "skills": ["HTML/CSS Fundamentals", "DOM Manipulation"]},
                {"id": "q001_003", "text": "What is the difference between let and var in JavaScript?", "max_points": 20, "skills": ["JavaScript Programming"]},
                {"id": "q001_004", "text": "How do you add an event listener to a button?", "max_points": 20, "skills": ["JavaScript Programming", "DOM Manipulation"]},
                {"id": "q001_005", "text": "What is the fetch() API used for?", "max_points": 20, "skills": ["Web APIs", "JavaScript Programming"]}
            ]
        },
        {
            "quiz_id": "quiz_demo_001_002", 
            "quiz_name": "Advanced Web Development Quiz",
            "questions": [
                {"id": "q002_001", "text": "Explain CSS Grid vs Flexbox", "max_points": 25, "skills": ["HTML/CSS Fundamentals", "Responsive Design"]},
                {"id": "q002_002", "text": "How do you handle promises in JavaScript?", "max_points": 25, "skills": ["JavaScript Programming", "Web APIs"]},
                {"id": "q002_003", "text": "What are media queries used for?", "max_points": 25, "skills": ["Responsive Design", "HTML/CSS Fundamentals"]},
                {"id": "q002_004", "text": "How do you manipulate DOM elements?", "max_points": 25, "skills": ["DOM Manipulation", "JavaScript Programming"]}
            ]
        }
    ],
    "demo_002": [
        {
            "quiz_id": "quiz_demo_002_001",
            "quiz_name": "Database Fundamentals Quiz", 
            "questions": [
                {"id": "q003_001", "text": "What is a primary key?", "max_points": 20, "skills": ["Database Design"]},
                {"id": "q003_002", "text": "Write a SELECT statement with JOIN", "max_points": 20, "skills": ["SQL Fundamentals"]},
                {"id": "q003_003", "text": "Explain database normalization", "max_points": 20, "skills": ["Data Normalization"]},
                {"id": "q003_004", "text": "How do you optimize a slow query?", "max_points": 20, "skills": ["Query Optimization"]},
                {"id": "q003_005", "text": "What are stored procedures?", "max_points": 20, "skills": ["Stored Procedures"]}
            ]
        }
    ],
    "demo_003": [
        {
            "quiz_id": "quiz_demo_003_001",
            "quiz_name": "Network Fundamentals Quiz",
            "questions": [
                {"id": "q004_001", "text": "Explain the OSI model", "max_points": 20, "skills": ["Network Protocols (TCP/IP)"]},
                {"id": "q004_002", "text": "Configure a firewall rule", "max_points": 20, "skills": ["Network Security"]},
                {"id": "q004_003", "text": "Troubleshoot network connectivity", "max_points": 20, "skills": ["Network Troubleshooting"]},
                {"id": "q004_004", "text": "Explain wireless security protocols", "max_points": 20, "skills": ["Wireless Networks", "Network Security"]},
                {"id": "q004_005", "text": "Configure routing tables", "max_points": 20, "skills": ["Routing & Switching"]}
            ]
        }
    ]
}

# Student names for generating realistic data
STUDENT_NAMES = [
    "Emily Rodriguez", "Michael Chen", "Sarah Johnson", "David Kim", "Jessica Martinez",
    "Ryan Thompson", "Ashley Brown", "Kevin Wang", "Amanda Davis", "Tyler Jackson",
    "Melissa Garcia", "Brandon Lee", "Rachel Wilson", "Jordan Smith", "Stephanie Liu",
    "Austin Miller", "Nicole Anderson", "Justin Park", "Samantha Taylor", "Alex Johnson",
    "Lauren White", "Connor Davis", "Megan Lee", "Ethan Brown", "Olivia Martinez"
]

async def create_skill_matrices(skill_matrices_collection):
    """Create skill matrices for each demo course."""
    print("🔗 Creating skill matrices for courses...")
    
    matrices_created = 0
    
    for course_id, course_info in DEMO_COURSES.items():
        # Check if skill matrix already exists
        existing_matrix = await skill_matrices_collection.find_one({'course_id': course_id})
        if existing_matrix:
            print(f"   ✅ Skill matrix for {course_id} already exists")
            continue
        
        skill_matrix_doc = {
            'course_id': course_id,
            'course_name': course_info['name'],
            'course_code': course_info['code'],
            'skills': course_info['skills'],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        await skill_matrices_collection.insert_one(skill_matrix_doc)
        matrices_created += 1
        
        print(f"   🎯 Created skill matrix for {course_id}: {len(course_info['skills'])} skills")
    
    print(f"✅ Created {matrices_created} skill matrices")

async def create_skill_assignments(skill_assignments_collection):
    """Create skill assignments for quiz questions."""
    print("🔗 Creating skill assignments for quiz questions...")
    
    assignments_created = 0
    
    for course_id, course_data in COURSE_QUIZ_QUESTIONS.items():
        for quiz_data in course_data:
            quiz_id = quiz_data["quiz_id"]
            
            for question in quiz_data["questions"]:
                question_id = question["id"]
                
                # Check if assignment already exists
                existing = await skill_assignments_collection.find_one({'question_id': question_id})
                if existing:
                    continue
                
                assignment_doc = {
                    'course_id': course_id,
                    'quiz_id': quiz_id,
                    'question_id': question_id,
                    'skills': question["skills"],
                    'ai_generated': True,
                    'human_reviewed': False,
                    'assigned_by_instructor': True,
                    'instructor_id': 'demo_instructor',
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                await skill_assignments_collection.insert_one(assignment_doc)
                assignments_created += 1
                
                print(f"   ✅ Assigned skills {question['skills']} to question {question_id}")
    
    print(f"✅ Created {assignments_created} skill assignments")

async def create_student_quiz_attempts(quiz_attempts_collection):
    """Create realistic student quiz attempts with question-level responses."""
    print("📝 Creating student quiz attempts...")
    
    attempts_created = 0
    
    for course_id, course_data in COURSE_QUIZ_QUESTIONS.items():
        # Get students for this course (first 10 for demo)
        course_students = []
        for i in range(min(10, len(STUDENT_NAMES))):
            student_name = STUDENT_NAMES[i]
            student_id = f"student_{course_id}_{i+1:03d}"
            course_students.append({"id": student_id, "name": student_name})
        
        for quiz_data in course_data:
            quiz_id = quiz_data["quiz_id"]
            quiz_name = quiz_data["quiz_name"]
            questions = quiz_data["questions"]
            
            for student in course_students:
                student_id = student["id"]
                student_name = student["name"]
                
                # Check if attempt already exists
                existing = await quiz_attempts_collection.find_one({
                    'student_id': student_id,
                    'quiz_id': quiz_id
                })
                if existing:
                    continue
                
                # Generate realistic performance (some students perform better than others)
                base_performance = random.uniform(0.4, 0.95)  # Student ability
                
                # Generate question responses
                question_responses = {}
                total_score = 0
                max_score = 0
                
                for question in questions:
                    q_id = question["id"]
                    max_points = question["max_points"]
                    max_score += max_points
                    
                    # Determine if correct (based on student ability + some randomness)
                    success_probability = base_performance + random.uniform(-0.2, 0.2)
                    success_probability = max(0.1, min(0.95, success_probability))
                    
                    is_correct = random.random() < success_probability
                    
                    if is_correct:
                        # Correct answer - give full or nearly full points
                        points = max_points if random.random() > 0.1 else max_points * random.uniform(0.8, 0.95)
                        points = round(points)
                    else:
                        # Incorrect answer - give partial credit sometimes
                        if random.random() < 0.3:  # 30% chance of partial credit
                            points = round(max_points * random.uniform(0.1, 0.4))
                        else:
                            points = 0
                    
                    total_score += points
                    
                    question_responses[q_id] = {
                        "correct": is_correct,
                        "points": points,
                        "max_points": max_points
                    }
                
                # Random submission date in the last 30 days
                days_ago = random.randint(1, 30)
                submission_date = datetime.utcnow() - timedelta(days=days_ago)
                
                attempt_doc = {
                    'student_id': student_id,
                    'student_name': student_name,
                    'course_id': course_id,
                    'quiz_id': quiz_id,
                    'quiz_name': quiz_name,
                    'submission_date': submission_date,
                    'total_score': total_score,
                    'max_score': max_score,
                    'percentage': round((total_score / max_score) * 100, 1) if max_score > 0 else 0,
                    'question_responses': question_responses,
                    'created_at': submission_date,
                    'updated_at': submission_date
                }
                
                await quiz_attempts_collection.insert_one(attempt_doc)
                attempts_created += 1
                
                print(f"   📝 Created quiz attempt for {student_name} on {quiz_name} (Score: {total_score}/{max_score})")
    
    print(f"✅ Created {attempts_created} quiz attempts")

async def calculate_and_store_skill_progress(skill_progress_collection, quiz_attempts_collection, skill_assignments_collection):
    """Calculate skill progress from quiz attempts and store results."""
    print("📊 Calculating and storing skill progress...")
    
    progress_records_created = 0
    
    for course_id in DEMO_COURSES.keys():
        course_skills = DEMO_COURSES[course_id]["skills"]
        
        # Get all quiz attempts for this course
        quiz_attempts = await quiz_attempts_collection.find({'course_id': course_id}).to_list(length=None)
        
        # Get skill assignments for this course
        skill_assignments = await skill_assignments_collection.find({'course_id': course_id}).to_list(length=None)
        
        # Create mapping of question_id to skills
        question_to_skills = {}
        for assignment in skill_assignments:
            question_to_skills[assignment['question_id']] = assignment['skills']
        
        # Group attempts by student
        students_attempts = {}
        for attempt in quiz_attempts:
            student_id = attempt['student_id']
            if student_id not in students_attempts:
                students_attempts[student_id] = {
                    'student_name': attempt['student_name'],
                    'attempts': []
                }
            students_attempts[student_id]['attempts'].append(attempt)
        
        # Calculate skill scores for each student
        for student_id, student_data in students_attempts.items():
            student_name = student_data['student_name']
            
            # Initialize skill tracking
            skill_stats = {}
            for skill in course_skills:
                skill_stats[skill] = {
                    'total_points': 0,
                    'max_points': 0,
                    'questions_attempted': 0,
                    'questions_correct': 0
                }
            
            # Process all quiz attempts for this student
            for attempt in student_data['attempts']:
                for question_id, response in attempt['question_responses'].items():
                    if question_id in question_to_skills:
                        assigned_skills = question_to_skills[question_id]
                        
                        for skill in assigned_skills:
                            if skill in skill_stats:
                                skill_stats[skill]['total_points'] += response['points']
                                skill_stats[skill]['max_points'] += response['max_points']
                                skill_stats[skill]['questions_attempted'] += 1
                                if response['correct']:
                                    skill_stats[skill]['questions_correct'] += 1
            
            # Calculate skill scores and store progress records
            for skill, stats in skill_stats.items():
                if stats['max_points'] > 0:
                    score_percentage = (stats['total_points'] / stats['max_points']) * 100
                    score_percentage = round(score_percentage, 1)
                    
                    # Determine skill level
                    if score_percentage >= 81:
                        level = 'advanced'
                    elif score_percentage >= 61:
                        level = 'intermediate'
                    else:
                        level = 'beginner'
                    
                    # Check if progress record already exists
                    existing = await skill_progress_collection.find_one({
                        'student_id': student_id,
                        'course_id': course_id,
                        'skill': skill
                    })
                    
                    if existing:
                        # Update existing record
                        await skill_progress_collection.update_one(
                            {'_id': existing['_id']},
                            {'$set': {
                                'score': score_percentage,
                                'level': level,
                                'questions_attempted': stats['questions_attempted'],
                                'questions_correct': stats['questions_correct'],
                                'total_points': stats['total_points'],
                                'max_points': stats['max_points'],
                                'updated_at': datetime.utcnow()
                            }}
                        )
                    else:
                        # Create new progress record
                        progress_doc = {
                            'student_id': student_id,
                            'student_name': student_name,
                            'course_id': course_id,
                            'skill': skill,
                            'score': score_percentage,
                            'level': level,
                            'questions_attempted': stats['questions_attempted'],
                            'questions_correct': stats['questions_correct'],
                            'total_points': stats['total_points'],
                            'max_points': stats['max_points'],
                            'completed': score_percentage >= 70,
                            'created_at': datetime.utcnow(),
                            'updated_at': datetime.utcnow()
                        }
                        
                        await skill_progress_collection.insert_one(progress_doc)
                        progress_records_created += 1
                
                print(f"   📊 Calculated {skill} progress for {student_name}: {score_percentage:.1f}% ({level})")
    
    print(f"✅ Created/updated {progress_records_created} skill progress records")

async def main():
    """Main function to create comprehensive mock data."""
    print("🎯 AchieveUp Comprehensive Mock Data Generator")
    print("=" * 60)
    print()
    
    try:
        # Connect to database
        print("🔗 Connecting to MongoDB...")
        client = AsyncIOMotorClient(PRODUCTION_DB_URI, tlsAllowInvalidCertificates=True)
        db = client[DATABASE_NAME]
        
        # Collections
        skill_matrices_collection = db["AchieveUp_Skill_Matrices"]
        skill_assignments_collection = db["AchieveUp_Question_Skills"]
        quiz_attempts_collection = db["AchieveUp_Quiz_Attempts"]
        skill_progress_collection = db["AchieveUp_Progress"]
        
        print("✅ Database connection established")
        print()
        
        # Create comprehensive mock data
        await create_skill_matrices(skill_matrices_collection)
        print()
        
        await create_skill_assignments(skill_assignments_collection)
        print()
        
        await create_student_quiz_attempts(quiz_attempts_collection)
        print()
        
        await calculate_and_store_skill_progress(skill_progress_collection, quiz_attempts_collection, skill_assignments_collection)
        print()
        
        # Print summary
        print("🎉 Comprehensive mock data generation complete!")
        print("=" * 60)
        print("✅ Skill matrices created (course → skills mapping)")
        print("✅ Skill assignments created (questions → skills mapping)")
        print("✅ Student quiz attempts generated with realistic responses")
        print("✅ Skill progress calculated and stored")
        print()
        print("The Student Progress feature should now work with:")
        print("   📊 Student analytics with actual progress data")
        print("   📈 Skill distribution charts")
        print("   🎯 Individual skill breakdowns")
        print("   📋 Risk level assessments")
        print()
        print("Frontend can now access:")
        print("   🔗 /achieveup/instructor/courses/{courseId}/student-analytics")
        print("   📊 Real student progress data")
        print("   📈 Meaningful skill statistics")
        
    except Exception as e:
        print(f"❌ Error generating comprehensive mock data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 