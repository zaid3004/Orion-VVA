#!/usr/bin/env python3
"""
Test the authentication system directly
"""
import requests
import json

def test_registration():
    """Test user registration"""
    print("🧪 Testing User Registration...")
    
    url = "http://localhost:5000/api/auth/register"
    data = {
        "username": "testcommander",
        "email": "testcommander@orion.ai", 
        "password": "SecurePass123",
        "full_name": "Test Commander"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 201
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        print("Make sure the server is running with: python web_server.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_login():
    """Test user login"""
    print("\n🧪 Testing User Login...")
    
    url = "http://localhost:5000/api/auth/login"
    data = {
        "username": "testcommander",
        "password": "SecurePass123"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_existing_user_login():
    """Test login with sample data user"""
    print("\n🧪 Testing Login with Sample Data User...")
    
    url = "http://localhost:5000/api/auth/login"
    data = {
        "username": "commander",
        "password": "hashed_password_123"  # This won't work because it's not properly hashed
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_server_running():
    """Check if the server is running"""
    try:
        response = requests.get("http://localhost:5000/api/status")
        print("✅ Server is running")
        return True
    except requests.exceptions.RequestException:
        print("❌ Server is not running. Start it with: python web_server.py")
        return False

def main():
    print("🤖 ORION AUTHENTICATION TEST")
    print("=" * 50)
    
    if not check_server_running():
        return
    
    # Test registration
    reg_success = test_registration()
    
    if reg_success:
        # Test login with newly registered user
        test_login()
    
    # Test login with existing sample data (will fail due to password hashing)
    test_existing_user_login()
    
    print("\n📝 Notes:")
    print("- The sample data users have fake password hashes")
    print("- Only properly registered users can log in")
    print("- Check browser console for frontend errors")

if __name__ == '__main__':
    main()