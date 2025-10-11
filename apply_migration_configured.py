import os
import sys

print("Configuring Django and applying migration")
print("=" * 50)

import logging
logging.disable(logging.CRITICAL)

# Set environment
os.environ['DJANGO_SETTINGS_MODULE'] = 'hms.settings'
os.chdir('C:\\Users\\dell\\Desktop\\MY_PRODUCTS\\HMS')

import django
from django.conf import settings

django.setup()

from django.core.management import execute_from_command_line

try:
    print("Applying database migration for activity monitoring...")
    
    # Test database connection first
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Current tables: {len(tables)}")
    
    execute_from_command_line(['manage.py', 'migrate', 'accounts', '0007'])
    
    print("Migration applied successfully!")
    print("\nActivity Monitoring system is READY!")
    print("You can now start the server and use all monitoring features.")
    
except Exception as e:
    print("Error:", e)
    try:
        # Try the merge approach
        execute_from_command_line(['manage.py', 'migrate', '--merge'])
        print("Migration completed with merge approach.")
    except:
        print("Please fix the migration issue manually.")
