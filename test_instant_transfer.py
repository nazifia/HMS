#!/usr/bin/env python
"""
Test script to verify instant transfer functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import Client
from accounts.models import CustomUser
from pharmacy.models import Medication, BulkStore, BulkStoreInventory, Dispensary, ActiveStore
from datetime import date, timedelta

def test_instant_transfer():
    """Test instant transfer functionality"""
    print("Testing instant transfer functionality...")
    
    # Create test user
    user, created = CustomUser.objects.get_or_create(
        username='test_pharmacist',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'Pharmacist',
            'phone_number': '+1234567899'
        }
    )
    
    # Create test medication
    medication, created = Medication.objects.get_or_create(
        name='Test Instant Transfer Medication 2024',
        defaults={
            'description': 'Test medication for instant transfer',
            'strength': '500mg',
            'price': 15.00,
            'reorder_level': 10,
            'is_active': True
        }
    )
    
    # Create test bulk store
    bulk_store, created = BulkStore.objects.get_or_create(
        name='Test Bulk Store',
        defaults={
            'location': 'Test Location',
            'capacity': 10000,
            'is_active': True
        }
    )
    
    # Create test bulk store inventory
    bulk_inventory, created = BulkStoreInventory.objects.get_or_create(
        medication=medication,
        bulk_store=bulk_store,
        defaults={
            'stock_quantity': 100,
            'unit_cost': 10.00,
            'expiry_date': date.today() + timedelta(days=365),
            'batch_number': 'TEST001'
        }
    )
    
    if not created:
        bulk_inventory.stock_quantity = 100
        bulk_inventory.save()
    
    # Create test dispensary and active store
    dispensary, created = Dispensary.objects.get_or_create(
        name='Test Dispensary',
        defaults={
            'location': 'Test Dispensary Location',
            'is_active': True
        }
    )
    
    active_store, created = ActiveStore.objects.get_or_create(
        dispensary=dispensary,
        defaults={
            'is_active': True
        }
    )
    
    print(f"✓ Created test data:")
    print(f"  - User: {user.username}")
    print(f"  - Medication: {medication.name} (Stock: {bulk_inventory.stock_quantity})")
    print(f"  - Bulk Store: {bulk_store.name}")
    print(f"  - Dispensary: {dispensary.name}")
    
    # Test client
    client = Client()
    client.force_login(user)
    
    # Test accessing bulk store dashboard
    response = client.get('/pharmacy/bulk-store/')
    if response.status_code == 200:
        print("✓ Bulk store dashboard accessible")
    else:
        print(f"✗ Bulk store dashboard returned status {response.status_code}")
    
    # Test instant transfer form submission
    transfer_data = {
        'medication': medication.id,
        'active_store': active_store.id,
        'quantity': 10,
        'notes': 'Test instant transfer',
        'csrfmiddlewaretoken': 'test'
    }
    
    # Get CSRF token first
    response = client.get('/pharmacy/bulk-store/')
    if hasattr(response, 'cookies'):
        csrf_token = response.cookies.get('csrftoken')
        if csrf_token:
            transfer_data['csrfmiddlewaretoken'] = csrf_token.value
    
    print("\nTesting instant transfer endpoint...")
    response = client.post('/pharmacy/bulk-store/transfer/instant/', transfer_data)
    
    if response.status_code == 302:  # Redirect after successful transfer
        print("✓ Instant transfer successful (redirect received)")
        
        # Check if inventory was updated
        bulk_inventory.refresh_from_db()
        print(f"  - Bulk store inventory after transfer: {bulk_inventory.stock_quantity}")
        
        # Check active store inventory
        try:
            active_inventory = ActiveStoreInventory.objects.get(
                medication=medication,
                active_store=active_store
            )
            print(f"  - Active store inventory after transfer: {active_inventory.stock_quantity}")
            
            if bulk_inventory.stock_quantity == 90 and active_inventory.stock_quantity == 10:
                print("✓ Transfer correctly updated inventory quantities")
            else:
                print("✗ Inventory quantities not updated correctly")
                
        except ActiveStoreInventory.DoesNotExist:
            print("✗ Active store inventory not created after transfer")
            
        # Check transfer record
        from pharmacy.models import MedicationTransfer
        transfer = MedicationTransfer.objects.filter(
            medication=medication,
            from_bulk_store=bulk_store,
            to_active_store=active_store,
            status='completed'
        ).first()
        
        if transfer:
            print(f"✓ Transfer record created: #{transfer.id}")
            print(f"  - Status: {transfer.status}")
            print(f"  - Quantity: {transfer.quantity}")
        else:
            print("✗ Transfer record not found")
            
    else:
        print(f"✗ Instant transfer failed with status {response.status_code}")
        if hasattr(response, 'content'):
            print(f"  Response: {response.content.decode()[:200]}...")
    
    print("\nInstant transfer test completed!")

if __name__ == '__main__':
    test_instant_transfer()
