print("Starting test...")

import os
print("Setting Django settings...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

import django
print("Setting up Django...")
django.setup()

print("Importing Dispensary model...")
from pharmacy.models import Dispensary

print("Testing query...")
try:
    count = Dispensary.objects.count()
    print(f"SUCCESS: Found {count} dispensaries in database")
except Exception as e:
    print(f"ERROR: {e}")

print("Test completed.")