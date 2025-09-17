#!/usr/bin/env python3
"""
Script to create and examine the Orion Voice Assistant database
"""
import sqlite3
import os
from datetime import datetime

def main():
    # Create/connect to the database
    conn = sqlite3.connect('orion_vva.db')
    cursor = conn.cursor()

    print('🗃️  Database: orion_vva.db')
    print(f'📁 Location: {os.path.abspath("orion_vva.db")}')
    
    # Create tables if they don't exist (basic structure based on your models)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(80) UNIQUE NOT NULL,
        email VARCHAR(120) UNIQUE NOT NULL,
        password_hash VARCHAR(128),
        full_name VARCHAR(200),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title VARCHAR(200),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        user_message TEXT,
        orion_response TEXT,
        intent VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
    )''')

    # Commit changes
    conn.commit()

    # Show table info
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print('\n📊 Tables in database:')
    for table in tables:
        print(f'   • {table[0]}')

    # Show table structures
    for table in tables:
        table_name = table[0]
        cursor.execute(f'PRAGMA table_info({table_name})')
        columns = cursor.fetchall()
        print(f'\n🏗️  Table Structure: {table_name}')
        print('   Columns:')
        for col in columns:
            pk = ' (PRIMARY KEY)' if col[5] == 1 else ''
            null = 'NOT NULL' if col[3] == 1 else 'NULL'
            default = f' DEFAULT {col[4]}' if col[4] else ''
            print(f'     - {col[1]}: {col[2]} {null}{default}{pk}')

    # Check if there's any data
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM chat_sessions')
    session_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM chat_messages')
    message_count = cursor.fetchone()[0]

    print(f'\n📈 Data Summary:')
    print(f'   👥 Users: {user_count}')
    print(f'   💬 Chat Sessions: {session_count}')
    print(f'   📝 Chat Messages: {message_count}')

    # Show some sample data if it exists
    if user_count > 0:
        print('\n👥 Users:')
        cursor.execute('SELECT id, username, email, full_name, created_at FROM users LIMIT 5')
        users = cursor.fetchall()
        for user in users:
            print(f'   ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, Name: {user[3]}, Created: {user[4]}')
    
    if message_count > 0:
        print('\n💬 Recent Messages:')
        cursor.execute('''
            SELECT user_message, orion_response, intent, created_at 
            FROM chat_messages 
            ORDER BY created_at DESC 
            LIMIT 5
        ''')
        messages = cursor.fetchall()
        for msg in messages:
            print(f'   User: "{msg[0][:50]}..."')
            print(f'   Orion: "{msg[1][:50]}..."')
            print(f'   Intent: {msg[2]}, Time: {msg[3]}')
            print('   ---')

    # Database file size
    db_size = os.path.getsize('orion_vva.db')
    print(f'\n💾 Database Size: {db_size} bytes ({db_size/1024:.2f} KB)')

    conn.close()
    print('\n✅ Database examination complete!')

if __name__ == '__main__':
    main()