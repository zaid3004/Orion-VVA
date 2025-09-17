#!/usr/bin/env python3
"""
Interactive SQLite Database Browser for Orion Voice Assistant
"""
import sqlite3
import os
from datetime import datetime

class OrionDBBrowser:
    def __init__(self, db_path='orion_vva.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to the database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            print(f"✅ Connected to database: {os.path.abspath(self.db_path)}")
            return True
        except Exception as e:
            print(f"❌ Error connecting to database: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("🔒 Database connection closed")
    
    def show_tables(self):
        """Show all tables in the database"""
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = self.cursor.fetchall()
        print("\n📊 Available Tables:")
        for i, table in enumerate(tables, 1):
            print(f"   {i}. {table[0]}")
        return [table[0] for table in tables]
    
    def describe_table(self, table_name):
        """Show table structure"""
        try:
            self.cursor.execute(f'PRAGMA table_info({table_name})')
            columns = self.cursor.fetchall()
            print(f"\n🏗️  Table Structure: {table_name}")
            print("   Columns:")
            for col in columns:
                pk = ' (PRIMARY KEY)' if col[5] == 1 else ''
                null = 'NOT NULL' if col[3] == 1 else 'NULL'
                default = f' DEFAULT {col[4]}' if col[4] else ''
                print(f"     - {col[1]}: {col[2]} {null}{default}{pk}")
        except Exception as e:
            print(f"❌ Error describing table: {e}")
    
    def count_records(self, table_name):
        """Count records in table"""
        try:
            self.cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = self.cursor.fetchone()[0]
            print(f"📊 Records in {table_name}: {count}")
            return count
        except Exception as e:
            print(f"❌ Error counting records: {e}")
            return 0
    
    def show_data(self, table_name, limit=10):
        """Show data from table"""
        try:
            self.cursor.execute(f'SELECT * FROM {table_name} LIMIT {limit}')
            data = self.cursor.fetchall()
            
            # Get column names
            self.cursor.execute(f'PRAGMA table_info({table_name})')
            columns = [col[1] for col in self.cursor.fetchall()]
            
            if data:
                print(f"\n📋 Data from {table_name} (showing {len(data)} records):")
                print("   Columns:", ", ".join(columns))
                print("   " + "-" * 80)
                for i, row in enumerate(data, 1):
                    print(f"   Record {i}:")
                    for col_name, value in zip(columns, row):
                        display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                        print(f"     {col_name}: {display_value}")
                    print("     " + "-" * 40)
            else:
                print(f"📭 No data found in {table_name}")
        except Exception as e:
            print(f"❌ Error showing data: {e}")
    
    def execute_query(self, query):
        """Execute custom SQL query"""
        try:
            self.cursor.execute(query)
            if query.strip().upper().startswith('SELECT'):
                results = self.cursor.fetchall()
                if results:
                    print(f"\n🔍 Query Results ({len(results)} rows):")
                    for i, row in enumerate(results, 1):
                        print(f"   Row {i}: {row}")
                else:
                    print("📭 No results found")
            else:
                self.conn.commit()
                print("✅ Query executed successfully")
        except Exception as e:
            print(f"❌ Error executing query: {e}")
    
    def add_sample_user(self):
        """Add a sample user for testing"""
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO users (username, email, password_hash, full_name, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', ('commander', 'commander@orion.ai', 'hashed_password_here', 'Commander Test User', 1))
            self.conn.commit()
            print("✅ Sample user added (if not already exists)")
        except Exception as e:
            print(f"❌ Error adding sample user: {e}")
    
    def interactive_menu(self):
        """Interactive menu for database operations"""
        while True:
            print("\n" + "="*60)
            print("🤖 ORION DATABASE BROWSER")
            print("="*60)
            print("1. Show all tables")
            print("2. Describe table structure")
            print("3. Count records in table")
            print("4. Show data from table")
            print("5. Execute custom SQL query")
            print("6. Add sample user")
            print("7. Show database info")
            print("0. Exit")
            print("-"*60)
            
            choice = input("Enter your choice (0-7): ").strip()
            
            if choice == '0':
                print("👋 Goodbye, Commander!")
                break
            elif choice == '1':
                self.show_tables()
            elif choice == '2':
                tables = self.show_tables()
                if tables:
                    table_choice = input("Enter table name: ").strip()
                    if table_choice in tables:
                        self.describe_table(table_choice)
                    else:
                        print("❌ Invalid table name")
            elif choice == '3':
                tables = self.show_tables()
                if tables:
                    table_choice = input("Enter table name: ").strip()
                    if table_choice in tables:
                        self.count_records(table_choice)
                    else:
                        print("❌ Invalid table name")
            elif choice == '4':
                tables = self.show_tables()
                if tables:
                    table_choice = input("Enter table name: ").strip()
                    if table_choice in tables:
                        limit = input("Enter limit (default 10): ").strip() or "10"
                        try:
                            limit = int(limit)
                            self.show_data(table_choice, limit)
                        except ValueError:
                            print("❌ Invalid limit number")
                    else:
                        print("❌ Invalid table name")
            elif choice == '5':
                query = input("Enter SQL query: ").strip()
                if query:
                    self.execute_query(query)
                else:
                    print("❌ Empty query")
            elif choice == '6':
                self.add_sample_user()
            elif choice == '7':
                self.show_database_info()
            else:
                print("❌ Invalid choice")
    
    def show_database_info(self):
        """Show general database information"""
        print(f"\n💾 Database Information:")
        print(f"   📁 File: {os.path.abspath(self.db_path)}")
        if os.path.exists(self.db_path):
            size = os.path.getsize(self.db_path)
            print(f"   📏 Size: {size} bytes ({size/1024:.2f} KB)")
        
        tables = self.show_tables()
        print(f"   📊 Total Tables: {len(tables)}")
        
        total_records = 0
        for table in tables:
            if table != 'sqlite_sequence':
                count = self.count_records(table)
                total_records += count
        print(f"   📈 Total Records: {total_records}")

def main():
    browser = OrionDBBrowser()
    
    if browser.connect():
        try:
            browser.interactive_menu()
        except KeyboardInterrupt:
            print("\n\n⚡ Interrupted by user")
        finally:
            browser.close()
    else:
        print("❌ Could not connect to database")

if __name__ == '__main__':
    main()