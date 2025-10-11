import os
import sys
import logging

logging.disable(logging.CRITICAL)

os.environ['DJANGO_SETTINGS_MODULE'] = 'hms.settings'
os.chdir('C:\\Users\\dell\\Desktop\\MY_PRODUCTS\\HMS')

import django
django.setup()

from django.core.management import execute_from_command_line

try:
    print("Fixing migration conflicts and applying...")
    
    # First try to fix conflicts
    execute_from_command_line(['manage.py', 'migrate', '--merge'])
    
    print("Migration completed successfully!")
    print("\nActivity Monitoring tables are ready!")
    print("The system can now track all user activities.")
    
except Exception as e:
    print(f"Migration error: {e}")
    print("\nAlternative approach:")
    print("1. Manually delete migration file 0007_activity_monitoring_models.py")
    print("2. Run: python manage.py makemigrations accounts")
    print("3. Then run: python manage.py migrate")
