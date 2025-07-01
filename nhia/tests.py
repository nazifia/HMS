from django.test import TestCase, Client
from django.urls import reverse
from patients.models import Patient
from nhia.models import NHIAPatient
import datetime
from django.contrib.auth import get_user_model

User = get_user_model()

class NHIARegistrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('nhia:register_independent_nhia_patient')
        self.patient_data = {
            'first_name': 'Test',
            'last_name': 'Patient',
            'date_of_birth': '2000-01-01',
            'gender': 'M',
            'phone_number': '+233240000000',
            'email': 'test@example.com',
            'address': '123 Test St',
            'city': 'Accra',
            'state': 'Greater Accra',
            'country': 'Ghana',
            'is_nhia_active': True,
        }
        self.user = User.objects.create_user(username='testuser', password='password', phone_number='1234567890')
        self.client.login(username='testuser', password='password')

    def test_nhia_reg_number_auto_generation(self):
        # Simulate a POST request to register an independent NHIA patient
        response = self.client.post(self.register_url, self.patient_data, follow=True)

        # Check if a new Patient and NHIAPatient object were created
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(NHIAPatient.objects.count(), 1)

        patient = Patient.objects.last()
        nhia_patient = NHIAPatient.objects.last()

        self.assertIsNotNone(patient)
        self.assertIsNotNone(nhia_patient)

        self.assertEqual(nhia_patient.patient, patient)
        self.assertTrue(nhia_patient.is_active)

        # Verify that nhia_reg_number was auto-generated and follows the expected format
        self.assertIsNotNone(nhia_patient.nhia_reg_number)
        
        today = datetime.date.today()
        expected_prefix = f"NHIA-{today.strftime('%Y%m%d')}-"
        self.assertTrue(nhia_patient.nhia_reg_number.startswith(expected_prefix))
        
        # Check if the sequential part is a 4-digit number
        sequential_part = nhia_patient.nhia_reg_number.split('-')[-1]
        self.assertTrue(sequential_part.isdigit())
        self.assertEqual(len(sequential_part), 4)

    def test_nhia_reg_number_uniqueness(self):
        # Register a first patient
        self.client.post(self.register_url, self.patient_data, follow=True)
        first_patient = Patient.objects.first()
        first_nhia_patient = NHIAPatient.objects.get(patient=first_patient)

        # Modify patient data for a second patient
        self.patient_data['first_name'] = 'Another'
        self.patient_data['email'] = 'another@example.com'
        self.patient_data['phone_number'] = '+233240000001'

        # Register a second patient
        self.client.post(self.register_url, self.patient_data, follow=True)
        second_patient = Patient.objects.last()
        second_nhia_patient = NHIAPatient.objects.get(patient=second_patient)

        # Assert that the registration numbers are different
        self.assertNotEqual(first_nhia_patient.nhia_reg_number, second_nhia_patient.nhia_reg_number)

        # Assert that both numbers follow the expected format
        today = datetime.date.today()
        expected_prefix = f"NHIA-{today.strftime('%Y%m%d')}-"
        self.assertTrue(first_nhia_patient.nhia_reg_number.startswith(expected_prefix))
        self.assertTrue(second_nhia_patient.nhia_reg_number.startswith(expected_prefix))
        
        # Check sequential parts
        first_seq = int(first_nhia_patient.nhia_reg_number.split('-')[-1])
        second_seq = int(second_nhia_patient.nhia_reg_number.split('-')[-1])
        self.assertEqual(second_seq, first_seq + 1)