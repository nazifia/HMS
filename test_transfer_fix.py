#!/usr/bin/env python3
"""
Test script to verify bulk store transfer functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.messages import get_messages
from accounts.models import CustomUser
from pharmacy.models import BulkStore, BulkStoreInventory, Medication, ActiveStore
from pharmacy.views import request_medication_transfer

def test_transfer_functionality():
    """Test bulk store transfer functionality"""
    print("=== Bulk Store Transfer Test ===")
    
    # Check if we have necessary data
    bulk_stores = BulkStore.objects.filter(is_active=True).count()
    print(f"Active bulk stores: {bulk_stores}")
    
    bulk_inventory = BulkStoreInventory.objects.filter(stock_quantity__gt=0).count()
    print(f"Bulk inventory items: {bulk_inventory}")
    
    active_stores = ActiveStore.objects.filter(is_active=True).count()
    print(f"Active stores: {active_stores}")
    
    medications = Medication.objects.filter(is_active=True).count()
    print(f"Active medications: {medications}")
    
    if bulk_stores == 0 or bulk_inventory == 0 or active_stores == 0:
        print("⚠ Warning: Insufficient data for testing")
        return False
    
    # Test GET request to show form
    factory = RequestFactory()
    user = CustomUser.objects.first()
    
    if not user:
        print("No user found!")
        return False
        
    get_request = factory.get('/pharmacy/bulk-store/transfer/request/')
    get_request.user = user
    
    try:
        get_response = request_medication_transfer(get_request)
        print(f"GET request status: {get_response.status_code}")
        
        if get_response.status_code == 200:
            context = get_response.context_data if hasattr(get_response, 'context_data') else {}
            
            # Check if bulk_inventory is provided
            if 'bulk_inventory' in context:
                inventory_count = len(context['bulk_inventory'])
                print(f"✓ Form shows {inventory_count} bulk inventory items")
            else:
                print("⚠ bulk_inventory not found in context")
                
        else:
            print(f"✗ GET request failed: {get_response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error in GET request: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test POST request with sample data
    print("\n--- Testing POST request ---")
    
    # Get first available medication and store
    first_inventory = BulkStoreInventory.objects.filter(stock_quantity__gt=0).first()
    first_active_store = ActiveStore.objects.filter(is_active=True).first()
    
    if not first_inventory or not first_active_store:
        print("⚠ Cannot test POST - no inventory or active store available")
        return True  # Still consider this a partial success
    
    post_data = {
        'medication': str(first_inventory.medication.id),
        'active_store': str(first_active_store.id),
        'quantity': '1',
        'batch_number': '',
        'csrfmiddlewaretoken': 'test-token'  # Will be handled by middleware
    }
    
    post_request = factory.post('/pharmacy/bulk-store/transfer/request/', data=post_data)
    post_request.user = user
    
    try:
        # Simulate CSRF middleware
        post_request.META['CSRF_COOKIE'] = 'test-token'
        
        post_response = request_medication_transfer(post_request)
        print(f"POST request status: {post_response.status_code}")
        
        # Check for redirect (success) or error
        if post_response.status_code == 302:
            print("✓ Transfer request created successfully (redirect)")
            return True
        elif post_response.status_code == 200:
            print("⚠ Form returned - possibly validation error")
            return False
        else:
            print(f"✗ POST request failed: {post_response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error in POST request: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_transfer_functionality()
    
    if success:
        print("\n✓ Transfer functionality test passed!")
    else:
        print("\n✗ Transfer functionality test failed!")
        sys.exit(1)
