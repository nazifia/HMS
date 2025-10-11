import os
import sys
import django
from django.db import connection
from django.core.management import execute_from_command_line

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def apply_migration():
    """Apply the migration to add missing fields"""
    try:
        with connection.cursor() as cursor:
            # Check if the migration has been applied
            cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app='accounts' AND name='0015_add_missing_fields_to_activity_models'")
            migration_applied = cursor.fetchone()[0] > 0
            
            if migration_applied:
                print("Migration 0015 is already applied")
                return
            
            # Check if ActivityAlert table exists and has ip_address column
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts_activityalert'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                print("ActivityAlert table does not exist. Please run initial migrations first.")
                return
            
            # Check if ip_address column exists
            cursor.execute("PRAGMA table_info(accounts_activityalert)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add missing columns if they don't exist
            if 'ip_address' not in columns:
                print("Adding ip_address column to ActivityAlert table...")
                cursor.execute("ALTER TABLE accounts_activityalert ADD COLUMN ip_address VARCHAR(15)")
            
            if 'metadata' not in columns:
                print("Adding metadata column to ActivityAlert table...")
                cursor.execute("ALTER TABLE accounts_activityalert ADD COLUMN metadata TEXT DEFAULT '{}'")
            
            if 'resolved_at' not in columns:
                print("Adding resolved_at column to ActivityAlert table...")
                cursor.execute("ALTER TABLE accounts_activityalert ADD COLUMN resolved_at DATETIME")
            
            if 'resolved_by_id' not in columns:
                print("Adding resolved_by_id column to ActivityAlert table...")
                cursor.execute("ALTER TABLE accounts_activityalert ADD COLUMN resolved_by_id INTEGER REFERENCES accounts_customuser(id)")
            
            if 'resolution_notes' not in columns:
                print("Adding resolution_notes column to ActivityAlert table...")
                cursor.execute("ALTER TABLE accounts_activityalert ADD COLUMN resolution_notes TEXT")
            
            if 'updated_at' not in columns:
                print("Adding updated_at column to ActivityAlert table...")
                cursor.execute("ALTER TABLE accounts_activityalert ADD COLUMN updated_at DATETIME")
            
            # Check UserActivity table fields
            cursor.execute("PRAGMA table_info(accounts_useractivity)")
            activity_columns = [column[1] for column in cursor.fetchall()]
            
            if 'ip_address' not in activity_columns:
                print("Adding ip_address column to UserActivity table...")
                cursor.execute("ALTER TABLE accounts_useractivity ADD COLUMN ip_address VARCHAR(15)")
                
            # Add other missing UserActivity fields
            missing_fields = {
                'module': 'VARCHAR(100)',
                'object_type': 'VARCHAR(100)',
                'object_id': 'VARCHAR(100)',
                'object_repr': 'VARCHAR(500)',
                'user_agent': 'TEXT',
                'session_key': 'VARCHAR(100)',
                'status_code': 'INTEGER',
                'response_time_ms': 'INTEGER',
                'additional_data': 'TEXT DEFAULT "{}"',
                'activity_level': 'VARCHAR(10) DEFAULT "low"'
            }
            
            for field_name, field_type in missing_fields.items():
                if field_name not in activity_columns:
                    print(f"Adding {field_name} column to UserActivity table...")
                    cursor.execute(f"ALTER TABLE accounts_useractivity ADD COLUMN {field_name} {field_type}")
            
            # Check UserSession table fields
            cursor.execute("PRAGMA table_info(accounts_usersession)")
            session_columns = [column[1] for column in cursor.fetchall()]
            
            if 'ip_address' not in session_columns:
                print("Adding ip_address column to UserSession table...")
                cursor.execute("ALTER TABLE accounts_usersession ADD COLUMN ip_address VARCHAR(15)")
                
            # Add other missing UserSession fields
            missing_session_fields = {
                'user_agent': 'TEXT',
                'last_activity': 'DATETIME',
                'is_active': 'BOOLEAN DEFAULT 1',
                'page_views': 'INTEGER DEFAULT 0',
                'total_requests': 'INTEGER DEFAULT 0',
                'average_response_time': 'REAL',
                'ended_at': 'DATETIME',
                'ended_reason': 'VARCHAR(100)'
            }
            
            for field_name, field_type in missing_session_fields.items():
                if field_name not in session_columns:
                    print(f"Adding {field_name} column to UserSession table...")
                    cursor.execute(f"ALTER TABLE accounts_usersession ADD COLUMN {field_name} {field_type}")
            
            # Record the migration as applied
            cursor.execute("""
                INSERT INTO django_migrations (app, name, applied) 
                VALUES ('accounts', '0015_add_missing_fields_to_activity_models', datetime('now'))
            """)
            
            print("Migration applied successfully!")
            
    except Exception as e:
        print(f"Error applying migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    apply_migration()
