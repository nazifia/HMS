from django.test import TestCase
from patients.forms import NHIAIndependentPatientForm
from patients.models import Patient
from nhia.models import NHIAPatient

class NHIAIndependentPatientFormTest(TestCase):
    def test_form_saves_patient_and_nhia_patient(self):
        form_data = {
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
        form = NHIAIndependentPatientForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        patient = form.save()

        self.assertIsNotNone(patient.pk)
        self.assertTrue(Patient.objects.filter(pk=patient.pk).exists())
        self.assertEqual(patient.patient_type, 'nhia')

        self.assertEqual(patient.patient_type, 'nhia')
