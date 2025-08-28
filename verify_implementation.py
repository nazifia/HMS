#!/usr/bin/env python
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Dispensary, Medication, MedicationInventory, ActiveStore, ActiveStoreInventory
from pharmacy.forms import DispenseItemForm

def test_implementation():
    """Test our implementation to verify it works correctly"""
    print("Testing our implementation...")
    
    # Check if THEATRE-PH dispensary exists
    try:
        theatre_ph = Dispensary.objects.get(name='THEATRE-PH')
        print(f"THEATRE-PH dispensary exists with ID: {theatre_ph.id}")
    except Dispensary.DoesNotExist:
        print("THEATRE-PH dispensary does not exist")
        return
    
    # Check if it has an active store
    active_store = getattr(theatre_ph, 'active_store', None)
    if active_store:
        print(f"THEATRE-PH has an active store: {active_store.name}")
    else:
        print("THEATRE-PH does not have an active store")
    
    # Get our test medication
    try:
        medication = Medication.objects.get(name='Test Medication For Dispensary Testing')
        print(f"Found test medication: {medication.name}")
    except Medication.DoesNotExist:
        print("Test medication not found")
        return
    
    # Create a mock prescription item for testing
    from pharmacy.models import Prescription, PrescriptionItem
    from patients.models import Patient
    from django.contrib.auth import get_user_model
    from datetime import date
    
    User = get_user_model()
    
    # Get or create a test patient
    patient, _ = Patient.objects.get_or_create(
        patient_number='TEST001',
        defaults={
            'first_name': 'Test',
            'last_name': 'Patient',
            'date_of_birth': date(1990, 1, 1),
            'gender': 'M',
            'phone_number': '0000000000',
            'is_active': True
        }
    )
    
    # Get or create a test doctor
    doctor, _ = User.objects.get_or_create(
        username='test_doctor',
        defaults={
            'first_name': 'Test',
            'last_name': 'Doctor',
            'email': 'test_doctor@example.com',
            'is_active': True
        }
    )
    
    # Create a test prescription
    prescription, _ = Prescription.objects.get_or_create(
        patient=patient,
        doctor=doctor,
        prescription_date=date.today(),
        diagnosis='Test diagnosis',
        defaults={
            'status': 'pending'
        }
    )
    
    # Create a test prescription item
    prescription_item, _ = PrescriptionItem.objects.get_or_create(
        prescription=prescription,
        medication=medication,
        dosage='1 tablet',
        frequency='Once daily',
        duration='5 days',
        quantity=10,
        defaults={
            'quantity_dispensed_so_far': 0,
            'is_dispensed': False
        }
    )
    
    print(f"Created test prescription item with {prescription_item.quantity} units prescribed")
    
    # Test the DispenseItemForm with MedicationInventory (legacy)
    print("\nTesting DispenseItemForm with MedicationInventory (legacy):")
    form1 = DispenseItemForm(
        data={
            'item_id': prescription_item.id,
            'dispense_this_item': True,
            'quantity_to_dispense': 5,
            'dispensary': theatre_ph.id
        },
        prescription_item=prescription_item,
        selected_dispensary=theatre_ph
    )
    
    if form1.is_valid():
        print("Form is valid with MedicationInventory")
        print(f"Available stock: {form1.available_stock}")
    else:
        print("Form is invalid with MedicationInventory")
        print(f"Errors: {form1.errors}")
    
    # Test the DispenseItemForm without selected dispensary
    print("\nTesting DispenseItemForm without selected dispensary:")
    form2 = DispenseItemForm(
        data={
            'item_id': prescription_item.id,
            'dispense_this_item': True,
            'quantity_to_dispense': 5
        },
        prescription_item=prescription_item
    )
    
    if form2.is_valid():
        print("Form is valid without selected dispensary")
        print(f"Available stock: {form2.available_stock}")
    else:
        print("Form is invalid without selected dispensary")
        print(f"Errors: {form2.errors}")
    
    print("\nTest completed successfully!")

if __name__ == '__main__':
    test_implementation()