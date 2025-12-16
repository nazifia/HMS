import os
import sys

print("Applying Activity Monitoring Migration")
print("=" * 50)

import logging
logging.disable(logging.CRITICAL)

os.chdir('C:\\Users\\dell\\Desktop\\MY_PRODUCTS\\HMS')

try:
    from django.core.management import execute_from_command_line
    
    print("Applying database migration for activity monitoring...")
    execute_from_command_line(['manage.py', 'migrate', 'accounts', '0007'])
    
    print("Migration applied successfully!")
    print("\nActivity Monitoring tables created!")
    print("\nYou can now:")
    print("  1. Start the server: python manage.py runserver")
    print(" 2. Access: User Management -> Activity Monitor")
    print(" 3. All monitoring features are available!")
    
    print("\nSystem Status: ACTIVE")
    
except Exception as e:
    print("Migration error:", e)
    print("Try running: python manage.py migrate --merge")
