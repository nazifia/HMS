"""
Fix DispensaryTransfer table to match the model
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.db import connection

# Drop and recreate the table
with connection.cursor() as cursor:
    print("Dropping existing table...")
    cursor.execute("DROP TABLE IF EXISTS pharmacy_dispensarytransfer;")
    
    print("Creating new table with correct schema...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pharmacy_dispensarytransfer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medication_id INTEGER NOT NULL,
            from_active_store_id INTEGER NOT NULL,
            to_dispensary_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            batch_number VARCHAR(50),
            expiry_date DATE,
            unit_cost DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            requested_by_id INTEGER,
            approved_by_id INTEGER,
            transferred_by_id INTEGER,
            notes TEXT,
            requested_at DATETIME NOT NULL,
            approved_at DATETIME,
            transferred_at DATETIME,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY (medication_id) REFERENCES pharmacy_medication(id) ON DELETE CASCADE,
            FOREIGN KEY (from_active_store_id) REFERENCES pharmacy_activestore(id) ON DELETE CASCADE,
            FOREIGN KEY (to_dispensary_id) REFERENCES pharmacy_dispensary(id) ON DELETE CASCADE,
            FOREIGN KEY (requested_by_id) REFERENCES accounts_customuser(id) ON DELETE SET NULL,
            FOREIGN KEY (approved_by_id) REFERENCES accounts_customuser(id) ON DELETE SET NULL,
            FOREIGN KEY (transferred_by_id) REFERENCES accounts_customuser(id) ON DELETE SET NULL
        );
    """)
    
    print("✅ Table created successfully!")
    
    # Verify
    cursor.execute("PRAGMA table_info(pharmacy_dispensarytransfer);")
    columns = cursor.fetchall()
    print("\nTable structure:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")

