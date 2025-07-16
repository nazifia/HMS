#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription
from django.urls import reverse

print("=== Available Prescriptions ===")
prescriptions = Prescription.objects.all().order_by('-prescription_date')

if prescriptions.exists():
    for prescription in prescriptions:
        print(f"\nPrescription #{prescription.id}")
        print(f"  Patient: {prescription.patient.get_full_name()}")
        print(f"  Doctor: {prescription.doctor.get_full_name()}")
        print(f"  Date: {prescription.prescription_date}")
        print(f"  Status: {prescription.status} ({prescription.get_status_display()})")
        print(f"  Type: {prescription.prescription_type} ({prescription.get_prescription_type_display()})")
        
        # Show URLs
        try:
            detail_url = reverse('pharmacy:prescription_detail', args=[prescription.id])
            dispense_url = reverse('pharmacy:dispense_prescription', args=[prescription.id])
            print(f"  Detail URL: http://127.0.0.1:8000{detail_url}")
            print(f"  Dispense URL: http://127.0.0.1:8000{dispense_url}")
        except Exception as e:
            print(f"  URL Error: {e}")
else:
    print("No prescriptions found in the database.")

print(f"\n=== Main URLs ===")
try:
    prescription_list_url = reverse('pharmacy:prescriptions')
    print(f"Prescription List: http://127.0.0.1:8000{prescription_list_url}")
except Exception as e:
    print(f"Prescription List URL Error: {e}")

print("\n=== Instructions ===")
print("1. Visit the Prescription List page to see all prescriptions")
print("2. Click 'Dispense' button next to any pending prescription")
print("3. This will take you to the dispensing page")