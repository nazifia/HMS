import sqlite3

# Connect to the database
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Check columns in pharmacy_activestoreinventory table
cursor.execute('PRAGMA table_info(pharmacy_activestoreinventory)')
columns = cursor.fetchall()
print('pharmacy_activestoreinventory columns:')
for col in columns:
    print(f"  {col[1]} ({col[2]}) NOT NULL: {bool(col[3])}")

conn.close()