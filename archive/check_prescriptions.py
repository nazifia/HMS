#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription, Patient
from django.contrib.auth.models import User
from datetime import date

print("=== Prescription Database Check ===")
print(f"Total prescriptions: {Prescription.objects.count()}")
print("\nPrescriptions by status:")
for status, display_name in Prescription.STATUS_CHOICES:
    count = Prescription.objects.filter(status=status).count()
    print(f"  {status} ({display_name}): {count}")

print(f"\nTotal patients: {Patient.objects.count()}")
print(f"Total users: {User.objects.count()}")

# Create a test prescription if none exist
if Prescription.objects.count() == 0:
    print("\n=== Creating Test Data ===")
    
    # Check if we have patients and users
    patients = Patient.objects.all()
    doctors = User.objects.filter(is_staff=True)
    
    if patients.exists() and doctors.exists():
        patient = patients.first()
        doctor = doctors.first()
        
        prescription = Prescription.objects.create(
            patient=patient,
            doctor=doctor,
            prescription_date=date.today(),
            status='pending',
            diagnosis='Test diagnosis for pending prescription',
            notes='This is a test prescription to verify the dispensing system'
        )
        
        print(f"Created test prescription #{prescription.id}")
        print(f"Patient: {prescription.patient.get_full_name()}")
        print(f"Doctor: {prescription.doctor.get_full_name()}")
        print(f"Status: {prescription.status}")
        print(f"Date: {prescription.prescription_date}")
    else:
        print("Cannot create test prescription - no patients or doctors found")
        print(f"Patients available: {patients.count()}")
        print(f"Staff users available: {doctors.count()}")
else:
    print("\nPrescriptions already exist in the database.")

print("\n=== Check Complete ===")