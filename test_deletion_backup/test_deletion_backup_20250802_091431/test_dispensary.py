import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

try:
    from pharmacy.models import Dispensary
    print("Model import successful")
    
    # Try to query the model
    dispensaries = Dispensary.objects.all()
    print(f"Query successful. Found {dispensaries.count()} dispensaries.")
    
    # Try to create a test dispensary
    test_dispensary = Dispensary(
        name="Test Dispensary",
        location="Test Location",
        description="Test Description",
        is_active=True
    )
    test_dispensary.save()
    print("Test dispensary created successfully")
    
    # Try to retrieve it
    retrieved = Dispensary.objects.get(name="Test Dispensary")
    print(f"Retrieved dispensary: {retrieved.name} - {retrieved.description}")
    
    # Clean up
    retrieved.delete()
    print("Test dispensary deleted successfully")
    
    print("All tests passed! The Dispensary model is working correctly.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()