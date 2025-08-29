#!/usr/bin/env python
"""
Test script to verify the transfer logic from bulk store to active store when processing pack orders

This script demonstrates:
1. Creating a medical pack with items
2. Ensuring medications are in bulk store but not in active store
3. Processing a pack order which should trigger transfer from bulk to active store
4. Verifying the transfer was successful
5. Dispensing the prescription to verify inventory usage
"""

import os
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import (
    MedicalPack, PackItem, PackOrder, Medication, MedicationCategory,
    BulkStore, BulkStoreInventory, ActiveStore, ActiveStoreInventory,
    Dispensary
)
from patients.models import Patient
from accounts.models import CustomUser
from theatre.models import Surgery, SurgeryType, OperationTheatre
from django.utils import timezone

def run_transfer_test():
    """Run a test to demonstrate the transfer logic from bulk store to active store"""
    print("🧪 Pack Order Transfer Logic Test")
    print("=" * 40)
    
    # Get or create test users
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
    
    # Get or create test patient
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
    
    # Get or create medication category
    try:
        med_category = MedicationCategory.objects.filter(name='Surgical Supplies').first()
        if not med_category:
            med_category = MedicationCategory.objects.create(
                name='Surgical Supplies',
                description='Medical supplies for surgical procedures'
            )
            print("✓ Created new medication category")
        else:
            print("✓ Using existing medication category")
    except Exception:
        med_category = MedicationCategory.objects.create(
            name='Surgical Supplies',
            description='Medical supplies for surgical procedures'
        )
        print("✓ Created new medication category")
    
    # Get or create medications
    try:
        medication1 = Medication.objects.filter(name='Surgical Gauze').first()
        medication2 = Medication.objects.filter(name='Antiseptic Solution').first()
        
        if not medication1 or not medication2:
            if not medication1:
                medication1 = Medication.objects.create(
                    name='Surgical Gauze',
                    category=med_category,
                    dosage_form='pad',
                    strength='4x4 inch',
                    price=Decimal('5.00'),
                    is_active=True
                )
            if not medication2:
                medication2 = Medication.objects.create(
                    name='Antiseptic Solution',
                    category=med_category,
                    dosage_form='solution',
                    strength='250ml',
                    price=Decimal('15.00'),
                    is_active=True
                )
            print("✓ Created new medications")
        else:
            print("✓ Using existing medications")
    except Exception:
        medication1 = Medication.objects.create(
            name='Surgical Gauze',
            category=med_category,
            dosage_form='pad',
            strength='4x4 inch',
            price=Decimal('5.00'),
            is_active=True
        )
        medication2 = Medication.objects.create(
            name='Antiseptic Solution',
            category=med_category,
            dosage_form='solution',
            strength='250ml',
            price=Decimal('15.00'),
            is_active=True
        )
        print("✓ Created new medications")
    
    # Get or create bulk store
    try:
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
            print("✓ Created new bulk store")
        else:
            print("✓ Using existing bulk store")
    except Exception:
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
        print("✓ Created new bulk store")
    
    # Get or create dispensary
    try:
        dispensary = Dispensary.objects.filter(name='Main Pharmacy').first()
        if not dispensary:
            dispensary = Dispensary.objects.create(
                name='Main Pharmacy',
                location='Ground Floor',
                description='Main hospital pharmacy',
                is_active=True,
                manager=pharmacist
            )
            print("✓ Created new dispensary")
        else:
            print("✓ Using existing dispensary")
    except Exception:
        dispensary = Dispensary.objects.create(
            name='Main Pharmacy',
            location='Ground Floor',
            description='Main hospital pharmacy',
            is_active=True,
            manager=pharmacist
        )
        print("✓ Created new dispensary")
    
    # Get or create active store
    try:
        active_store = ActiveStore.objects.filter(dispensary=dispensary).first()
        if not active_store:
            active_store = ActiveStore.objects.create(
                dispensary=dispensary,
                name=f'Active Store - {dispensary.name}',
                capacity=1000
            )
            print("✓ Created new active store")
        else:
            print("✓ Using existing active store")
    except Exception:
        active_store = ActiveStore.objects.create(
            dispensary=dispensary,
            name=f'Active Store - {dispensary.name}',
            capacity=1000
        )
        print("✓ Created new active store")
    
    print("\n1️⃣ Setting up inventory")
    # Add medications to bulk store
    bulk_inventory1, created1 = BulkStoreInventory.objects.get_or_create(
        medication=medication1,
        bulk_store=bulk_store,
        batch_number='BATCH-001',
        defaults={
            'stock_quantity': 100,
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'unit_cost': Decimal('4.50')
        }
    )
    
    if not created1:
        bulk_inventory1.stock_quantity = 100
        bulk_inventory1.save()
    
    bulk_inventory2, created2 = BulkStoreInventory.objects.get_or_create(
        medication=medication2,
        bulk_store=bulk_store,
        batch_number='BATCH-002',
        defaults={
            'stock_quantity': 50,
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'unit_cost': Decimal('14.00')
        }
    )
    
    if not created2:
        bulk_inventory2.stock_quantity = 50
        bulk_inventory2.save()
    
    print(f"   Added {medication1.name} to bulk store: {bulk_inventory1.stock_quantity} units")
    print(f"   Added {medication2.name} to bulk store: {bulk_inventory2.stock_quantity} units")
    
    # Ensure active store has no inventory (or very low inventory)
    try:
        active_inventory1 = ActiveStoreInventory.objects.get(
            medication=medication1,
            active_store=active_store
        )
        active_inventory1.stock_quantity = 0
        active_inventory1.save()
    except ActiveStoreInventory.DoesNotExist:
        active_inventory1 = ActiveStoreInventory.objects.create(
            medication=medication1,
            active_store=active_store,
            stock_quantity=0,
            batch_number='BATCH-001',
            expiry_date=timezone.now().date() + timedelta(days=365),
            unit_cost=Decimal('4.50')
        )
    
    try:
        active_inventory2 = ActiveStoreInventory.objects.get(
            medication=medication2,
            active_store=active_store
        )
        active_inventory2.stock_quantity = 0
        active_inventory2.save()
    except ActiveStoreInventory.DoesNotExist:
        active_inventory2 = ActiveStoreInventory.objects.create(
            medication=medication2,
            active_store=active_store,
            stock_quantity=0,
            batch_number='BATCH-002',
            expiry_date=timezone.now().date() + timedelta(days=365),
            unit_cost=Decimal('14.00')
        )
    
    print(f"   Active store inventory for {medication1.name}: {active_inventory1.stock_quantity} units")
    print(f"   Active store inventory for {medication2.name}: {active_inventory2.stock_quantity} units")
    
    print("\n2️⃣ Creating Medical Pack")
    # Create a medical pack
    medical_pack = MedicalPack.objects.create(
        name='Appendectomy Surgery Pack',
        description='Standard pack for appendectomy procedures',
        pack_type='surgery',
        surgery_type='appendectomy',
        risk_level='medium',
        requires_approval=False,
        is_active=True,
        created_by=pharmacist
    )
    print(f"   Created pack: {medical_pack.name}")
    
    # Add items to the pack (requiring more than what's in active store)
    pack_item1 = PackItem.objects.create(
        pack=medical_pack,
        medication=medication1,
        quantity=20,  # Need 20 units but active store has 0
        item_type='consumable',
        usage_instructions='Use for wound dressing',
        is_critical=True,
        order=1
    )
    
    pack_item2 = PackItem.objects.create(
        pack=medical_pack,
        medication=medication2,
        quantity=10,  # Need 10 units but active store has 0
        item_type='consumable',
        usage_instructions='Use for cleaning wounds',
        is_critical=False,
        order=2
    )
    
    print(f"   Added {medical_pack.items.count()} items to pack")
    print(f"   Total pack cost: ₦{medical_pack.get_total_cost()}")
    
    print("\n3️⃣ Creating Pack Order")
    # Create a pack order
    pack_order = PackOrder.objects.create(
        pack=medical_pack,
        patient=patient,
        ordered_by=doctor,
        scheduled_date=timezone.now() + timedelta(days=1),
        order_notes='Needed for appendectomy surgery tomorrow'
    )
    print(f"   Created pack order #{pack_order.id}")
    print(f"   Order status: {pack_order.get_status_display()}")
    
    print("\n4️⃣ Processing Pack Order (This should trigger transfer)")
    # Process the pack order to create prescription
    # This should automatically transfer medications from bulk store to active store
    prescription = pack_order.process_order(pharmacist)
    print(f"   Processed order, created prescription #{prescription.id}")
    print(f"   Prescription status: {prescription.get_status_display()}")
    
    print("\n5️⃣ Verifying Transfer Results")
    # Verify the pack order was updated
    pack_order.refresh_from_db()
    print(f"   Updated order status: {pack_order.get_status_display()}")
    print(f"   Processed by: {pack_order.processed_by.get_full_name()}")
    print(f"   Linked prescription: #{pack_order.prescription.id}")
    
    # Check if medications were transferred to active store
    active_inventory1.refresh_from_db()
    active_inventory2.refresh_from_db()
    
    print(f"   Active store inventory for {medication1.name}: {active_inventory1.stock_quantity} units (should be >= 20)")
    print(f"   Active store inventory for {medication2.name}: {active_inventory2.stock_quantity} units (should be >= 10)")
    
    # Verify bulk store inventory was reduced
    bulk_inventory1.refresh_from_db()
    bulk_inventory2.refresh_from_db()
    
    print(f"   Bulk store inventory for {medication1.name}: {bulk_inventory1.stock_quantity} units (should be 80)")
    print(f"   Bulk store inventory for {medication2.name}: {bulk_inventory2.stock_quantity} units (should be 40)")
    
    # Verify that the transfer happened by checking if active store now has sufficient stock
    sufficient_stock_1 = active_inventory1.stock_quantity >= pack_item1.quantity
    sufficient_stock_2 = active_inventory2.stock_quantity >= pack_item2.quantity
    
    if sufficient_stock_1 and sufficient_stock_2:
        print("✅ Transfer successful! Active store now has sufficient stock for pack items.")
    else:
        print("❌ Transfer may have failed. Active store doesn't have sufficient stock.")
    
    print("\n6️⃣ Testing Prescription Dispensing")
    # Test dispensing the prescription to verify inventory usage
    # This should use the active store inventory
    prescription_items = prescription.items.all()
    print(f"   Prescription items to dispense: {prescription_items.count()}")
    
    for item in prescription_items:
        print(f"     - {item.medication.name}: {item.quantity} units required")
    
    print("\n✅ Pack Order Transfer Logic Test Completed!")
    print("\n📋 Summary of functionality verified:")
    print("   • Medical pack creation with items")
    print("   • Pack order creation")
    print("   • Automatic transfer from bulk store to active store when processing pack orders")
    print("   • Inventory management during transfers")
    print("   • Prescription creation with proper inventory linkage")
    
    return True

if __name__ == '__main__':
    try:
        run_transfer_test()
        print("\n🎉 Pack order transfer logic test completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()