#!/usr/bin/env python3
"""
Test script to verify the production code (the 3 files you committed) works.
This tests the actual functions and API endpoint you're using in production.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_production_function():
    """Test the fetch_video_transcript function from youtube_utils.py"""
    print("=" * 60)
    print("TEST 1: Production Function (youtube_utils.py)")
    print("=" * 60)
    
    # Import the actual production function
    from utils.youtube_utils import fetch_video_transcript
    
    video_url = "https://www.youtube.com/watch?v=0QzopZ78w9M"
    print(f"\nTesting: {video_url}")
    print("-" * 60)
    
    result = await fetch_video_transcript(video_url)
    
    if result.get('success'):
        print("✅ SUCCESS: Production function works!")
        print(f"   Video ID: {result.get('video_id')}")
        print(f"   Language: {result.get('language')}")
        print(f"   Segments: {len(result.get('transcript', []))}")
        print(f"   First 200 chars: {result.get('transcript_text', '')[:200]}...")
        return True
    else:
        print(f"❌ FAILED: {result.get('error')}")
        return False


async def test_api_endpoint():
    """Test the /get-video-transcript API endpoint"""
    print("\n" + "=" * 60)
    print("TEST 2: API Endpoint (video_routes.py)")
    print("=" * 60)
    
    import aiohttp
    
    backend_url = "http://127.0.0.1:5001"
    video_url = "https://www.youtube.com/watch?v=0QzopZ78w9M"
    
    print(f"\nTesting endpoint: {backend_url}/get-video-transcript")
    print(f"Video URL: {video_url}")
    print("-" * 60)
    print("⚠️  Make sure backend server is running: python app.py")
    print("-" * 60)
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "video_url": video_url,
                "languages": ["en"]
            }
            
            async with session.post(
                f"{backend_url}/get-video-transcript",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Origin": "http://127.0.0.1:5001"  # Required for CORS
                }
            ) as response:
                status = response.status
                data = await response.json()
                
                if status == 200 and data.get('success'):
                    print("✅ SUCCESS: API endpoint works!")
                    print(f"   Status: {status}")
                    print(f"   Video ID: {data.get('video_id')}")
                    print(f"   Language: {data.get('language')}")
                    print(f"   Segments: {len(data.get('transcript', []))}")
                    print(f"   First 200 chars: {data.get('transcript_text', '')[:200]}...")
                    return True
                else:
                    print(f"❌ FAILED: Status {status}")
                    print(f"   Error: {data.get('error', 'Unknown error')}")
                    return False
                    
    except aiohttp.ClientConnectorError:
        print(f"❌ CONNECTION ERROR: Could not connect to {backend_url}")
        print("   Start the backend server first:")
        print("   cd knowgap-backend")
        print("   source venv/bin/activate")
        print("   python app.py")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all production tests"""
    print("\n" + "=" * 60)
    print("Production Code Test - The 3 Files You Committed")
    print("=" * 60)
    print("\nThis tests:")
    print("  1. utils/youtube_utils.py - fetch_video_transcript() function")
    print("  2. routes/video_routes.py - /get-video-transcript endpoint")
    print("\n" + "=" * 60)
    
    results = []
    
    # Test 1: Production function (doesn't need server)
    results.append(await test_production_function())
    
    # Test 2: API endpoint (needs server running)
    print("\n" + "⚠️  " * 20)
    print("For the next test, make sure your backend server is running!")
    print("If not, start it in another terminal:")
    print("  cd knowgap-backend")
    print("  source venv/bin/activate")
    print("  python app.py")
    print("⚠️  " * 20)
    print("\nPress Enter to test API endpoint, or Ctrl+C to skip...")
    
    try:
        input()
        results.append(await test_api_endpoint())
    except KeyboardInterrupt:
        print("\nSkipping API endpoint test.")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All production code tests passed!")
        print("\nYour committed files are working correctly!")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

