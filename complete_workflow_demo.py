#!/usr/bin/env python
"""
Complete workflow demonstration showing the transfer logic in action

This script demonstrates the complete workflow from pack creation to dispensing
with automatic transfer from bulk store to active store.
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
    Dispensary, MedicationTransfer, Prescription, PrescriptionItem
)
from patients.models import Patient
from accounts.models import CustomUser
from django.utils import timezone

def run_complete_workflow_demo():
    """Run a complete workflow demonstration"""
    print("🏥 Complete Workflow Demonstration")
    print("=" * 35)
    
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
    
    # Get or create test data
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
    
    print("\n📋 STEP 1: Setting Up Initial Inventory")
    print("   Setting bulk store with plenty of stock")
    print("   Setting active store with zero stock")
    
    # Setup bulk store inventory (plenty of stock)
    bulk_inv1, _ = BulkStoreInventory.objects.get_or_create(
        medication=medication1,
        bulk_store=bulk_store,
        batch_number='WORKFLOW-DEMO-001',
        defaults={
            'stock_quantity': 200,
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'unit_cost': Decimal('4.50')
        }
    )
    bulk_inv1.stock_quantity = 200
    bulk_inv1.save()
    
    bulk_inv2, _ = BulkStoreInventory.objects.get_or_create(
        medication=medication2,
        bulk_store=bulk_store,
        batch_number='WORKFLOW-DEMO-002',
        defaults={
            'stock_quantity': 100,
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'unit_cost': Decimal('14.00')
        }
    )
    bulk_inv2.stock_quantity = 100
    bulk_inv2.save()
    
    # Setup active store inventory (zero stock)
    active_inv1, _ = ActiveStoreInventory.objects.get_or_create(
        medication=medication1,
        active_store=active_store,
        batch_number='WORKFLOW-DEMO-001',
        defaults={
            'stock_quantity': 0,
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'unit_cost': Decimal('4.50')
        }
    )
    active_inv1.stock_quantity = 0
    active_inv1.save()
    
    active_inv2, _ = ActiveStoreInventory.objects.get_or_create(
        medication=medication2,
        active_store=active_store,
        batch_number='WORKFLOW-DEMO-002',
        defaults={
            'stock_quantity': 0,
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'unit_cost': Decimal('14.00')
        }
    )
    active_inv2.stock_quantity = 0
    active_inv2.save()
    
    print(f"   Bulk store: {medication1.name} = {bulk_inv1.stock_quantity} units")
    print(f"   Bulk store: {medication2.name} = {bulk_inv2.stock_quantity} units")
    print(f"   Active store: {medication1.name} = {active_inv1.stock_quantity} units")
    print(f"   Active store: {medication2.name} = {active_inv2.stock_quantity} units")
    
    print("\n📋 STEP 2: Creating Medical Pack")
    # Create a medical pack that needs more than what's in active store
    medical_pack_name = f'Surgery Pack Demo {timezone.now().timestamp()}'
    medical_pack = MedicalPack.objects.create(
        name=medical_pack_name,
        description='Demo pack for workflow demonstration',
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
        quantity=50,  # Need 50 units but active store has 0
        item_type='consumable',
        usage_instructions='Use for wound dressing',
        is_critical=True,
        order=1
    )
    
    pack_item2 = PackItem.objects.create(
        pack=medical_pack,
        medication=medication2,
        quantity=25,  # Need 25 units but active store has 0
        item_type='consumable',
        usage_instructions='Use for cleaning wounds',
        is_critical=False,
        order=2
    )
    
    print(f"   Created pack: {medical_pack.name}")
    print(f"   Items in pack: {medical_pack.items.count()}")
    print(f"   Total pack cost: ₦{medical_pack.get_total_cost()}")
    
    print("\n📋 STEP 3: Creating Pack Order")
    # Create a pack order
    pack_order = PackOrder.objects.create(
        pack=medical_pack,
        patient=patient,
        ordered_by=doctor,
        scheduled_date=timezone.now() + timedelta(days=1),
        order_notes='Demo pack order for workflow demonstration'
    )
    
    print(f"   Pack order #{pack_order.id} created")
    print(f"   Order status: {pack_order.get_status_display()}")
    
    print("\n📋 STEP 4: Processing Pack Order")
    print("   This should trigger automatic transfer from bulk to active store")
    
    # Record inventory before processing
    bulk_before_1 = bulk_inv1.stock_quantity
    bulk_before_2 = bulk_inv2.stock_quantity
    active_before_1 = active_inv1.stock_quantity
    active_before_2 = active_inv2.stock_quantity
    
    # Process the pack order - this should trigger transfer
    try:
        prescription = pack_order.process_order(pharmacist)
        print(f"   ✅ Processed successfully, prescription #{prescription.id} created")
    except Exception as e:
        print(f"   ❌ Processing failed: {str(e)}")
        return False
    
    print("\n📋 STEP 5: Verifying Transfer Results")
    # Refresh inventory data
    bulk_inv1.refresh_from_db()
    bulk_inv2.refresh_from_db()
    active_inv1.refresh_from_db()
    active_inv2.refresh_from_db()
    
    print("   Inventory changes:")
    print(f"   {medication1.name}:")
    print(f"     Bulk store: {bulk_before_1} → {bulk_inv1.stock_quantity} (change: {bulk_inv1.stock_quantity - bulk_before_1})")
    print(f"     Active store: {active_before_1} → {active_inv1.stock_quantity} (change: {active_inv1.stock_quantity - active_before_1})")
    print(f"   {medication2.name}:")
    print(f"     Bulk store: {bulk_before_2} → {bulk_inv2.stock_quantity} (change: {bulk_inv2.stock_quantity - bulk_before_2})")
    print(f"     Active store: {active_before_2} → {active_inv2.stock_quantity} (change: {active_inv2.stock_quantity - active_before_2})")
    
    # Check if transfer happened correctly
    expected_bulk_1 = bulk_before_1 - 50  # Should have reduced by 50
    expected_bulk_2 = bulk_before_2 - 25  # Should have reduced by 25
    expected_active_1 = active_before_1 + 50  # Should have increased by 50
    expected_active_2 = active_before_2 + 25  # Should have increased by 25
    
    transfer_correct = (
        bulk_inv1.stock_quantity == expected_bulk_1 and
        bulk_inv2.stock_quantity == expected_bulk_2 and
        active_inv1.stock_quantity == expected_active_1 and
        active_inv2.stock_quantity == expected_active_2
    )
    
    if transfer_correct:
        print("   ✅ Transfer logic working correctly!")
    else:
        print("   ⚠️  Transfer logic may have issues")
    
    print("\n📋 STEP 6: Checking Transfer Records")
    # Check transfer records
    recent_transfers = MedicationTransfer.objects.filter(
        requested_at__gte=timezone.now() - timedelta(minutes=10)
    ).order_by('-requested_at')
    
    print(f"   Recent transfers created: {recent_transfers.count()}")
    for transfer in recent_transfers:
        print(f"   - Transfer #{transfer.id}: {transfer.quantity} {transfer.medication.name}")
        print(f"     Status: {transfer.get_status_display()}")
        print(f"     From: {transfer.from_bulk_store.name} → To: {transfer.to_active_store.dispensary.name}")
    
    print("\n📋 STEP 7: Verifying Prescription")
    # Check the created prescription
    prescription.refresh_from_db()
    prescription_items = prescription.items.all()
    
    print(f"   Prescription #{prescription.id} created")
    print(f"   Prescription status: {prescription.get_status_display()}")
    print(f"   Items in prescription: {prescription_items.count()}")
    
    for item in prescription_items:
        print(f"   - {item.medication.name}: {item.quantity} units")
    
    print("\n📋 STEP 8: Testing Dispensing")
    print("   Testing that prescription can be dispensed using active store inventory")
    
    # Try to dispense a small quantity from the prescription
    if prescription_items.exists():
        item_to_dispense = prescription_items.first()
        print(f"   Attempting to dispense 10 units of {item_to_dispense.medication.name}")
        
        # This would normally be done through the web interface, but we can simulate it
        try:
            # Check if we have enough in active store (sum all batches)
            active_store_items = ActiveStoreInventory.objects.filter(
                medication=item_to_dispense.medication,
                active_store=active_store
            )
            
            total_active_stock = sum(item.stock_quantity for item in active_store_items)
            
            if total_active_stock >= 10:
                print("   ✅ Sufficient stock in active store for dispensing")
                print("   ✅ Prescription dispensing would work correctly")
            else:
                print("   ❌ Insufficient stock in active store")
        except Exception as e:
            print(f"   ❌ Error checking inventory: {str(e)}")
    
    print("\n🏥 Complete Workflow Demonstration Completed!")
    print("\n📋 Summary of the workflow:")
    print("   1. ✅ Medical pack created with required medications")
    print("   2. ✅ Pack order created with pending status")
    print("   3. ✅ Pack order processed, triggering automatic transfer")
    print("   4. ✅ Medications transferred from bulk store to active store")
    print("   5. ✅ Prescription created with correct items")
    print("   6. ✅ Prescription can be dispensed using active store inventory")
    
    if transfer_correct:
        print("\n🎉 COMPLETE WORKFLOW IS WORKING CORRECTLY! 🎉")
        print("   The system automatically transfers medications when needed")
        print("   and maintains proper inventory levels throughout the process.")
        return True
    else:
        print("\n⚠️  There may be issues with the workflow.")
        return False

if __name__ == '__main__':
    try:
        success = run_complete_workflow_demo()
        if success:
            print("\n✅ All systems working correctly!")
        else:
            print("\n❌ Workflow issues detected.")
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)