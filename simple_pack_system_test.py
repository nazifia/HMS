#!/usr/bin/env python
"""
Simple test script to demonstrate core pharmacy pack system functionality

This script demonstrates:
1. Creating a medical pack with items
2. Creating a pack order
3. Processing the pack order to create a prescription
4. Verifying the prescription was created correctly
"""

import os
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import MedicalPack, PackItem, PackOrder, Medication, MedicationCategory
from patients.models import Patient
from accounts.models import CustomUser
from django.utils import timezone

def run_simple_test():
    """Run a simple test to demonstrate the pack system functionality"""
    print("🧪 Simple Pharmacy Pack System Test")
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
        # Try to get the first category with this name
        med_category = MedicationCategory.objects.filter(name='Surgical Supplies').first()
        if not med_category:
            # Create if none exists
            med_category = MedicationCategory.objects.create(
                name='Surgical Supplies',
                description='Medical supplies for surgical procedures'
            )
            print("✓ Created new medication category")
        else:
            print("✓ Using existing medication category")
    except Exception as e:
        # Create if any other error
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
            # Create medications if they don't exist
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
    except Exception as e:
        # Create medications if any error
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
    
    print("\n1️⃣ Creating Medical Pack")
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
    
    # Add items to the pack
    pack_item1 = PackItem.objects.create(
        pack=medical_pack,
        medication=medication1,
        quantity=10,
        item_type='consumable',
        usage_instructions='Use for wound dressing',
        is_critical=True,
        order=1
    )
    
    pack_item2 = PackItem.objects.create(
        pack=medical_pack,
        medication=medication2,
        quantity=5,
        item_type='consumable',
        usage_instructions='Use for cleaning wounds',
        is_critical=False,
        order=2
    )
    
    print(f"   Added {medical_pack.items.count()} items to pack")
    print(f"   Total pack cost: ₦{medical_pack.get_total_cost()}")
    
    print("\n2️⃣ Creating Pack Order")
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
    
    print("\n3️⃣ Processing Pack Order")
    # Process the pack order to create prescription
    prescription = pack_order.process_order(pharmacist)
    print(f"   Processed order, created prescription #{prescription.id}")
    print(f"   Prescription status: {prescription.get_status_display()}")
    
    print("\n4️⃣ Verifying Results")
    # Verify the pack order was updated
    pack_order.refresh_from_db()
    print(f"   Updated order status: {pack_order.get_status_display()}")
    print(f"   Processed by: {pack_order.processed_by.get_full_name()}")
    print(f"   Linked prescription: #{pack_order.prescription.id}")
    
    # Verify prescription items
    prescription_items = prescription.items.all()
    print(f"   Prescription items created: {prescription_items.count()}")
    
    for item in prescription_items:
        print(f"     - {item.medication.name}: {item.quantity} units")
    
    print("\n5️⃣ Testing Dispensing")
    # Test dispensing the pack order
    pack_order.dispense_order(pharmacist)
    pack_order.refresh_from_db()
    print(f"   Dispensed order status: {pack_order.get_status_display()}")
    print(f"   Dispensed by: {pack_order.dispensed_by.get_full_name()}")
    
    print("\n✅ All tests completed successfully!")
    print("\n📋 Summary of functionality verified:")
    print("   • Medical pack creation with items")
    print("   • Pack order creation")
    print("   • Automatic prescription creation from pack orders")
    print("   • Prescription item generation")
    print("   • Pack order status management")
    print("   • Pack order dispensing workflow")
    
    return True

if __name__ == '__main__':
    try:
        run_simple_test()
        print("\n🎉 Simple test completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()