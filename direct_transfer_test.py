#!/usr/bin/env python
"""
Direct test of the MedicationTransfer functionality

This script tests the MedicationTransfer.execute_transfer method directly
to verify that it correctly moves medications from bulk store to active store.
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import (
    Medication, MedicationCategory,
    BulkStore, BulkStoreInventory, ActiveStore, ActiveStoreInventory,
    Dispensary, MedicationTransfer
)
from accounts.models import CustomUser
from django.utils import timezone

def run_direct_transfer_test():
    """Run a direct test of the MedicationTransfer functionality"""
    print("🧪 Direct MedicationTransfer Test")
    print("=" * 35)
    
    # Get existing users or create new ones
    try:
        pharmacist = CustomUser.objects.get(username='testpharmacist')
        print("✓ Using existing test pharmacist")
    except CustomUser.DoesNotExist:
        pharmacist = CustomUser.objects.create_user(
            username='testpharmacist',
            email='pharmacist@test.com',
            password='testpass123',
            phone_number='1234567890',
            first_name='Test',
            last_name='Pharmacist'
        )
        print("✓ Created new test pharmacist")
    
    # Get or create test data
    med_category = MedicationCategory.objects.filter(name='Surgical Supplies').first()
    if not med_category:
        med_category = MedicationCategory.objects.create(
            name='Surgical Supplies',
            description='Medical supplies for surgical procedures'
        )
    
    medication = Medication.objects.filter(name='Surgical Gauze').first()
    if not medication:
        medication = Medication.objects.create(
            name='Surgical Gauze',
            category=med_category,
            dosage_form='pad',
            strength='4x4 inch',
            price=Decimal('5.00'),
            is_active=True
        )
    
    bulk_store = BulkStore.objects.filter(name='Main Bulk Store').first()
    if not bulk_store:
        bulk_store = BulkStore.objects.create(
            name='Main Bulk Store',
            location='Central Storage Area',
            description='Main bulk storage for all procured medications',
            capacity=50000,
            temperature_controlled=True,
            humidity_controlled=True,
            security_level='high',
            is_active=True
        )
    
    dispensary = Dispensary.objects.filter(name='Main Pharmacy').first()
    if not dispensary:
        dispensary = Dispensary.objects.create(
            name='Main Pharmacy',
            location='Ground Floor',
            description='Main hospital pharmacy',
            is_active=True,
            manager=pharmacist
        )
    
    active_store = ActiveStore.objects.filter(dispensary=dispensary).first()
    if not active_store:
        active_store = ActiveStore.objects.create(
            dispensary=dispensary,
            name=f'Active Store - {dispensary.name}',
            capacity=1000
        )
    
    print("\n1️⃣ Setting up initial inventory")
    # Setup bulk store inventory
    bulk_inventory, created1 = BulkStoreInventory.objects.get_or_create(
        medication=medication,
        bulk_store=bulk_store,
        batch_number='DIRECT-TEST-001',
        defaults={
            'stock_quantity': 100,
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'unit_cost': Decimal('4.50')
        }
    )
    
    # If not created, update the quantity
    if not created1:
        bulk_inventory.stock_quantity = 100
        bulk_inventory.save()
    
    # Setup active store inventory
    active_inventory, created2 = ActiveStoreInventory.objects.get_or_create(
        medication=medication,
        active_store=active_store,
        batch_number='DIRECT-TEST-001',
        defaults={
            'stock_quantity': 10,
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'unit_cost': Decimal('4.50')
        }
    )
    
    # If not created, update the quantity
    if not created2:
        active_inventory.stock_quantity = 10
        active_inventory.save()
    
    print(f"   Bulk store inventory: {bulk_inventory.stock_quantity} units")
    print(f"   Active store inventory: {active_inventory.stock_quantity} units")
    
    print("\n2️⃣ Creating Transfer Request")
    # Create a transfer request
    transfer = MedicationTransfer.objects.create(
        medication=medication,
        from_bulk_store=bulk_store,
        to_active_store=active_store,
        quantity=30,
        batch_number=bulk_inventory.batch_number,
        expiry_date=bulk_inventory.expiry_date,
        unit_cost=bulk_inventory.unit_cost,
        status='pending',
        requested_by=pharmacist
    )
    
    print(f"   Transfer request #{transfer.id} created")
    print(f"   Requested quantity: {transfer.quantity} units")
    print(f"   Status: {transfer.get_status_display()}")
    
    print("\n3️⃣ Approving Transfer")
    # Approve the transfer
    transfer.approved_by = pharmacist
    transfer.approved_at = timezone.now()
    transfer.status = 'in_transit'
    transfer.save()
    
    print(f"   Transfer approved")
    print(f"   Status: {transfer.get_status_display()}")
    
    print("\n4️⃣ Executing Transfer")
    # Execute the transfer
    try:
        transfer.execute_transfer(pharmacist)
        print(f"   ✅ Transfer executed successfully")
    except Exception as e:
        print(f"   ❌ Transfer execution failed: {str(e)}")
        return False
    
    print(f"   Status: {transfer.get_status_display()}")
    
    print("\n5️⃣ Verifying Results")
    # Refresh inventory data
    bulk_inventory.refresh_from_db()
    active_inventory.refresh_from_db()
    
    print(f"   Bulk store inventory after transfer: {bulk_inventory.stock_quantity} units")
    print(f"   Active store inventory after transfer: {active_inventory.stock_quantity} units")
    
    # Expected results:
    # Bulk store: 100 - 30 = 70
    # Active store: 10 + 30 = 40
    
    expected_bulk = 70
    expected_active = 40
    
    if bulk_inventory.stock_quantity == expected_bulk:
        print("   ✅ Bulk store inventory correctly reduced")
    else:
        print(f"   ❌ Bulk store inventory incorrect. Expected: {expected_bulk}, Got: {bulk_inventory.stock_quantity}")
    
    if active_inventory.stock_quantity == expected_active:
        print("   ✅ Active store inventory correctly increased")
    else:
        print(f"   ❌ Active store inventory incorrect. Expected: {expected_active}, Got: {active_inventory.stock_quantity}")
    
    # Check if both conditions are met
    if bulk_inventory.stock_quantity == expected_bulk and active_inventory.stock_quantity == expected_active:
        print("\n✅ Direct MedicationTransfer Test Passed!")
        print("   The transfer functionality is working correctly.")
        return True
    else:
        print("\n❌ Direct MedicationTransfer Test Failed!")
        print("   There are issues with the transfer functionality.")
        return False

if __name__ == '__main__':
    try:
        success = run_direct_transfer_test()
        if success:
            print("\n🎉 MedicationTransfer functionality is working correctly!")
        else:
            print("\n❌ MedicationTransfer functionality has issues.")
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)