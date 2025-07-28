#!/usr/bin/env python3
"""
Create Demo Instructor Account
=============================

This script creates the demo instructor account in the production database.
Run this to ensure the demo account is available for frontend testing.

Usage:
    python3 create_demo_account.py
"""

import asyncio
import bcrypt
import uuid
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

# Demo account credentials
DEMO_INSTRUCTOR_EMAIL = "demo.instructor@ucf.edu"
DEMO_INSTRUCTOR_PASSWORD = "AchieveUp2024!"
DEMO_CANVAS_TOKEN = "1234567890abcdef" * 4  # 64-character demo token

async def create_demo_instructor():
    """Create the demo instructor account in the database."""
    print("🎯 Creating Demo Instructor Account")
    print("=" * 50)
    
    try:
        # Connect to database
        print("🔗 Connecting to MongoDB...")
        client = AsyncIOMotorClient(Config.DB_CONNECTION_STRING)
        db = client[Config.DATABASE]
        users_collection = db["AchieveUp_Users"]
        
        # Check if demo instructor already exists
        existing_instructor = await users_collection.find_one({'email': DEMO_INSTRUCTOR_EMAIL})
        if existing_instructor:
            print(f"✅ Demo instructor already exists: {DEMO_INSTRUCTOR_EMAIL}")
            print(f"   User ID: {existing_instructor.get('user_id', 'N/A')}")
            return existing_instructor['user_id']
        
        # Create new instructor
        print("👨‍🏫 Creating new demo instructor account...")
        
        # Hash password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(DEMO_INSTRUCTOR_PASSWORD.encode('utf-8'), salt)
        
        # Encrypt demo Canvas token
        from utils.encryption_utils import encrypt_token
        encrypted_token = encrypt_token(bytes.fromhex(Config.HEX_ENCRYPTION_KEY), DEMO_CANVAS_TOKEN)
        
        # Create instructor document
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
        
        # Insert into database
        await users_collection.insert_one(instructor_doc)
        
        print("✅ Demo instructor created successfully!")
        print(f"   📧 Email: {DEMO_INSTRUCTOR_EMAIL}")
        print(f"   🔑 Password: {DEMO_INSTRUCTOR_PASSWORD}")
        print(f"   🎯 Role: Instructor")
        print(f"   🆔 User ID: {instructor_id}")
        print()
        print("🌐 Ready to use with frontend:")
        print("   Frontend: https://achieveup.netlify.app")
        print("   Backend: https://gen-ai-prime-3ddeabb35bd7.herokuapp.com")
        
        return instructor_id
        
    except Exception as e:
        print(f"❌ Error creating demo instructor: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Main function."""
    print("🎯 AchieveUp Demo Account Creator")
    print("=" * 50)
    print()
    
    # Create demo instructor
    instructor_id = await create_demo_instructor()
    
    if instructor_id:
        print()
        print("🎉 Demo account creation complete!")
        print("=" * 50)
        print("You can now log in to the frontend using:")
        print(f"   Email: {DEMO_INSTRUCTOR_EMAIL}")
        print(f"   Password: {DEMO_INSTRUCTOR_PASSWORD}")
        print()
        print("The demo account has full instructor permissions")
        print("and will work with all AchieveUp features.")
    else:
        print("❌ Failed to create demo account. Check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main()) 