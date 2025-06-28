import os
import django
import sqlite3

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Write output to file
with open('debug_output.txt', 'w') as f:
    f.write("Starting debug process...\n")
    
    # Check database directly
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pharmacy_dispensary';")
        table_exists = cursor.fetchone()
        f.write(f"Table pharmacy_dispensary exists: {bool(table_exists)}\n")
        
        if table_exists:
            # Get table schema
            cursor.execute("PRAGMA table_info(pharmacy_dispensary);")
            columns = cursor.fetchall()
            f.write("Table schema:\n")
            for col in columns:
                f.write(f"  {col[1]} ({col[2]})\n")
        
        conn.close()
        
    except Exception as e:
        f.write(f"Database check error: {e}\n")
    
    # Test Django model
    try:
        from pharmacy.models import Dispensary
        f.write("Dispensary model imported successfully\n")
        
        count = Dispensary.objects.count()
        f.write(f"Dispensary count: {count}\n")
        
        # Try to create a test record
        test_dispensary = Dispensary.objects.create(
            name="Debug Test Dispensary",
            description="Test description for debugging"
        )
        f.write(f"Created test dispensary: {test_dispensary.name}\n")
        
        # Clean up
        test_dispensary.delete()
        f.write("Test dispensary deleted\n")
        
        f.write("All tests passed!\n")
        
    except Exception as e:
        f.write(f"Django model error: {e}\n")
        import traceback
        f.write(traceback.format_exc())

print("Debug completed. Check debug_output.txt for results.")