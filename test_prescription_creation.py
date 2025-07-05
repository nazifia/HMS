import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Prescription, Medication
from patients.models import Patient
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

def test_direct_prescription_creation():
    try:
        # Create a test patient and doctor
        patient, created = Patient.objects.get_or_create(
            first_name='Test', last_name='Patient',
            defaults={'date_of_birth': '1990-01-01', 'gender': 'M', 'phone_number': '+1234567890'}
        )
        import random

        doctor, created = User.objects.get_or_create(
            username='testdoctor',
            defaults={'password': 'testpass', 'phone_number': f'+123456789{random.randint(100, 999)}'}
        )

        # Create a prescription directly
        prescription = Prescription.objects.create(
            patient=patient,
            doctor=doctor,
            prescription_date=timezone.now().date(),
            diagnosis='Test Diagnosis',
            notes='Test Notes',
            status='pending',
            payment_status='unpaid'
        )

        print(f"Successfully created Prescription with ID: {prescription.id}")
        assert Prescription.objects.filter(id=prescription.id).exists()
        print("Assertion passed: Prescription exists in database.")

    except Exception as e:
        print(f"Error during direct prescription creation test: {e}")

if __name__ == '__main__':
    test_direct_prescription_creation()
