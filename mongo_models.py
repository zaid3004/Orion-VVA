#!/usr/bin/env python3
"""
Orion Voice Assistant - MongoDB Models
PyMongo-based models for user authentication and chat management
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import os
import logging

logger = logging.getLogger(__name__)

class MongoDatabase:
    """MongoDB connection and database manager"""
    
    def __init__(self, connection_string=None):
        self.connection_string = connection_string or os.environ.get('MONGODB_URI')
        self.client = None
        self.db = None
        
    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.connection_string)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client.orion_vva
            logger.info("✅ Connected to MongoDB")
            self._create_indexes()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            return False
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            # Users collection indexes
            self.db.users.create_index([("username", ASCENDING)], unique=True)
            self.db.users.create_index([("email", ASCENDING)], unique=True)
            
            # Chat sessions indexes
            self.db.chat_sessions.create_index([("user_id", ASCENDING)])
            self.db.chat_sessions.create_index([("created_at", DESCENDING)])
            
            # Chat messages indexes
            self.db.chat_messages.create_index([("session_id", ASCENDING)])
            self.db.chat_messages.create_index([("timestamp", DESCENDING)])
            
            # User sessions indexes
            self.db.user_sessions.create_index([("session_token", ASCENDING)], unique=True)
            self.db.user_sessions.create_index([("user_id", ASCENDING)])
            self.db.user_sessions.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
            
            logger.info("📊 Database indexes created")
        except Exception as e:
            logger.warning(f"⚠️  Index creation warning: {e}")
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("🔒 MongoDB connection closed")

class User:
    """User model for authentication and profile management"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.users
    
    def create_user(self, username, password, email=None, full_name=None):
        """Create a new user"""
        try:
            # Check if user already exists
            query_conditions = [{"username": username}]
            if email:
                query_conditions.append({"email": email})
            
            if self.collection.find_one({"$or": query_conditions}):
                return None
            
            user_data = {
                "_id": str(uuid.uuid4()),
                "username": username,
                "email": email.lower() if email else None,
                "password_hash": generate_password_hash(password),
                "full_name": full_name,
                "voice_preference": "default",
                "theme_preference": "aurora",
                "created_at": datetime.utcnow(),
                "last_login": datetime.utcnow(),
                "is_active": True
            }
            
            result = self.collection.insert_one(user_data)
            user_data["id"] = user_data["_id"]  # For compatibility
            
            logger.info(f"👤 User created: {username}")
            return user_data
            
        except Exception as e:
            logger.error(f"❌ Error creating user: {e}")
            return None
    
    def authenticate_user(self, username_or_email, password):
        """Authenticate user by username/email and password"""
        try:
            user = self.collection.find_one({
                "$or": [
                    {"username": username_or_email},
                    {"email": username_or_email.lower()}
                ],
                "is_active": True
            })
            
            if user and check_password_hash(user["password_hash"], password):
                # Update last login
                self.collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"last_login": datetime.utcnow()}}
                )
                user["id"] = user["_id"]  # For compatibility
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error authenticating user: {e}")
            return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            user = self.collection.find_one({"_id": user_id, "is_active": True})
            if user:
                user["id"] = user["_id"]
            return user
        except Exception as e:
            logger.error(f"❌ Error getting user: {e}")
            return None
    
    def update_user(self, user_id, update_data):
        """Update user data"""
        try:
            result = self.collection.update_one(
                {"_id": user_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Error updating user: {e}")
            return False

class ChatSession:
    """Chat session model to organize conversations"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.chat_sessions
    
    def create_session(self, user_id, title, description=None):
        """Create a new chat session"""
        try:
            session_data = {
                "_id": str(uuid.uuid4()),
                "user_id": user_id,
                "title": title,
                "description": description,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True,
                "message_count": 0
            }
            
            result = self.collection.insert_one(session_data)
            session_data["id"] = session_data["_id"]
            
            logger.info(f"💬 Chat session created: {title}")
            return session_data
            
        except Exception as e:
            logger.error(f"❌ Error creating chat session: {e}")
            return None
    
    def get_user_sessions(self, user_id, limit=20):
        """Get user's chat sessions"""
        try:
            sessions = list(self.collection.find(
                {"user_id": user_id, "is_active": True}
            ).sort("updated_at", DESCENDING).limit(limit))
            
            for session in sessions:
                session["id"] = session["_id"]
            
            return sessions
        except Exception as e:
            logger.error(f"❌ Error getting user sessions: {e}")
            return []
    
    def get_session(self, session_id, user_id=None):
        """Get a specific chat session"""
        try:
            query = {"_id": session_id, "is_active": True}
            if user_id:
                query["user_id"] = user_id
            
            session = self.collection.find_one(query)
            if session:
                session["id"] = session["_id"]
            
            return session
        except Exception as e:
            logger.error(f"❌ Error getting session: {e}")
            return None
    
    def update_session(self, session_id, update_data):
        """Update session data"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = self.collection.update_one(
                {"_id": session_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Error updating session: {e}")
            return False

class ChatMessage:
    """Individual chat message model"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.chat_messages
        self.sessions = ChatSession(db)
    
    def create_message(self, session_id, sender, content, intent=None, message_type="text", processing_time=None, groq_used=False):
        """Create a new chat message"""
        try:
            message_data = {
                "_id": str(uuid.uuid4()),
                "session_id": session_id,
                "sender": sender,  # 'user' or 'orion'
                "message_type": message_type,
                "content": content,
                "timestamp": datetime.utcnow(),
                "intent": intent,
                "processing_time": processing_time,
                "groq_used": groq_used
            }
            
            result = self.collection.insert_one(message_data)
            message_data["id"] = message_data["_id"]
            
            # Update session message count and last activity
            self.sessions.collection.update_one(
                {"_id": session_id},
                {
                    "$inc": {"message_count": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            return message_data
            
        except Exception as e:
            logger.error(f"❌ Error creating message: {e}")
            return None
    
    def get_session_messages(self, session_id, limit=100):
        """Get messages for a session"""
        try:
            messages = list(self.collection.find(
                {"session_id": session_id}
            ).sort("timestamp", ASCENDING).limit(limit))
            
            for message in messages:
                message["id"] = message["_id"]
            
            return messages
        except Exception as e:
            logger.error(f"❌ Error getting session messages: {e}")
            return []
    
    def get_recent_messages(self, user_id, limit=20):
        """Get recent messages for a user across all sessions"""
        try:
            # First get user's active sessions
            user_sessions = self.sessions.get_user_sessions(user_id)
            session_ids = [session["_id"] for session in user_sessions]
            
            if not session_ids:
                return []
            
            messages = list(self.collection.find(
                {"session_id": {"$in": session_ids}}
            ).sort("timestamp", DESCENDING).limit(limit))
            
            for message in messages:
                message["id"] = message["_id"]
            
            return messages
        except Exception as e:
            logger.error(f"❌ Error getting recent messages: {e}")
            return []

class UserSession:
    """User session tracking for web interface"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.user_sessions
    
    def create_session(self, user_id, session_token, ip_address=None, user_agent=None, expires_days=30):
        """Create a new user session"""
        try:
            session_data = {
                "_id": str(uuid.uuid4()),
                "user_id": user_id,
                "session_token": session_token,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=expires_days),
                "is_active": True
            }
            
            result = self.collection.insert_one(session_data)
            session_data["id"] = session_data["_id"]
            
            return session_data
            
        except Exception as e:
            logger.error(f"❌ Error creating user session: {e}")
            return None
    
    def get_session_by_token(self, session_token):
        """Get session by token"""
        try:
            session = self.collection.find_one({
                "session_token": session_token,
                "is_active": True,
                "expires_at": {"$gt": datetime.utcnow()}
            })
            
            if session:
                session["id"] = session["_id"]
                # Update last activity
                self.collection.update_one(
                    {"_id": session["_id"]},
                    {"$set": {"last_activity": datetime.utcnow()}}
                )
            
            return session
        except Exception as e:
            logger.error(f"❌ Error getting session by token: {e}")
            return None
    
    def invalidate_session(self, session_token):
        """Invalidate a session"""
        try:
            result = self.collection.update_one(
                {"session_token": session_token},
                {"$set": {"is_active": False}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"❌ Error invalidating session: {e}")
            return False

# Global database instance
mongo_db = MongoDatabase()

def init_mongo_db(connection_string):
    """Initialize MongoDB connection"""
    global mongo_db
    mongo_db.connection_string = connection_string
    return mongo_db.connect()

def get_mongo_models():
    """Get MongoDB model instances"""
    if mongo_db.db is None:
        raise Exception("MongoDB not connected. Call init_mongo_db first.")
    
    return {
        'users': User(mongo_db.db),
        'chat_sessions': ChatSession(mongo_db.db),
        'chat_messages': ChatMessage(mongo_db.db),
        'user_sessions': UserSession(mongo_db.db)
    }
