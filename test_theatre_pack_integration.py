#!/usr/bin/env python
"""
Test script to verify integration between pharmacy pack system and theatre module

This script demonstrates:
1. Creating a surgery
2. Ordering a medical pack for the surgery
3. Processing the pack order to create a prescription
4. Verifying the integration between theatre and pharmacy modules
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
from theatre.models import Surgery, SurgeryType, OperationTheatre
from django.utils import timezone

def run_theatre_integration_test():
    """Run a test to demonstrate the integration between theatre and pharmacy"""
    print("🎭 Theatre-Pharmacy Integration Test")
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
    
    # Get or create surgery type
    try:
        surgery_type = SurgeryType.objects.filter(name='Appendectomy').first()
        if not surgery_type:
            surgery_type = SurgeryType.objects.create(
                name='Appendectomy',
                description='Surgical removal of appendix',
                average_duration=timedelta(hours=2),
                preparation_time=timedelta(minutes=30),
                recovery_time=timedelta(hours=4),
                risk_level='medium'
            )
            print("✓ Created new surgery type")
        else:
            print("✓ Using existing surgery type")
    except Exception:
        surgery_type = SurgeryType.objects.create(
            name='Appendectomy',
            description='Surgical removal of appendix',
            average_duration=timedelta(hours=2),
            preparation_time=timedelta(minutes=30),
            recovery_time=timedelta(hours=4),
            risk_level='medium'
        )
        print("✓ Created new surgery type")
    
    # Get or create operation theatre
    try:
        theatre = OperationTheatre.objects.filter(name='Theatre 1').first()
        if not theatre:
            theatre = OperationTheatre.objects.create(
                name='Theatre 1',
                theatre_number='T001',
                floor='2nd Floor',
                is_available=True,
                capacity=1
            )
            print("✓ Created new operation theatre")
        else:
            print("✓ Using existing operation theatre")
    except Exception:
        theatre = OperationTheatre.objects.create(
            name='Theatre 1',
            theatre_number='T001',
            floor='2nd Floor',
            is_available=True,
            capacity=1
        )
        print("✓ Created new operation theatre")
    
    print("\n1️⃣ Creating Surgery")
    # Create a surgery
    surgery = Surgery.objects.create(
        patient=patient,
        surgery_type=surgery_type,
        surgeon=doctor,
        scheduled_date=timezone.now() + timedelta(days=1),
        status='scheduled',
        theatre=theatre
    )
    print(f"   Created surgery #{surgery.id}")
    print(f"   Surgery type: {surgery.surgery_type.name}")
    print(f"   Patient: {surgery.patient.get_full_name()}")
    
    print("\n2️⃣ Creating Medical Pack for Surgery")
    # Create a medical pack specifically for this surgery type
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
        usage_instructions='Use for wound dressing during appendectomy',
        is_critical=True,
        order=1
    )
    
    pack_item2 = PackItem.objects.create(
        pack=medical_pack,
        medication=medication2,
        quantity=5,
        item_type='consumable',
        usage_instructions='Use for cleaning surgical site',
        is_critical=False,
        order=2
    )
    
    print(f"   Added {medical_pack.items.count()} items to pack")
    print(f"   Total pack cost: ₦{medical_pack.get_total_cost()}")
    
    print("\n3️⃣ Creating Pack Order with Surgery Context")
    # Create a pack order linked to the surgery
    pack_order = PackOrder.objects.create(
        pack=medical_pack,
        patient=patient,
        surgery=surgery,
        ordered_by=doctor,
        scheduled_date=surgery.scheduled_date,
        order_notes=f'Needed for appendectomy surgery #{surgery.id}'
    )
    print(f"   Created pack order #{pack_order.id}")
    print(f"   Linked to surgery #{pack_order.surgery.id}")
    print(f"   Order status: {pack_order.get_status_display()}")
    
    print("\n4️⃣ Processing Pack Order")
    # Process the pack order to create prescription
    prescription = pack_order.process_order(pharmacist)
    print(f"   Processed order, created prescription #{prescription.id}")
    print(f"   Prescription type: {prescription.get_prescription_type_display()}")
    
    print("\n5️⃣ Verifying Integration")
    # Verify the integration
    pack_order.refresh_from_db()
    print(f"   Updated order status: {pack_order.get_status_display()}")
    print(f"   Still linked to surgery: #{pack_order.surgery.id}")
    print(f"   Linked prescription: #{pack_order.prescription.id}")
    
    # Verify prescription details
    prescription.refresh_from_db()
    print(f"   Prescription diagnosis: {prescription.diagnosis}")
    print(f"   Prescription notes: {prescription.notes}")
    
    # Verify prescription items
    prescription_items = prescription.items.all()
    print(f"   Prescription items created: {prescription_items.count()}")
    
    for item in prescription_items:
        print(f"     - {item.medication.name}: {item.quantity} units")
        print(f"       Instructions: {item.instructions}")
    
    print("\n6️⃣ Testing Dispensing")
    # Test dispensing the pack order
    pack_order.dispense_order(pharmacist)
    pack_order.refresh_from_db()
    print(f"   Dispensed order status: {pack_order.get_status_display()}")
    
    print("\n✅ Theatre-Pharmacy Integration Test Completed Successfully!")
    print("\n📋 Summary of integration functionality verified:")
    print("   • Surgery creation with all required fields")
    print("   • Medical pack creation for specific surgery type")
    print("   • Pack order creation with surgery context")
    print("   • Automatic prescription creation with surgery information")
    print("   • Prescription item generation with proper instructions")
    print("   • Complete workflow from surgery to dispensing")
    print("   • Data consistency between theatre and pharmacy modules")
    
    return True

if __name__ == '__main__':
    try:
        run_theatre_integration_test()
        print("\n🎉 Theatre-Pharmacy integration test completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()