from django.test import TestCase, Client
from django.urls import reverse
from patients.models import Patient
from retainership.models import RetainershipPatient
import datetime
from django.contrib.auth import get_user_model

User = get_user_model()

class RetainershipRegistrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('retainership:register_independent_retainership_patient')
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
            'is_retainership_active': True,
        }
        self.user = User.objects.create_user(username='testuser', password='password', phone_number='1234567890')
        self.client.login(username='testuser', password='password')

    def test_retainership_reg_number_auto_generation(self):
        # Simulate a POST request to register an independent Retainership patient
        response = self.client.post(self.register_url, self.patient_data, follow=True)

        # Check if a new Patient and RetainershipPatient object were created
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(Patient.objects.filter(patient_type='retainership').count(), 1)

        patient = Patient.objects.last()
        retainership_patient = RetainershipPatient.objects.last()

        self.assertIsNotNone(patient)
        self.assertIsNotNone(retainership_patient)

        self.assertEqual(retainership_patient.patient, patient)
        self.assertTrue(retainership_patient.is_active)

        # Verify that retainership_reg_number was auto-generated and follows the expected format
        self.assertIsNotNone(retainership_patient.retainership_reg_number)
        self.assertTrue(str(retainership_patient.retainership_reg_number).startswith('3'))
        self.assertEqual(len(str(retainership_patient.retainership_reg_number)), 10)

    def test_retainership_reg_number_uniqueness(self):
        # Register a first patient
        self.client.post(self.register_url, self.patient_data, follow=True)
        first_patient = Patient.objects.first()
        first_retainership_patient = RetainershipPatient.objects.get(patient=first_patient)

        # Modify patient data for a second patient
        self.patient_data['first_name'] = 'Another'
        self.patient_data['email'] = 'another@example.com'
        self.patient_data['phone_number'] = '+233240000001'

        # Register a second patient
        self.client.post(self.register_url, self.patient_data, follow=True)
        second_patient = Patient.objects.last()
        self.assertEqual(second_patient.patient_type, 'retainership')
        second_retainership_patient = RetainershipPatient.objects.get(patient=second_patient)

        # Assert that the registration numbers are different
        self.assertNotEqual(first_retainership_patient.retainership_reg_number, second_retainership_patient.retainership_reg_number)
