import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

try:
    django.setup()
    print("Django setup successful")
    
    # Test importing all pharmacy components
    from pharmacy import views, models, forms, admin
    print("All pharmacy imports successful")
    
    # Test the specific model that was causing issues
    from pharmacy.models import Dispensary
    print("Dispensary model import successful")
    
    # Test a basic query
    count = Dispensary.objects.count()
    print(f"Dispensary table accessible, contains {count} records")
    
    print("Server startup test completed successfully!")
    
except Exception as e:
    print(f"Error during startup: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)