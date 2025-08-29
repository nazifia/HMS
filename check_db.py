import sqlite3

# Connect to the database
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Get all pharmacy-related tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'pharmacy%'")
tables = cursor.fetchall()
print('Pharmacy tables:', tables)

# Get migration status
cursor.execute("SELECT * FROM django_migrations WHERE app = 'pharmacy' ORDER BY id")
migrations = cursor.fetchall()
print('Pharmacy migrations:')
for migration in migrations:
    print(f"  {migration[2]} (applied at {migration[3]})")

conn.close()