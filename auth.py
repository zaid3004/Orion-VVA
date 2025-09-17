"""
Aurora Voice Assistant - Authentication System
Flask-Login based authentication with session management
"""

from flask import Blueprint, request, jsonify, session, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import secrets
import re

from models import db, User, ChatSession, UserSession

auth_bp = Blueprint('auth', __name__)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access Aurora.'

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return User.query.get(user_id)

def init_auth(app):
    """Initialize authentication with app"""
    login_manager.init_app(app)

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

# Authentication routes
@auth_bp.route('/register', methods=['POST'])
def register():
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
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        
        # Create new user
        user = User(
            username=username,
            email=email,
            full_name=full_name or None
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Create default chat session
        default_session = ChatSession(
            user_id=user.id,
            title="General Chat",
            description="Your default chat session with Aurora"
        )
        db.session.add(default_session)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {e}")
        return jsonify({'success': False, 'message': 'Registration failed'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
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
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email.lower())
        ).first()
        
        if not user or not user.check_password(password):
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'success': False, 'message': 'Account is disabled'}), 401
        
        # Login user
        login_user(user, remember=remember_me)
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Create user session record
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=30 if remember_me else 1)
        
        user_session = UserSession(
            user_id=user.id,
            session_token=session_token,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            expires_at=expires_at
        )
        db.session.add(user_session)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'theme_preference': user.theme_preference,
                'voice_preference': user.voice_preference
            },
            'session_token': session_token
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Login failed'}), 500

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """User logout endpoint"""
    try:
        # Deactivate user sessions
        UserSession.query.filter_by(user_id=current_user.id, is_active=True).update({
            'is_active': False
        })
        db.session.commit()
        
        logout_user()
        
        return jsonify({'success': True, 'message': 'Logout successful'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Logout error: {e}")
        return jsonify({'success': False, 'message': 'Logout failed'}), 500

@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get user profile"""
    try:
        return jsonify({
            'success': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'full_name': current_user.full_name,
                'theme_preference': current_user.theme_preference,
                'voice_preference': current_user.voice_preference,
                'created_at': current_user.created_at.isoformat(),
                'last_login': current_user.last_login.isoformat() if current_user.last_login else None
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Profile error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get profile'}), 500

@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        # Update allowed fields
        if 'full_name' in data:
            current_user.full_name = data['full_name'].strip() if data['full_name'] else None
        
        if 'theme_preference' in data:
            allowed_themes = ['aurora', 'dark', 'light']
            if data['theme_preference'] in allowed_themes:
                current_user.theme_preference = data['theme_preference']
        
        if 'voice_preference' in data:
            current_user.voice_preference = data['voice_preference']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'full_name': current_user.full_name,
                'theme_preference': current_user.theme_preference,
                'voice_preference': current_user.voice_preference
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Profile update error: {e}")
        return jsonify({'success': False, 'message': 'Failed to update profile'}), 500

@auth_bp.route('/check-session', methods=['GET'])
def check_session():
    """Check if user is logged in"""
    try:
        if current_user.is_authenticated:
            return jsonify({
                'success': True,
                'authenticated': True,
                'user': {
                    'id': current_user.id,
                    'username': current_user.username,
                    'full_name': current_user.full_name,
                    'theme_preference': current_user.theme_preference
                }
            }), 200
        else:
            return jsonify({
                'success': True,
                'authenticated': False
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"Session check error: {e}")
        return jsonify({'success': False, 'message': 'Session check failed'}), 500