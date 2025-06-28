import os
import django
import sqlite3

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

print("Fixing dispensary table schema...")

# Connect to database
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

try:
    # Drop the existing table
    cursor.execute("DROP TABLE IF EXISTS pharmacy_dispensary;")
    print("Dropped existing pharmacy_dispensary table")
    
    # Create the table with correct schema
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
    print("Created pharmacy_dispensary table with correct schema")
    
    # Create index for manager_id
    cursor.execute('CREATE INDEX "pharmacy_dispensary_manager_id_idx" ON "pharmacy_dispensary" ("manager_id");')
    print("Created index for manager_id")
    
    # Commit changes
    conn.commit()
    print("Changes committed to database")
    
    # Verify the table schema
    cursor.execute("PRAGMA table_info(pharmacy_dispensary);")
    columns = cursor.fetchall()
    print("\nNew table schema:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()

# Test the model
try:
    from pharmacy.models import Dispensary
    
    # Test creating a dispensary
    test_dispensary = Dispensary.objects.create(
        name="Test Dispensary",
        location="Test Location",
        description="Test Description",
        is_active=True
    )
    print(f"\nSuccessfully created test dispensary: {test_dispensary.name}")
    print(f"Description: {test_dispensary.description}")
    
    # Clean up
    test_dispensary.delete()
    print("Test dispensary deleted")
    
    print("\nTable fix completed successfully!")
    
except Exception as e:
    print(f"Model test failed: {e}")
    import traceback
    traceback.print_exc()