"""
Check if DispensaryTransfer table exists and create it if needed
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.db import connection

# Check if table exists
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='pharmacy_dispensarytransfer';
    """)
    result = cursor.fetchone()
    
    if result:
        print("✅ Table 'pharmacy_dispensarytransfer' EXISTS")
        
        # Show table structure
        cursor.execute("PRAGMA table_info(pharmacy_dispensarytransfer);")
        columns = cursor.fetchall()
        print("\nTable structure:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
    else:
        print("❌ Table 'pharmacy_dispensarytransfer' DOES NOT EXIST")
        print("\nAttempting to create table...")
        
        # Create the table manually
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pharmacy_dispensarytransfer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medication_id INTEGER NOT NULL,
                from_active_store_id INTEGER NOT NULL,
                to_dispensary_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                batch_number VARCHAR(100),
                expiry_date DATE,
                unit_cost DECIMAL(10, 2),
                status VARCHAR(20) NOT NULL,
                requested_by_id INTEGER NOT NULL,
                requested_at DATETIME NOT NULL,
                approved_by_id INTEGER,
                approved_at DATETIME,
                completed_by_id INTEGER,
                completed_at DATETIME,
                notes TEXT,
                FOREIGN KEY (medication_id) REFERENCES pharmacy_medication(id),
                FOREIGN KEY (from_active_store_id) REFERENCES pharmacy_activestore(id),
                FOREIGN KEY (to_dispensary_id) REFERENCES pharmacy_dispensary(id),
                FOREIGN KEY (requested_by_id) REFERENCES accounts_customuser(id),
                FOREIGN KEY (approved_by_id) REFERENCES accounts_customuser(id),
                FOREIGN KEY (completed_by_id) REFERENCES accounts_customuser(id)
            );
        """)
        
        print("✅ Table created successfully!")
        
        # Verify
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='pharmacy_dispensarytransfer';
        """)
        result = cursor.fetchone()
        
        if result:
            print("✅ Verified: Table now exists")
        else:
            print("❌ Error: Table still doesn't exist")

