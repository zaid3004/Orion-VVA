#!/usr/bin/env python3
"""
MongoDB Atlas Connection Test
Test script to verify MongoDB Atlas connection and basic operations
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our MongoDB models
try:
    from mongo_models import init_mongo_db, get_mongo_models
    print("✅ MongoDB models imported successfully")
except ImportError as e:
    print(f"❌ Failed to import MongoDB models: {e}")
    sys.exit(1)

def test_mongodb_connection():
    """Test MongoDB Atlas connection and basic operations"""
    
    print("🔗 Testing MongoDB Atlas Connection...")
    print("="*50)
    
    # Get MongoDB URI from environment
    mongodb_uri = os.environ.get('MONGODB_URI')
    if not mongodb_uri:
        print("❌ MONGODB_URI not found in environment variables")
        print("   Please update your .env file with the correct MongoDB connection string")
        return False
    
    # Hide sensitive parts of the URI for logging
    safe_uri = mongodb_uri.replace(mongodb_uri.split('@')[0].split('://')[1], '***:***')
    print(f"🌐 Connecting to: {safe_uri}")
    
    try:
        # Initialize MongoDB connection
        if not init_mongo_db(mongodb_uri):
            print("❌ Failed to connect to MongoDB Atlas")
            return False
        
        print("✅ Successfully connected to MongoDB Atlas!")
        
        # Get models
        models = get_mongo_models()
        if not models:
            print("❌ Failed to get MongoDB models")
            return False
        
        print("✅ MongoDB models initialized successfully")
        
        # Test basic operations
        print("\n🧪 Testing basic database operations...")
        
        # Test 1: Create a test user
        print("   1️⃣ Creating test user...")
        test_user = models['users'].create_user(
            username=f"test_user_{int(datetime.now().timestamp())}",
            password="test_password_123"
        )
        
        if test_user:
            print(f"      ✅ Test user created: {test_user['username']} (ID: {test_user['id']})")
            
            # Test 2: Verify user can be retrieved
            print("   2️⃣ Retrieving test user...")
            retrieved_user = models['users'].get_user_by_id(test_user['id'])
            if retrieved_user:
                print(f"      ✅ User retrieved successfully: {retrieved_user['username']}")
            else:
                print("      ❌ Failed to retrieve test user")
                return False
            
            # Test 3: Create a chat session
            print("   3️⃣ Creating test chat session...")
            test_session = models['chat_sessions'].create_session(
                user_id=test_user['id'],
                title="Test Session",
                description="MongoDB connection test session"
            )
            
            if test_session:
                print(f"      ✅ Chat session created: {test_session['title']} (ID: {test_session['id']})")
                
                # Test 4: Create a chat message
                print("   4️⃣ Creating test chat message...")
                test_message = models['chat_messages'].create_message(
                    session_id=test_session['id'],
                    sender='user',
                    content="Hello Orion, this is a test message!",
                    intent='test'
                )
                
                if test_message:
                    print(f"      ✅ Chat message created: {test_message['content'][:30]}...")
                else:
                    print("      ❌ Failed to create chat message")
                    return False
                
                # Test 5: Retrieve messages
                print("   5️⃣ Retrieving chat messages...")
                messages = models['chat_messages'].get_session_messages(test_session['id'])
                if messages and len(messages) > 0:
                    print(f"      ✅ Retrieved {len(messages)} message(s)")
                else:
                    print("      ❌ Failed to retrieve chat messages")
                    return False
            
            else:
                print("      ❌ Failed to create chat session")
                return False
            
            # Test 6: Clean up test data
            print("   6️⃣ Cleaning up test data...")
            # Note: In a production app, you might want to keep test data or have a cleanup method
            print("      ℹ️  Test data cleanup not implemented (test collections will remain)")
            
        else:
            print("      ❌ Failed to create test user")
            return False
        
        print("\n🎉 All MongoDB tests passed successfully!")
        print("✅ Your MongoDB Atlas connection is working perfectly!")
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🤖 Orion Voice Assistant - MongoDB Atlas Connection Test")
    print("="*60)
    
    success = test_mongodb_connection()
    
    if success:
        print("\n🚀 Ready for deployment!")
        print("   Next steps:")
        print("   1. Update .env file with your actual MongoDB connection string")
        print("   2. Set environment variables on Vercel")
        print("   3. Deploy to Vercel")
    else:
        print("\n⚠️  Please fix the MongoDB connection issues before proceeding")
        print("   Check:")
        print("   1. Your MongoDB connection string is correct")
        print("   2. Your database user has proper permissions")
        print("   3. Your network access is configured correctly")
    
    return success

if __name__ == "__main__":
    main()