#!/usr/bin/env python
"""
Test script to verify bulk store modal functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from pharmacy.models import Medication, BulkStore, BulkStoreInventory, Dispensary, ActiveStore
from decimal import Decimal

def test_bulk_store_modal():
    """Test the bulk store modal functionality"""
    print("Testing bulk store modal functionality...")
    
    # Create test client
    client = Client()
    
    # Create test user
    user = CustomUser.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    client.login(username='testuser', password='testpass123')
    
    # Create test data
    medication = Medication.objects.create(
        name='Test Medication',
        description='Test description',
        category_id=1,
        unit='Tablets',
        strength='500mg',
        is_active=True
    )
    
    bulk_store = BulkStore.objects.create(
        name='Test Bulk Store',
        location='Test Location',
        is_active=True
    )
    
    dispensary = Dispensary.objects.create(
        name='Test Dispensary',
        location='Test Location',
        is_active=True
    )
    
    active_store = ActiveStore.objects.create(
        dispensary=dispensary,
        is_active=True
    )
    
    # Create bulk inventory
    bulk_inventory = BulkStoreInventory.objects.create(
        medication=medication,
        bulk_store=bulk_store,
        stock_quantity=100,
        unit_cost=Decimal('10.00'),
        batch_number='BATCH001',
        expiry_date='2025-12-31'
    )
    
    # Test GET request to bulk store dashboard
    print("\n1. Testing bulk store dashboard GET request...")
    response = client.get(reverse('pharmacy:bulk_store_dashboard'))
    
    if response.status_code == 200:
        print("✓ Bulk store dashboard loaded successfully")
        
        # Check if modal elements are present
        content = response.content.decode('utf-8')
        
        if 'transferModal' in content:
            print("✓ Transfer modal present in template")
        else:
            print("✗ Transfer modal not found in template")
            
        if 'medication' in content and 'active_store' in content:
            print("✓ Modal form fields present")
        else:
            print("✗ Modal form fields missing")
            
    else:
        print(f"✗ Failed to load bulk store dashboard: {response.status_code}")
    
    # Test POST request for transfer
    print("\n2. Testing transfer request POST...")
    response = client.post(
        reverse('pharmacy:request_medication_transfer'),
        {
            'medication': medication.id,
            'active_store': active_store.id,
            'quantity': 10,
            'notes': 'Test transfer'
        }
    )
    
    if response.status_code == 302:
        print("✓ Transfer request created successfully (redirect expected)")
    else:
        print(f"✗ Transfer request failed: {response.status_code}")
        print(f"Response content: {response.content.decode('utf-8')[:500]}")
    
    print("\n3. Checking context variables in view...")
    # Test if view returns correct context
    from pharmacy.views import bulk_store_dashboard
    from django.http import HttpRequest
    from django.contrib.auth.models import AnonymousUser
    
    # Create a mock request
    request = HttpRequest()
    request.user = user
    request.method = 'GET'
    
    # Call the view function directly
    try:
        context = bulk_store_dashboard(request)
        if hasattr(context, 'context_data'):
            ctx = context.context_data
            if 'dispensaries' in ctx and 'bulk_inventory' in ctx:
                print("✓ Required context variables present")
            else:
                print("✗ Missing context variables")
                print(f"  - dispensaries: {'present' if 'dispensaries' in ctx else 'missing'}")
                print(f"  - bulk_inventory: {'present' if 'bulk_inventory' in ctx else 'missing'}")
                print(f"  - total_stock_value: {'present' if 'total_stock_value' in ctx else 'missing'}")
    except Exception as e:
        print(f"✗ Error testing view context: {str(e)}")
    
    print("\nTest completed!")

if __name__ == '__main__':
    test_bulk_store_modal()
