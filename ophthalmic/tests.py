from django.test import TestCase
from django.contrib.auth import get_user_model
from patients.models import Patient
from doctors.models import Doctor
from .models import OphthalmicRecord
from datetime import datetime

User = get_user_model()

class OphthalmicRecordModelTest(TestCase):
    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create a patient
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            gender='M',
            date_of_birth='1990-01-01'
        )
        
        # Create a doctor
        self.doctor = Doctor.objects.create(
            first_name='Jane',
            last_name='Smith',
            specialization='Ophthalmologist'
        )
    
    def test_ophthalmic_record_creation(self):
        """Test that an ophthalmic record can be created"""
        record = OphthalmicRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            diagnosis='Myopia',
            treatment_plan='Prescribe glasses'
        )
        
        self.assertEqual(record.patient, self.patient)
        self.assertEqual(record.doctor, self.doctor)
        self.assertEqual(record.diagnosis, 'Myopia')
        self.assertEqual(record.treatment_plan, 'Prescribe glasses')
        self.assertIsNotNone(record.created_at)
        self.assertIsNotNone(record.updated_at)
    
    def test_ophthalmic_record_str_representation(self):
        """Test the string representation of an ophthalmic record"""
        record = OphthalmicRecord.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            visit_date=datetime(2023, 1, 15, 10, 30)
        )
        
        expected_str = f"Ophthalmic Record for John Doe - 2023-01-15"
        self.assertEqual(str(record), expected_str)