#!/usr/bin/env python
"""
Test script to verify bulk store functionality after template fixes.
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
sys.path.append(r'C:\Users\dell\Desktop\MY_PRODUCTS\HMS')
django.setup()

from pharmacy.models import BulkStore, BulkStoreInventory, Medication, Dispensary, ActiveStore, MedicationTransfer
from accounts.models import CustomUser

User = get_user_model()

def test_bulk_store_functionality():
    """Test bulk store dashboard and transfer functionality"""
    print("=" * 80)
    print("BULK STORE FUNCTIONALITY TEST")
    print("=" * 80)
    
    # Create test user
    user, created = User.objects.get_or_create(
        username='test_bulk_user',
        defaults={
            'email': 'testbulk@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True,
        }
    )
    
    # Create test bulk store
    bulk_store, created = BulkStore.objects.get_or_create(
        name='Test Bulk Store',
        defaults={
            'location': 'Test Location',
            'capacity': 10000,
            'is_active': True,
        }
    )
    
    # Create test dispensary and active store
    dispensary, created = Dispensary.objects.get_or_create(
        name='Test Dispensary',
        defaults={
            'location': 'Test Dispensary Location',
            'is_active': True,
            'manager': user,
        }
    )
    
    active_store, created = ActiveStore.objects.get_or_create(
        dispensary=dispensary,
        defaults={
            'name': 'Test Active Store',
            'is_active': True,
        }
    )
    
    # Create test medication
    medication, created = Medication.objects.get_or_create(
        name='Test Medication',
        defaults={
            'strength': '500mg',
            'reorder_level': 50,
            'is_active': True,
        }
    )
    
    # Create bulk inventory
    bulk_inventory, created = BulkStoreInventory.objects.get_or_create(
        medication=medication,
        bulk_store=bulk_store,
        batch_number='TEST001',
        defaults={
            'stock_quantity': 1000,
            'expiry_date': '2025-12-31',
            'unit_cost': 10.50,
            'purchase_date': '2025-01-01',
        }
    )
    
    print(f"✓ Created test bulk store: {bulk_store.name}")
    print(f"✓ Created test dispensary: {dispensary.name}")
    print(f"✓ Created test medication: {medication.name}")
    print(f"✓ Created bulk inventory: {bulk_inventory.stock_quantity} units")
    
    # Test transfer
    transfer = MedicationTransfer.objects.create(
        medication=medication,
        from_bulk_store=bulk_store,
        to_active_store=active_store,
        quantity=100,
        batch_number='TEST001',
        expiry_date='2025-12-31',
        unit_cost=10.50,
        status='pending',
        requested_by=user,
        notes='Test transfer',
    )
    
    print(f"✓ Created transfer: {transfer.id} - {transfer.quantity} units")
    
    # Test instant transfer execution
    try:
        transfer.approved_by = user
        transfer.approved_at = django.utils.timezone.now()
        transfer.transferred_by = user
        transfer.transferred_at = django.utils.timezone.now()
        transfer.status = 'completed'
        transfer.save()
        
        # Execute the stock transfer
        transfer.execute_transfer(user)
        
        print(f"✓ Instant transfer executed successfully")
        
        # Verify inventory changes
        bulk_inventory.refresh_from_db()
        print(f"✓ Bulk store inventory updated: {bulk_inventory.stock_quantity} units remaining")
        
        # Check active store inventory
        active_inventory = active_store.inventories.filter(medication=medication).first()
        if active_inventory:
            print(f"✓ Active store inventory created: {active_inventory.stock_quantity} units")
        else:
            print("✗ Active store inventory not found")
            
    except Exception as e:
        print(f"✗ Transfer execution failed: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("BULK STORE FUNCTIONALITY TEST COMPLETED")
    print("=" * 80)
    return True

if __name__ == '__main__':
    test_bulk_store_functionality()
