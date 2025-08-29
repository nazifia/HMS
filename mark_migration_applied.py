import sqlite3
import datetime

# Connect to the database
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Insert the migration record
cursor.execute(
    "INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, ?)",
    ('pharmacy', '0012_pack_alter_packitem_options_alter_packorder_options_and_more', datetime.datetime.now())
)

conn.commit()
conn.close()
print('Migration 0012 marked as applied')