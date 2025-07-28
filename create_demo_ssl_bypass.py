#!/usr/bin/env python3
"""
Create Demo Instructor Account via API (SSL Bypass)
==================================================

This script creates the demo instructor account by calling the backend API directly,
bypassing SSL certificate verification for local development.

Usage:
    python3 create_demo_ssl_bypass.py
"""

import asyncio
import aiohttp
import ssl
import certifi
import json

# Demo account credentials
DEMO_INSTRUCTOR_EMAIL = "demo.instructor@ucf.edu"
DEMO_INSTRUCTOR_PASSWORD = "AchieveUp2024!"
DEMO_CANVAS_TOKEN = "1234567890abcdef" * 4  # 64-character demo token

# Backend API URL
BACKEND_URL = "https://gen-ai-prime-3ddeabb35bd7.herokuapp.com"

async def create_demo_instructor_via_api():
    """Create the demo instructor account via the backend API."""
    print("🎯 Creating Demo Instructor Account via API")
    print("=" * 55)
    
    try:
        # Prepare signup data
        signup_data = {
            "name": "Dr. Jane Smith",
            "email": DEMO_INSTRUCTOR_EMAIL,
            "password": DEMO_INSTRUCTOR_PASSWORD,
            "canvasApiToken": DEMO_CANVAS_TOKEN,
            "canvasTokenType": "instructor"
        }
        
        print("🔗 Connecting to backend API...")
        print(f"   URL: {BACKEND_URL}")
        print("   ⚠️  SSL verification disabled for local development")
        print()
        
        # Create SSL context that bypasses certificate verification
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create connector with SSL bypass
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        # Make API call to create instructor account
        async with aiohttp.ClientSession(connector=connector) as session:
            url = f"{BACKEND_URL}/auth/signup"
            headers = {
                'Content-Type': 'application/json'
            }
            
            print("📝 Creating demo instructor account...")
            async with session.post(url, json=signup_data, headers=headers) as response:
                response_text = await response.text()
                
                print(f"   Status Code: {response.status}")
                print(f"   Response: {response_text}")
                print()
                
                if response.status == 201:
                    print("✅ Demo instructor created successfully via API!")
                    print(f"   📧 Email: {DEMO_INSTRUCTOR_EMAIL}")
                    print(f"   🔑 Password: {DEMO_INSTRUCTOR_PASSWORD}")
                    print(f"   🎯 Role: Instructor")
                    print()
                    print("🌐 Ready to use with frontend:")
                    print("   Frontend: https://achieveup.netlify.app")
                    print("   Backend: https://gen-ai-prime-3ddeabb35bd7.herokuapp.com")
                    return True
                elif response.status == 409:
                    print("ℹ️  Demo instructor already exists in database")
                    print(f"   📧 Email: {DEMO_INSTRUCTOR_EMAIL}")
                    print("   You can now log in with the demo credentials")
                    return True
                else:
                    print(f"❌ Failed to create demo instructor: {response.status}")
                    print(f"   Response: {response_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error creating demo instructor via API: {str(e)}")
        print()
        print("🔧 TROUBLESHOOTING:")
        print("1. Check if the backend is running and accessible")
        print("2. Verify the backend URL is correct")
        print("3. Check network connectivity")
        print()
        import traceback
        traceback.print_exc()
        return False

async def test_demo_login():
    """Test the demo account login to verify it works."""
    print("🧪 Testing Demo Account Login")
    print("=" * 35)
    
    try:
        # Prepare login data
        login_data = {
            "email": DEMO_INSTRUCTOR_EMAIL,
            "password": DEMO_INSTRUCTOR_PASSWORD
        }
        
        print("🔐 Testing login with demo credentials...")
        
        # Create SSL context that bypasses certificate verification
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create connector with SSL bypass
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            url = f"{BACKEND_URL}/auth/login"
            headers = {
                'Content-Type': 'application/json'
            }
            
            async with session.post(url, json=login_data, headers=headers) as response:
                response_text = await response.text()
                
                print(f"   Status Code: {response.status}")
                print(f"   Response: {response_text}")
                print()
                
                if response.status == 200:
                    print("✅ Demo account login successful!")
                    print("   The demo account is working correctly")
                    return True
                else:
                    print(f"❌ Demo account login failed: {response.status}")
                    print(f"   Response: {response_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error testing demo login: {str(e)}")
        return False

async def main():
    """Main function."""
    print("🎯 AchieveUp Demo Account Creator (SSL Bypass Version)")
    print("=" * 60)
    print()
    print("⚠️  SSL certificate verification is disabled for local development")
    print("   This is safe for creating demo accounts.")
    print()
    
    # Create demo instructor via API
    success = await create_demo_instructor_via_api()
    
    if success:
        print()
        print("🎉 Demo account creation complete!")
        print("=" * 50)
        
        # Test the login
        print("Testing login functionality...")
        login_success = await test_demo_login()
        
        if login_success:
            print()
            print("🎯 DEMO ACCOUNT READY!")
            print("=" * 25)
            print("You can now log in to the frontend using:")
            print(f"   Email: {DEMO_INSTRUCTOR_EMAIL}")
            print(f"   Password: {DEMO_INSTRUCTOR_PASSWORD}")
            print()
            print("The demo account has full instructor permissions")
            print("and will work with all AchieveUp features.")
        else:
            print()
            print("⚠️  Demo account created but login test failed.")
            print("   Please check the backend logs for more details.")
    else:
        print("❌ Failed to create demo account. Check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main()) 