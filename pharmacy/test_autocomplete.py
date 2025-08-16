from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
User = get_user_model()
from patients.models import Patient
from pharmacy.models import Prescription, Medication, PrescriptionItem, DispensingLog, MedicationCategory, Dispensary
from billing.models import Service, Invoice
from decimal import Decimal
from accounts.models import CustomUserProfile

class MedicationAutocompleteTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(phone_number='+1234567891', password='testpass', username='testpharmacist', is_staff=True)
        # Create profile if it doesn't exist
        if not hasattr(self.user, 'profile'):
            CustomUserProfile.objects.create(user=self.user, role='pharmacist')
        else:
            self.user.profile.role = 'pharmacist'
            self.user.profile.save()
        self.client.login(phone_number='+1234567891', password='testpass')

        self.category = MedicationCategory.objects.create(name='Test Category')
        self.medication1 = Medication.objects.create(name='Paracetamol', price=Decimal('50.00'), category=self.category)
        self.medication2 = Medication.objects.create(name='Paracetamol Extra', price=Decimal('75.00'), category=self.category)
        self.medication3 = Medication.objects.create(name='Ibuprofen', price=Decimal('60.00'), category=self.category)

    def test_medication_autocomplete(self):
        # Test autocomplete endpoint
        response = self.client.get(reverse('pharmacy:medication_autocomplete'), {'term': 'Para'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('Paracetamol', data)
        self.assertIn('Paracetamol Extra', data)
        self.assertNotIn('Ibuprofen', data)
        
        # Test with different term
        response = self.client.get(reverse('pharmacy:medication_autocomplete'), {'term': 'Ibu'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('Ibuprofen', data)
        self.assertNotIn('Paracetamol', data)
        self.assertNotIn('Paracetamol Extra', data)
        
        # Test with empty term
        response = self.client.get(reverse('pharmacy:medication_autocomplete'), {'term': ''})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])