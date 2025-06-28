import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

# Check if table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pharmacy_dispensary';")
table_exists = bool(cursor.fetchone())
print(f"Table 'pharmacy_dispensary' exists: {table_exists}")

if table_exists:
    # Get table schema
    cursor.execute("PRAGMA table_info(pharmacy_dispensary);")
    columns = cursor.fetchall()
    print("\nTable schema:")
    for column in columns:
        print(f"  {column[1]} ({column[2]})")
else:
    print("Table does not exist - migration needs to be applied")

# Check migration status
from django.db.migrations.executor import MigrationExecutor
executor = MigrationExecutor(connection)
plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
print(f"\nPending migrations: {len(plan)}")
for migration in plan:
    print(f"  {migration}")