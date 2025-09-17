#!/usr/bin/env python3
"""
Fix database schema to match Flask models
"""
import sqlite3
import os
from werkzeug.security import generate_password_hash
import uuid

def backup_database():
    """Create a backup of the current database"""
    if os.path.exists('orion_vva.db'):
        import shutil
        backup_name = f'orion_vva_backup_{int(time.time())}.db'
        shutil.copy('orion_vva.db', backup_name)
        print(f"✅ Database backed up to: {backup_name}")
        return backup_name
    return None

def fix_database_schema():
    """Fix the database schema to match the Flask models"""
    print("🔧 Fixing database schema...")
    
    conn = sqlite3.connect('orion_vva.db')
    cursor = conn.cursor()
    
    try:
        # Check current schema
        cursor.execute('PRAGMA table_info(users)')
        current_columns = [col[1] for col in cursor.fetchall()]
        print(f"Current columns: {current_columns}")
        
        # Drop existing tables and recreate with correct schema
        print("🗑️  Dropping old tables...")
        cursor.execute('DROP TABLE IF EXISTS chat_messages')
        cursor.execute('DROP TABLE IF EXISTS chat_sessions') 
        cursor.execute('DROP TABLE IF EXISTS user_sessions')
        cursor.execute('DROP TABLE IF EXISTS users')
        
        # Create users table with correct schema
        print("🏗️  Creating users table with UUID...")
        cursor.execute('''
            CREATE TABLE users (
                id VARCHAR(36) PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(150),
                voice_preference VARCHAR(100) DEFAULT 'default',
                theme_preference VARCHAR(50) DEFAULT 'aurora',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Create chat_sessions table
        print("🏗️  Creating chat_sessions table...")
        cursor.execute('''
            CREATE TABLE chat_sessions (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create chat_messages table
        print("🏗️  Creating chat_messages table...")
        cursor.execute('''
            CREATE TABLE chat_messages (
                id VARCHAR(36) PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL,
                sender VARCHAR(20) NOT NULL,
                message_type VARCHAR(20) DEFAULT 'text',
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                intent VARCHAR(50),
                confidence REAL,
                processing_time REAL,
                groq_used BOOLEAN DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
            )
        ''')
        
        # Create user_sessions table
        print("🏗️  Creating user_sessions table...")
        cursor.execute('''
            CREATE TABLE user_sessions (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                session_token VARCHAR(255) UNIQUE NOT NULL,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Add a properly hashed test user
        print("👤 Adding test user with proper password hash...")
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash('testpass123')
        
        cursor.execute('''
            INSERT INTO users (id, username, email, password_hash, full_name, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (user_id, 'testuser', 'test@orion.ai', password_hash, 'Test User'))
        
        # Add default chat session for test user
        session_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO chat_sessions (id, user_id, title, description)
            VALUES (?, ?, ?, ?)
        ''', (session_id, user_id, 'General Chat', 'Default chat session'))
        
        conn.commit()
        print("✅ Database schema fixed successfully!")
        
        # Show final schema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()
        print(f"\n📊 Tables created: {[t[0] for t in tables]}")
        
        # Show test user
        cursor.execute('SELECT username, email FROM users WHERE username = "testuser"')
        test_user = cursor.fetchone()
        if test_user:
            print(f"👤 Test user created: {test_user[0]} ({test_user[1]})")
            print("   Login with: username='testuser', password='testpass123'")
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    print("🗃️  DATABASE SCHEMA FIX")
    print("=" * 50)
    
    if not os.path.exists('orion_vva.db'):
        print("❌ Database file not found!")
        return
    
    # Create backup
    backup_database()
    
    # Fix schema
    fix_database_schema()
    
    print("\n🎯 Next Steps:")
    print("1. Restart your web server: python web_server.py")
    print("2. Try logging in with: username='testuser', password='testpass123'")
    print("3. Or register a new user through the web interface")

if __name__ == '__main__':
    import time
    main()