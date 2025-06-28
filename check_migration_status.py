import os
import sys
import django

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.core.management import execute_from_command_line

print("Checking migration status...")
try:
    execute_from_command_line(['manage.py', 'showmigrations', 'pharmacy'])
except SystemExit:
    pass

print("\nChecking if we can import and use Dispensary...")
try:
    from pharmacy.models import Dispensary
    dispensaries = Dispensary.objects.all()
    print(f"SUCCESS: Dispensary model works, found {dispensaries.count()} records")
except Exception as e:
    print(f"ERROR: {e}")
    
print("Done.")