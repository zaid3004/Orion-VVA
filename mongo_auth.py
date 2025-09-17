#!/usr/bin/env python3
"""
Orion Voice Assistant - MongoDB Authentication System
MongoDB-based authentication with session management
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import secrets
import re
import logging

logger = logging.getLogger(__name__)

# MongoDB models will be injected
mongo_models = None

def init_mongo_auth(models):
    """Initialize MongoDB authentication with models"""
    global mongo_models
    mongo_models = models
    logger.info("🔐 MongoDB authentication initialized")

# Utility functions
def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

def validate_username(username):
    """Validate username format"""
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    if len(username) > 20:
        return False, "Username must be less than 20 characters"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    return True, "Username is valid"

# Authentication endpoints
def register_user():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        # Extract and validate fields
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        
        # Validation
        if not username or not email or not password:
            return jsonify({'success': False, 'message': 'Username, email, and password are required'}), 400
        
        # Validate username
        valid, message = validate_username(username)
        if not valid:
            return jsonify({'success': False, 'message': message}), 400
        
        # Validate email
        if not validate_email(email):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
        # Validate password
        valid, message = validate_password(password)
        if not valid:
            return jsonify({'success': False, 'message': message}), 400
        
        # Create new user
        user_data, error = mongo_models['users'].create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name or None
        )
        
        if error:
            return jsonify({'success': False, 'message': error}), 400
        
        # Create default chat session
        default_session = mongo_models['chat_sessions'].create_session(
            user_id=user_data['id'],
            title="General Chat",
            description="Your default chat session with Orion"
        )
        
        logger.info(f"👤 User registered: {username}")
        
        return jsonify({
            'success': True,
            'message': 'Registration successful! Welcome to Orion, Commander!',
            'user': {
                'id': user_data['id'],
                'username': user_data['username'],
                'email': user_data['email'],
                'full_name': user_data['full_name']
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'success': False, 'message': 'Registration failed'}), 500

def login_user():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        username_or_email = data.get('username', '').strip()
        password = data.get('password', '')
        remember_me = data.get('remember_me', False)
        
        if not username_or_email or not password:
            return jsonify({'success': False, 'message': 'Username/email and password are required'}), 400
        
        # Authenticate user
        user = mongo_models['users'].authenticate_user(username_or_email, password)
        
        if not user:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        if not user.get('is_active', True):
            return jsonify({'success': False, 'message': 'Account is disabled'}), 401
        
        # Create user session
        session_token = secrets.token_urlsafe(32)
        expires_days = 30 if remember_me else 7
        
        user_session = mongo_models['user_sessions'].create_session(
            user_id=user['id'],
            session_token=session_token,
            ip_address=request.environ.get('REMOTE_ADDR'),
            user_agent=request.headers.get('User-Agent'),
            expires_days=expires_days
        )
        
        logger.info(f"🔑 User logged in: {user['username']}")
        
        return jsonify({
            'success': True,
            'message': 'Welcome back, Commander! Login successful.',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'full_name': user['full_name'],
                'theme_preference': user.get('theme_preference', 'aurora'),
                'voice_preference': user.get('voice_preference', 'default')
            },
            'session_token': session_token
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Login failed'}), 500

def logout_user():
    """User logout endpoint"""
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header.split(' ')[1]
            mongo_models['user_sessions'].invalidate_session(session_token)
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully, Commander. Until next time!'
        }), 200
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'success': False, 'message': 'Logout failed'}), 500

def get_current_user():
    """Get current user from session token"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        session_token = auth_header.split(' ')[1]
        session = mongo_models['user_sessions'].get_session_by_token(session_token)
        
        if not session:
            return None
        
        user = mongo_models['users'].get_user_by_id(session['user_id'])
        return user
        
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return None

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        request.current_user = user
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

# Create Blueprint for authentication routes
def create_auth_blueprint():
    """Create authentication blueprint"""
    auth_bp = Blueprint('auth', __name__)
    
    @auth_bp.route('/register', methods=['POST'])
    def register():
        return register_user()
    
    @auth_bp.route('/login', methods=['POST'])
    def login():
        return login_user()
    
    @auth_bp.route('/logout', methods=['POST'])
    def logout():
        return logout_user()
    
    @auth_bp.route('/me', methods=['GET'])
    @require_auth
    def get_me():
        """Get current user info"""
        user = request.current_user
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'full_name': user['full_name'],
                'theme_preference': user.get('theme_preference', 'aurora'),
                'voice_preference': user.get('voice_preference', 'default'),
                'created_at': user['created_at'].isoformat() if user.get('created_at') else None,
                'last_login': user['last_login'].isoformat() if user.get('last_login') else None
            }
        })
    
    @auth_bp.route('/sessions', methods=['GET'])
    @require_auth
    def get_user_sessions():
        """Get user's chat sessions"""
        user = request.current_user
        sessions = mongo_models['chat_sessions'].get_user_sessions(user['id'])
        
        return jsonify({
            'success': True,
            'sessions': [{
                'id': session['id'],
                'title': session['title'],
                'description': session.get('description'),
                'message_count': session.get('message_count', 0),
                'created_at': session['created_at'].isoformat(),
                'updated_at': session['updated_at'].isoformat()
            } for session in sessions]
        })
    
    return auth_bp