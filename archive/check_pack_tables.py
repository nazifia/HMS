import sqlite3

# Connect to the database
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Get all pack-related tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%pack%'")
tables = cursor.fetchall()
print('Pack-related tables:', tables)

# Check if pharmacy_packitem table exists and its columns
try:
    cursor.execute("PRAGMA table_info(pharmacy_packitem)")
    columns = cursor.fetchall()
    print('pharmacy_packitem columns:')
    for column in columns:
        print(f"  {column[1]} ({column[2]})")
except Exception as e:
    print(f"Error checking pharmacy_packitem table: {e}")

conn.close()