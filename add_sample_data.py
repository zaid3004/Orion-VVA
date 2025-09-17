#!/usr/bin/env python3
"""
Add sample data to Orion database for demonstration
"""
import sqlite3
import hashlib
from datetime import datetime, timedelta

def add_sample_data():
    conn = sqlite3.connect('orion_vva.db')
    cursor = conn.cursor()
    
    print("🔧 Adding sample data to Orion database...")
    
    try:
        # Add sample users
        sample_users = [
            ('commander', 'commander@orion.ai', 'Commander Zaid', 'hashed_password_123'),
            ('testuser', 'test@example.com', 'Test User', 'hashed_password_456'),
        ]
        
        for username, email, full_name, password_hash in sample_users:
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, email, full_name, password_hash, is_active)
                VALUES (?, ?, ?, ?, 1)
            ''', (username, email, full_name, password_hash))
        
        # Add sample chat sessions
        cursor.execute('''
            INSERT OR IGNORE INTO chat_sessions (user_id, title, created_at, updated_at)
            VALUES (1, 'First Conversation with Orion', datetime('now'), datetime('now'))
        ''')
        
        cursor.execute('''
            INSERT OR IGNORE INTO chat_sessions (user_id, title, created_at, updated_at)  
            VALUES (1, 'Questions about Weather', datetime('now', '-1 day'), datetime('now', '-1 day'))
        ''')
        
        # Add sample chat messages
        sample_messages = [
            (1, 'Hello Orion', 'Greetings, Commander! I am Orion, your strategic voice assistant. How can I assist you today?', 'greeting'),
            (1, 'What time is it?', 'The current time is 3:45 PM, Commander.', 'time'),
            (1, 'Set a timer for 5 minutes', 'Timer set for 5 minutes, Commander. I will alert you when time is up.', 'timer'),
            (2, 'What is the weather like?', 'I need your location to provide weather information, Commander. Please specify a city.', 'weather'),
            (2, 'Weather in Dubai', 'The weather in Dubai is sunny with temperature 32°C and humidity 65%, Commander.', 'weather'),
        ]
        
        for session_id, user_msg, orion_response, intent in sample_messages:
            cursor.execute('''
                INSERT OR IGNORE INTO chat_messages (session_id, user_message, orion_response, intent, created_at)
                VALUES (?, ?, ?, ?, datetime('now', '-' || ? || ' hours'))
            ''', (session_id, user_msg, orion_response, intent, len(sample_messages) - sample_messages.index((session_id, user_msg, orion_response, intent))))
        
        conn.commit()
        print("✅ Sample data added successfully!")
        
        # Show what was added
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM chat_sessions') 
        session_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM chat_messages')
        message_count = cursor.fetchone()[0]
        
        print(f"📊 Database now contains:")
        print(f"   👥 Users: {user_count}")
        print(f"   💬 Chat Sessions: {session_count}")
        print(f"   📝 Messages: {message_count}")
        
    except Exception as e:
        print(f"❌ Error adding sample data: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    add_sample_data()