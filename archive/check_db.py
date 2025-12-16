import sqlite3
import os

# Connect to the database
db_path = 'db.sqlite3'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if the table exists and get its columns
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pharmacy_prescriptioncartitem'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        print("Table 'pharmacy_prescriptioncartitem' exists")
        cursor.execute("PRAGMA table_info('pharmacy_prescriptioncartitem')")
        columns = cursor.fetchall()
        print("Columns in 'pharmacy_prescriptioncartitem':")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
    else:
        print("Table 'pharmacy_prescriptioncartitem' does not exist")
    
    conn.close()
else:
    print(f"Database file {db_path} not found")