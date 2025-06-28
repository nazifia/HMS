import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

try:
    from pharmacy.models import Dispensary
    print("Testing Dispensary model...")
    
    # Test the exact line that's causing the error
    dispensaries = Dispensary.objects.all().order_by('name')
    print(f"Successfully queried dispensaries: {dispensaries.count()} found")
    
    # Test creating a dispensary with description
    test_dispensary = Dispensary.objects.create(
        name="Test Dispensary with Description",
        location="Test Location",
        description="This is a test description field",
        is_active=True
    )
    print(f"Created dispensary with description: {test_dispensary.description}")
    
    # Test querying by description
    dispensaries_with_desc = Dispensary.objects.filter(description__icontains="test")
    print(f"Found {dispensaries_with_desc.count()} dispensaries with 'test' in description")
    
    # Clean up
    test_dispensary.delete()
    print("Test completed successfully!")
    
except Exception as e:
    print(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()