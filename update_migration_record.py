import os
import django
import sqlite3

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Connect to database
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

try:
    # Check if migration record exists
    cursor.execute("SELECT * FROM django_migrations WHERE app='pharmacy' AND name='0002_dispensary';")
    existing = cursor.fetchone()
    
    if not existing:
        # Insert migration record
        cursor.execute("""
            INSERT INTO django_migrations (app, name, applied) 
            VALUES ('pharmacy', '0002_dispensary', datetime('now'));
        """)
        print("Added migration record for 0002_dispensary")
        conn.commit()
    else:
        print("Migration record already exists")
        
except Exception as e:
    print(f"Error updating migration record: {e}")
finally:
    conn.close()

print("Migration record update completed.")