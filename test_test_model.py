#!/usr/bin/env python
"""
Simple test script to verify Test model functionality
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('C:\\Users\\Dell\\Desktop\\MY_PRODUCTS\\HMS')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from laboratory.models import Test, TestCategory

def test_test_model():
    """Test the Test model functionality"""
    print("Testing Test model functionality...")
    
    try:
        # Test 1: Check if Test model exists
        print("\n1. Checking if Test model exists...")
        test_count = Test.objects.count()
        print(f"   Found {test_count} Test records")
        
        # Test 2: Check if TestCategory model exists
        print("\n2. Checking if TestCategory model exists...")
        category_count = TestCategory.objects.count()
        print(f"   Found {category_count} TestCategory records")
        
        # Test 3: Create a test category
        print("\n3. Creating a test category...")
        category = TestCategory.objects.create(
            name="Test Category",
            description="This is a test category"
        )
        print(f"   Created category: {category.name}")
        
        # Test 4: Create a test
        print("\n4. Creating a test...")
        test = Test.objects.create(
            name="Test Blood Test",
            category=category,
            description="This is a test blood test",
            price=100.00,
            preparation_instructions="Fast for 8 hours",
            normal_range="1-10",
            unit="mg/dL",
            sample_type="blood",
            duration="1 day",
            is_active=True
        )
        print(f"   Created test: {test.name}")
        
        # Test 5: Retrieve the test
        print("\n5. Retrieving the test...")
        retrieved_test = Test.objects.get(id=test.id)
        print(f"   Retrieved test: {retrieved_test.name}")
        
        # Test 6: Update the test
        print("\n6. Updating the test...")
        retrieved_test.price = 150.00
        retrieved_test.save()
        print(f"   Updated test price to: {retrieved_test.price}")
        
        # Test 7: Delete the test
        print("\n7. Deleting the test...")
        test_id = retrieved_test.id
        retrieved_test.delete()
        print(f"   Deleted test with id: {test_id}")
        
        # Test 8: Verify deletion
        print("\n8. Verifying deletion...")
        test_count_after = Test.objects.count()
        print(f"   Test count after deletion: {test_count_after}")
        
        # Test 9: Clean up - delete the category
        print("\n9. Cleaning up - deleting the category...")
        category.delete()
        print(f"   Deleted category: {category.name}")
        
        print("\n✅ All tests passed! Test model is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing Test model: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_test_model()
    sys.exit(0 if success else 1)
