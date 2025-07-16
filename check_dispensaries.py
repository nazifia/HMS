import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Dispensary

print("Checking dispensaries in the database...")
try:
    dispensaries = Dispensary.objects.all()
    print(f"Total dispensaries found: {dispensaries.count()}")
    
    if dispensaries.exists():
        print("\nDispensaries:")
        for dispensary in dispensaries:
            print(f"- ID: {dispensary.id}, Name: {dispensary.name}, Active: {dispensary.is_active}")
    else:
        print("No dispensaries found in the database.")
        print("\nCreating a sample dispensary...")
        
        # Create a sample dispensary
        sample_dispensary = Dispensary.objects.create(
            name="Main Dispensary",
            location="Ground Floor",
            description="Main hospital dispensary",
            is_active=True
        )
        print(f"Created dispensary: {sample_dispensary.name} (ID: {sample_dispensary.id})")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()