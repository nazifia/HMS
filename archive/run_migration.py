#!/usr/bin/env python
import os
import sys
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
    django.setup()
    
    print("Running migration for pharmacy app...")
    try:
        execute_from_command_line(['manage.py', 'migrate', 'pharmacy', '--verbosity=2'])
        print("Migration completed.")
    except Exception as e:
        print(f"Migration failed: {e}")
    
    print("\nTesting Dispensary model...")
    try:
        from pharmacy.models import Dispensary
        count = Dispensary.objects.count()
        print(f"Dispensary model test successful. Count: {count}")
    except Exception as e:
        print(f"Dispensary model test failed: {e}")
        import traceback
        traceback.print_exc()