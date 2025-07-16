#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription, PrescriptionItem, Medication, Dispensary, MedicationInventory
from django.contrib.auth import get_user_model
from datetime import date

User = get_user_model()

print("=== Prescription 2 Analysis ===")
try:
    prescription = Prescription.objects.get(id=2)
    print(f"Prescription {prescription.id}: {prescription.status}")
    print(f"Patient: {prescription.patient.get_full_name()}")
    print(f"Doctor: {prescription.doctor.get_full_name()}")
    print(f"Date: {prescription.prescription_date}")
    
    items = prescription.items.all()
    print(f"\nTotal items: {items.count()}")
    print(f"Non-dispensed items: {prescription.items.filter(is_dispensed=False).count()}")
    
    if items.exists():
        for item in items:
            print(f"  - {item.medication.name}: qty={item.quantity}, dispensed_so_far={item.quantity_dispensed_so_far}, is_dispensed={item.is_dispensed}")
    else:
        print("\n=== No prescription items found. Creating sample items... ===")
        
        # Get some medications
        medications = Medication.objects.filter(is_active=True)[:3]
        if medications.exists():
            for i, medication in enumerate(medications, 1):
                item = PrescriptionItem.objects.create(
                    prescription=prescription,
                    medication=medication,
                    dosage=f"{i} tablet(s)",
                    frequency="Twice daily",
                    duration="7 days",
                    instructions="Take after meals",
                    quantity=14  # 2 tablets per day for 7 days
                )
                print(f"  Created item: {item.medication.name} - {item.quantity} units")
        else:
            print("  No medications found to create items")
    
    print("\n=== Dispensary and Stock Check ===")
    dispensaries = Dispensary.objects.all()
    print(f"Available dispensaries: {dispensaries.count()}")
    
    if not dispensaries.exists():
        print("Creating default dispensary...")
        dispensary = Dispensary.objects.create(
            name="Main Pharmacy",
            location="Ground Floor",
            description="Main hospital pharmacy",
            is_active=True
        )
        print(f"Created dispensary: {dispensary.name}")
    else:
        dispensary = dispensaries.first()
        print(f"Using dispensary: {dispensary.name}")
    
    # Check stock for prescription items
    print("\n=== Stock Status ===")
    for item in prescription.items.all():
        try:
            inventory = MedicationInventory.objects.get(
                medication=item.medication,
                dispensary=dispensary
            )
            print(f"  {item.medication.name}: {inventory.stock_quantity} units in stock")
        except MedicationInventory.DoesNotExist:
            print(f"  {item.medication.name}: No stock record - creating with 50 units")
            MedicationInventory.objects.create(
                medication=item.medication,
                dispensary=dispensary,
                stock_quantity=50,
                reorder_level=10
            )
    
except Prescription.DoesNotExist:
    print("Prescription with ID 2 does not exist")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Fix Complete ===")