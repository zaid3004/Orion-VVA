"""
Aurora Voice Assistant - Database Models
SQLAlchemy models for user authentication and chat management
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=True)
    
    # Profile settings
    voice_preference = db.Column(db.String(100), default='default')
    theme_preference = db.Column(db.String(50), default='aurora')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    chat_sessions = db.relationship('ChatSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_chat_sessions(self, limit=20):
        """Get user's chat sessions ordered by last activity"""
        return self.chat_sessions.order_by(ChatSession.updated_at.desc()).limit(limit).all()
    
    def __repr__(self):
        return f'<User {self.username}>'

class ChatSession(db.Model):
    """Chat session model to organize conversations by topic/context"""
    __tablename__ = 'chat_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Session metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    messages = db.relationship('ChatMessage', backref='session', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_messages(self, limit=100):
        """Get session messages ordered by timestamp"""
        return self.messages.order_by(ChatMessage.timestamp.asc()).limit(limit).all()
    
    def get_last_message(self):
        """Get the most recent message in this session"""
        return self.messages.order_by(ChatMessage.timestamp.desc()).first()
    
    def message_count(self):
        """Get total message count for this session"""
        return self.messages.count()
    
    def __repr__(self):
        return f'<ChatSession {self.title}>'

class ChatMessage(db.Model):
    """Individual chat message model"""
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), db.ForeignKey('chat_sessions.id'), nullable=False)
    
    # Message content
    sender = db.Column(db.String(20), nullable=False)  # 'user' or 'aurora'
    message_type = db.Column(db.String(20), default='text')  # 'text', 'command', 'system'
    content = db.Column(db.Text, nullable=False)
    
    # Message metadata
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    intent = db.Column(db.String(50), nullable=True)  # recognized intent
    confidence = db.Column(db.Float, nullable=True)  # recognition confidence
    
    # Processing info
    processing_time = db.Column(db.Float, nullable=True)  # response time in seconds
    groq_used = db.Column(db.Boolean, default=False)  # whether Groq AI was used
    
    def __repr__(self):
        return f'<ChatMessage {self.sender}: {self.content[:50]}...>'

class UserSession(db.Model):
    """User session tracking for web interface"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    
    # Session info
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True)
    
    def is_expired(self):
        """Check if session has expired"""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f'<UserSession {self.user_id}>'

# Database initialization functions
def init_db(app):
    """Initialize database with app context"""
    db.init_app(app)
    
def create_tables(app):
    """Create all database tables"""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")

def drop_tables(app):
    """Drop all database tables (use with caution!)"""
    with app.app_context():
        db.drop_all()
        print("Database tables dropped")