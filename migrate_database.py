#!/usr/bin/env python3
"""
Database migration script to upgrade from old schema to new schema.
"""
import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path="logs.db"):
    """Migrate database from old schema to new schema."""
    print(f"🔄 Migrating database: {db_path}")
    
    # Check if database exists
    if not Path(db_path).exists():
        print("❌ Database file not found!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(logs)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Current columns: {columns}")
        
        # Add missing columns from new schema
        new_columns = {
            'x_forwarded_for': 'TEXT',
            'path': 'TEXT', 
            'query': 'TEXT',
            'body_digest': 'TEXT',
            'body_content': 'TEXT',
            'referer': 'TEXT',
            'accept_language': 'TEXT',
            'campaign': 'TEXT',
            'response_time_ms': 'INTEGER'
        }
        
        changes_made = 0
        
        for column_name, column_type in new_columns.items():
            if column_name not in columns:
                print(f"➕ Adding column: {column_name} ({column_type})")
                try:
                    cursor.execute(f"ALTER TABLE logs ADD COLUMN {column_name} {column_type}")
                    changes_made += 1
                except sqlite3.Error as e:
                    print(f"⚠️  Warning: Could not add column {column_name}: {e}")
        
        # Set default campaign for existing records
        if 'campaign' not in columns:
            print("🏷️  Setting default campaign for existing records...")
            cursor.execute("UPDATE logs SET campaign = 'legacy-import' WHERE campaign IS NULL")
        
        # Create campaigns table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Create default campaign
        cursor.execute("""
            INSERT OR IGNORE INTO campaigns (name, description) 
            VALUES ('legacy-import', 'Imported from legacy database')
        """)
        
        # Create indexes for better performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_timestamp_campaign ON logs(timestamp, campaign)",
            "CREATE INDEX IF NOT EXISTS idx_ip_campaign ON logs(ip, campaign)",
            "CREATE INDEX IF NOT EXISTS idx_path_campaign ON logs(path, campaign)",
            "CREATE INDEX IF NOT EXISTS idx_method_campaign ON logs(method, campaign)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except sqlite3.Error as e:
                print(f"⚠️  Warning: Could not create index: {e}")
        
        conn.commit()
        conn.close()
        
        if changes_made > 0:
            print(f"✅ Migration completed successfully! Added {changes_made} columns.")
        else:
            print("✅ Database is already up to date!")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "logs.db"
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)