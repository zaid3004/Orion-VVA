#!/usr/bin/env python3
"""
View all content in Orion Voice Assistant database
"""
import sqlite3
import os
from datetime import datetime

def view_database_content():
    db_path = 'orion_vva.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return
    
    print("🗃️  ORION DATABASE CONTENT VIEWER")
    print("=" * 50)
    print(f"📁 Database: {os.path.abspath(db_path)}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()
        
        if not tables:
            print("📭 No user tables found in database")
            return
        
        print(f"📊 Found {len(tables)} tables")
        print("=" * 50)
        
        for table_tuple in tables:
            table_name = table_tuple[0]
            
            # Get column info
            cursor.execute(f'PRAGMA table_info({table_name})')
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Count records
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            record_count = cursor.fetchone()[0]
            
            print(f"\n🏷️  TABLE: {table_name.upper()}")
            print(f"📊 Records: {record_count}")
            print(f"📋 Columns: {', '.join(column_names)}")
            
            if record_count > 0:
                # Show all data
                cursor.execute(f'SELECT * FROM {table_name}')
                records = cursor.fetchall()
                
                print("📄 DATA:")
                print("-" * 80)
                
                for i, record in enumerate(records, 1):
                    print(f"   📝 Record {i}:")
                    for col_name, value in zip(column_names, record):
                        # Handle long text by truncating
                        if isinstance(value, str) and len(value) > 100:
                            display_value = value[:100] + "..."
                        else:
                            display_value = value
                        print(f"      {col_name}: {display_value}")
                    print()
            else:
                print("   📭 No data in this table")
            
            print("-" * 80)
        
        conn.close()
        print("\n✅ Database content review complete!")
        
    except Exception as e:
        print(f"❌ Error reading database: {e}")

if __name__ == '__main__':
    view_database_content()