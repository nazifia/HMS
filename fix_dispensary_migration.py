import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

# Check current state
cursor = connection.cursor()

# Check if table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pharmacy_dispensary';")
table_exists = bool(cursor.fetchone())
print(f"Table 'pharmacy_dispensary' exists: {table_exists}")

if not table_exists:
    print("Creating table manually...")
    # Create the table manually
    cursor.execute("""
        CREATE TABLE "pharmacy_dispensary" (
            "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
            "name" varchar(100) NOT NULL UNIQUE,
            "location" varchar(200) NULL,
            "description" text NULL,
            "is_active" bool NOT NULL,
            "created_at" datetime NOT NULL,
            "updated_at" datetime NOT NULL,
            "manager_id" bigint NULL REFERENCES "accounts_customuser" ("id") DEFERRABLE INITIALLY DEFERRED
        );
    """)
    
    # Create index
    cursor.execute('CREATE INDEX "pharmacy_dispensary_manager_id_idx" ON "pharmacy_dispensary" ("manager_id");')
    
    print("Table created successfully!")
    
    # Mark migration as applied
    cursor.execute("INSERT INTO django_migrations (app, name, applied) VALUES ('pharmacy', '0002_dispensary', datetime('now'));")
    
    print("Migration marked as applied.")
else:
    print("Table already exists. Checking schema...")
    cursor.execute("PRAGMA table_info(pharmacy_dispensary);")
    columns = cursor.fetchall()
    print("Current columns:")
    for column in columns:
        print(f"  {column[1]} ({column[2]})")