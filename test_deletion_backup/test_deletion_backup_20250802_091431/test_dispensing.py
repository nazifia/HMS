#!/usr/bin/env python
"""
Test script for dispensing functionality
"""
import os
import sys
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription, PrescriptionItem, Dispensary, MedicationInventory, Medication, MedicationCategory
from patients.models import Patient
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

def test_dispensing_workflow():
    """Test the dispensing workflow"""
    print("Testing Dispensing Workflow")
    print("=" * 50)
    
    # Get prescription 2
    try:
        prescription = Prescription.objects.get(id=2)
        print(f"✓ Found prescription {prescription.id}")
        print(f"  Patient: {prescription.patient.get_full_name()}")
        print(f"  Status: {prescription.status}")
        print(f"  Date: {prescription.prescription_date}")
        
        # Check prescription items
        items = prescription.items.all()
        print(f"  Total items: {items.count()}")
        
        pending_items = prescription.items.filter(is_dispensed=False)
        print(f"  Pending items: {pending_items.count()}")
        
        for item in pending_items:
            print(f"    - {item.medication.name}: {item.quantity} prescribed, {item.quantity_dispensed_so_far} dispensed, {item.remaining_quantity_to_dispense} remaining")
        
        # Check dispensaries
        dispensaries = Dispensary.objects.filter(is_active=True)
        print(f"  Active dispensaries: {dispensaries.count()}")
        
        for dispensary in dispensaries:
            print(f"    - {dispensary.name}")
            
            # Check inventory for each pending item
            for item in pending_items:
                try:
                    inventory = MedicationInventory.objects.get(
                        medication=item.medication,
                        dispensary=dispensary
                    )
                    print(f"      {item.medication.name}: {inventory.stock_quantity} in stock")
                except MedicationInventory.DoesNotExist:
                    print(f"      {item.medication.name}: No inventory record")
        
        print("\n✓ Dispensing workflow test completed successfully!")
        return True
        
    except Prescription.DoesNotExist:
        print("✗ Prescription with ID 2 not found")
        return False
    except Exception as e:
        print(f"✗ Error during test: {str(e)}")
        return False

def create_test_inventory():
    """Create test inventory if needed"""
    print("\nCreating test inventory...")
    
    try:
        prescription = Prescription.objects.get(id=2)
        dispensary = Dispensary.objects.filter(is_active=True).first()
        
        if not dispensary:
            print("✗ No active dispensary found")
            return False
            
        for item in prescription.items.filter(is_dispensed=False):
            inventory, created = MedicationInventory.objects.get_or_create(
                medication=item.medication,
                dispensary=dispensary,
                defaults={
                    'stock_quantity': 100,  # Add sufficient stock for testing
                    'reorder_level': 10,
                }
            )
            
            if created:
                print(f"✓ Created inventory for {item.medication.name} with 100 units")
            else:
                if inventory.stock_quantity < item.remaining_quantity_to_dispense:
                    inventory.stock_quantity = item.remaining_quantity_to_dispense + 50
                    inventory.save()
                    print(f"✓ Updated inventory for {item.medication.name} to {inventory.stock_quantity} units")
                else:
                    print(f"✓ Inventory for {item.medication.name} already sufficient: {inventory.stock_quantity} units")
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating test inventory: {str(e)}")
        return False

def create_test_data():
    """Create test data if prescription 2 doesn't exist"""
    print("\nChecking/Creating test data...")

    try:
        # Check if prescription 2 exists
        prescription = Prescription.objects.get(id=2)
        print(f"✓ Prescription 2 already exists")
        return True
    except Prescription.DoesNotExist:
        print("Creating test prescription...")

        # Get or create test patient
        patient, created = Patient.objects.get_or_create(
            patient_id='TEST001',
            defaults={
                'first_name': 'Test',
                'last_name': 'Patient',
                'date_of_birth': '1990-01-01',
                'gender': 'M',
                'phone_number': '1234567890'
            }
        )

        # Get or create test doctor
        doctor, created = User.objects.get_or_create(
            username='testdoctor',
            defaults={
                'first_name': 'Test',
                'last_name': 'Doctor',
                'email': 'testdoctor@example.com'
            }
        )

        # Get or create medication category
        category, created = MedicationCategory.objects.get_or_create(
            name='Test Category',
            defaults={'description': 'Test medication category'}
        )

        # Get or create test medication
        medication, created = Medication.objects.get_or_create(
            name='Test Medication',
            defaults={
                'generic_name': 'Test Generic',
                'category': category,
                'dosage_form': 'Tablet',
                'strength': '500mg',
                'price': 10.00,
                'is_active': True
            }
        )

        # Create test prescription
        prescription = Prescription.objects.create(
            patient=patient,
            doctor=doctor,
            prescription_date=timezone.now().date(),
            diagnosis='Test diagnosis',
            status='pending'
        )

        # Create prescription item
        PrescriptionItem.objects.create(
            prescription=prescription,
            medication=medication,
            dosage='1 tablet',
            frequency='twice daily',
            duration='7 days',
            instructions='Take after meals',
            quantity=14
        )

        print(f"✓ Created test prescription {prescription.id}")
        return True

def create_test_dispensary():
    """Create test dispensary if needed"""
    dispensary, created = Dispensary.objects.get_or_create(
        name='Test Dispensary',
        defaults={
            'location': 'Test Location',
            'description': 'Test dispensary for testing',
            'is_active': True
        }
    )

    if created:
        print(f"✓ Created test dispensary: {dispensary.name}")
    else:
        print(f"✓ Test dispensary already exists: {dispensary.name}")

    return dispensary

if __name__ == "__main__":
    print("HMS Dispensing Workflow Test")
    print("=" * 50)

    # Create test data if needed
    create_test_data()
    create_test_dispensary()

    # Test the workflow
    if test_dispensing_workflow():
        # Create test inventory if needed
        create_test_inventory()

        # Test again after inventory creation
        print("\nRe-testing after inventory setup...")
        test_dispensing_workflow()

    print("\nTest completed!")
    print("\nYou can now test the dispensing workflow at:")
    print("http://127.0.0.1:8001/pharmacy/prescriptions/2/dispense/")
