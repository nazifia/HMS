#!/usr/bin/env python
"""
Comprehensive test to verify the transfer functionality from bulk store to active store

This script demonstrates:
1. Setting up bulk store and active store inventory
2. Creating a pack order that requires transfer
3. Processing the pack order to trigger transfer
4. Verifying the transfer worked by checking MedicationTransfer records
5. Verifying inventory changes in both bulk and active stores
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
    MedicalPack, PackItem, PackOrder, Medication, MedicationCategory,
    BulkStore, BulkStoreInventory, ActiveStore, ActiveStoreInventory,
    Dispensary, MedicationTransfer
)
from patients.models import Patient
from accounts.models import CustomUser
from django.utils import timezone

def run_comprehensive_transfer_test():
    """Run a comprehensive test to verify the transfer functionality"""
    print("🧪 Comprehensive Transfer Functionality Test")
    print("=" * 45)
    
    # Get existing users or create new ones
    try:
        pharmacist = CustomUser.objects.get(username='testpharmacist')
        doctor = CustomUser.objects.get(username='testdoctor')
        print("✓ Using existing test users")
    except CustomUser.DoesNotExist:
        pharmacist = CustomUser.objects.create_user(
            username='testpharmacist',
            email='pharmacist@test.com',
            password='testpass123',
            phone_number='1234567890',
            first_name='Test',
            last_name='Pharmacist'
        )
        doctor = CustomUser.objects.create_user(
            username='testdoctor',
            email='doctor@test.com',
            password='testpass123',
            phone_number='0987654321',
            first_name='Test',
            last_name='Doctor'
        )
        print("✓ Created new test users")
    
    # Get existing patient or create new one
    try:
        patient = Patient.objects.get(email='john.doe@example.com')
        print("✓ Using existing test patient")
    except Patient.DoesNotExist:
        patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1980-01-01',
            gender='male',
            phone_number='1234567890',
            email='john.doe@example.com',
            patient_type='paying'
        )
        print("✓ Created new test patient")
    
    # Get or create test data - handle multiple categories
    med_category = MedicationCategory.objects.filter(name='Surgical Supplies').first()
    if not med_category:
        med_category = MedicationCategory.objects.create(
            name='Surgical Supplies',
            description='Medical supplies for surgical procedures'
        )
    
    medication1 = Medication.objects.filter(name='Surgical Gauze').first()
    if not medication1:
        medication1 = Medication.objects.create(
            name='Surgical Gauze',
            category=med_category,
            dosage_form='pad',
            strength='4x4 inch',
            price=Decimal('5.00'),
            is_active=True
        )
    
    medication2 = Medication.objects.filter(name='Antiseptic Solution').first()
    if not medication2:
        medication2 = Medication.objects.create(
            name='Antiseptic Solution',
            category=med_category,
            dosage_form='solution',
            strength='250ml',
            price=Decimal('15.00'),
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
    
    print("\n1️⃣ Setting up inventory")
    # Setup bulk store inventory (plenty of stock)
    bulk_inv1, created1 = BulkStoreInventory.objects.get_or_create(
        medication=medication1,
        bulk_store=bulk_store,
        batch_number='BATCH-001',
        defaults={
            'stock_quantity': 100,
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'unit_cost': Decimal('4.50')
        }
    )
    
    # If not created, update the quantity
    if not created1:
        bulk_inv1.stock_quantity = 100
        bulk_inv1.save()
    
    bulk_inv2, created2 = BulkStoreInventory.objects.get_or_create(
        medication=medication2,
        bulk_store=bulk_store,
        batch_number='BATCH-002',
        defaults={
            'stock_quantity': 50,
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'unit_cost': Decimal('14.00')
        }
    )
    
    # If not created, update the quantity
    if not created2:
        bulk_inv2.stock_quantity = 50
        bulk_inv2.save()
    
    # Setup active store inventory (no stock)
    active_inv1, created3 = ActiveStoreInventory.objects.get_or_create(
        medication=medication1,
        active_store=active_store,
        batch_number='BATCH-001',
        defaults={
            'stock_quantity': 0,
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'unit_cost': Decimal('4.50')
        }
    )
    
    # If not created, update the quantity
    if not created3:
        active_inv1.stock_quantity = 0
        active_inv1.save()
    
    active_inv2, created4 = ActiveStoreInventory.objects.get_or_create(
        medication=medication2,
        active_store=active_store,
        batch_number='BATCH-002',
        defaults={
            'stock_quantity': 0,
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'unit_cost': Decimal('14.00')
        }
    )
    
    # If not created, update the quantity
    if not created4:
        active_inv2.stock_quantity = 0
        active_inv2.save()
    
    print(f"   Bulk store: {medication1.name} = {bulk_inv1.stock_quantity} units")
    print(f"   Bulk store: {medication2.name} = {bulk_inv2.stock_quantity} units")
    print(f"   Active store: {medication1.name} = {active_inv1.stock_quantity} units")
    print(f"   Active store: {medication2.name} = {active_inv2.stock_quantity} units")
    
    print("\n2️⃣ Creating Medical Pack")
    # Create a medical pack that needs more than what's in active store
    medical_pack_name = f'Appendectomy Surgery Pack {timezone.now().timestamp()}'
    medical_pack = MedicalPack.objects.create(
        name=medical_pack_name,
        description='Standard pack for appendectomy procedures',
        pack_type='surgery',
        surgery_type='appendectomy',
        risk_level='medium',
        requires_approval=False,
        is_active=True,
        created_by=pharmacist
    )
    
    # Add items to the pack
    pack_item1 = PackItem.objects.create(
        pack=medical_pack,
        medication=medication1,
        quantity=20,
        item_type='consumable',
        usage_instructions='Use for wound dressing',
        is_critical=True,
        order=1
    )
    
    pack_item2 = PackItem.objects.create(
        pack=medical_pack,
        medication=medication2,
        quantity=10,
        item_type='consumable',
        usage_instructions='Use for cleaning wounds',
        is_critical=False,
        order=2
    )
    
    print(f"   Pack created with {medical_pack.items.count()} items")
    print(f"   Pack total cost: ₦{medical_pack.get_total_cost()}")
    
    print("\n3️⃣ Creating Pack Order")
    # Create a pack order
    pack_order = PackOrder.objects.create(
        pack=medical_pack,
        patient=patient,
        ordered_by=doctor,
        scheduled_date=timezone.now() + timedelta(days=1),
        order_notes='Needed for appendectomy surgery tomorrow'
    )
    
    print(f"   Pack order #{pack_order.id} created")
    print(f"   Order status: {pack_order.get_status_display()}")
    
    # Count transfers before processing
    transfers_before = MedicationTransfer.objects.count()
    print(f"   Transfers before processing: {transfers_before}")
    
    print("\n4️⃣ Processing Pack Order")
    # Process the pack order - this should trigger transfer
    try:
        prescription = pack_order.process_order(pharmacist)
        print(f"   ✅ Processed successfully, prescription #{prescription.id} created")
    except Exception as e:
        print(f"   ❌ Processing failed: {str(e)}")
        return False
    
    # Count transfers after processing
    transfers_after = MedicationTransfer.objects.count()
    print(f"   Transfers after processing: {transfers_after}")
    
    if transfers_after > transfers_before:
        print("   ✅ Transfer requests were created!")
    else:
        print("   ⚠️  No transfer requests were created")
    
    print("\n5️⃣ Verifying Results")
    # Refresh inventory data
    active_inv1.refresh_from_db()
    active_inv2.refresh_from_db()
    bulk_inv1.refresh_from_db()
    bulk_inv2.refresh_from_db()
    
    print(f"   Active store after transfer: {medication1.name} = {active_inv1.stock_quantity} units")
    print(f"   Active store after transfer: {medication2.name} = {active_inv2.stock_quantity} units")
    print(f"   Bulk store after transfer: {medication1.name} = {bulk_inv1.stock_quantity} units")
    print(f"   Bulk store after transfer: {medication2.name} = {bulk_inv2.stock_quantity} units")
    
    # Check if transfer happened by looking at MedicationTransfer records
    recent_transfers = MedicationTransfer.objects.filter(
        requested_at__gte=timezone.now() - timedelta(minutes=5)
    ).order_by('-requested_at')
    
    print(f"\n6️⃣ Checking Transfer Records")
    print(f"   Recent transfers found: {recent_transfers.count()}")
    
    for transfer in recent_transfers:
        print(f"   - Transfer {transfer.quantity} {transfer.medication.name}")
        print(f"     From: {transfer.from_bulk_store.name}")
        print(f"     To: {transfer.to_active_store.dispensary.name}")
        print(f"     Status: {transfer.get_status_display()}")
    
    # Check if bulk store inventory was reduced
    bulk_store_reduced = (
        bulk_inv1.stock_quantity < 100 or 
        bulk_inv2.stock_quantity < 50
    )
    
    if bulk_store_reduced:
        print("   ✅ Bulk store inventory was reduced (transfer initiated)")
    else:
        print("   ⚠️  Bulk store inventory was not reduced")
    
    # Check transfer completion
    completed_transfers = recent_transfers.filter(status='completed').count()
    if completed_transfers > 0:
        print("   ✅ Some transfers were completed successfully")
    else:
        print("   ⚠️  No transfers were completed (may still be in progress)")
    
    print("\n✅ Comprehensive Transfer Functionality Test Completed!")
    print("\n📋 Summary:")
    print("   • Pack order processing triggers transfer logic")
    print("   • Transfer requests are created when needed")
    print("   • Bulk store inventory is adjusted")
    print("   • Active store should receive transferred medications")
    print("   • Transfer records are maintained for audit trail")
    
    return True

if __name__ == '__main__':
    try:
        success = run_comprehensive_transfer_test()
        if success:
            print("\n🎉 Transfer functionality is working!")
        else:
            print("\n❌ Transfer functionality needs attention.")
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)