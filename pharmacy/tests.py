from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
User = get_user_model()
from pharmacy.models import Patient, Prescription, Medication, PrescriptionItem
from pharmacy_billing.models import Invoice
from billing.models import Service
from decimal import Decimal

class CreatePrescriptionTestCase(TestCase):

    def setUp(self):
        # Create test user, patient, and service
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass', phone_number='+1234567890')
        self.client.login(username='testuser', password='testpass')

        self.patient = Patient.objects.create(first_name='Test', last_name='Patient', date_of_birth='1995-01-01', gender='M', phone_number='+1234567890', address='123 Test St', city='Test City', state='Test State', country='Test Country')
        self.service = Service.objects.create(name='Medication Dispensing', tax_percentage=10, price=Decimal('0.00'))
        self.medication = Medication.objects.create(name='Test Medication', price=Decimal('50.00'))

    def test_create_prescription_with_invoice(self):
        # Simulate POST request to create prescription
        response = self.client.post(reverse('pharmacy:create_prescription'), {
            'patient': self.patient.id,
            'doctor': self.user.id,
            'diagnosis': 'Test Diagnosis',
            'notes': 'Test Notes',
            'medication[]': [self.medication.id],
            'quantity[]': ['2'],
            'dosage[]': ['1 tablet'],
            'frequency[]': ['Twice a day'],
            'duration[]': ['5 days'],
            'instructions[]': ['After meals']
        })

        # Check prescription and invoice creation
        self.assertEqual(response.status_code, 302)  # Redirect after success
        prescription = Prescription.objects.get(patient=self.patient)
        self.assertIsNotNone(prescription)
        invoice = Invoice.objects.get(prescription=prescription)
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.subtotal, Decimal('100.00'))  # 2 * 50.00


    def test_create_prescription_without_service(self):
        # Delete the required service
        self.service.delete()

        response = self.client.post(reverse('pharmacy:create_prescription'), {
            'patient': self.patient.id,
            'doctor': self.user.id,
            'diagnosis': 'Test Diagnosis',
            'notes': 'Test Notes',
            'medication[]': [self.medication.id],
            'quantity[]': ['2'],
            'dosage[]': ['1 tablet'],
            'frequency[]': ['Twice a day'],
            'duration[]': ['5 days'],
            'instructions[]': ['After meals']
        })

        # Check that no invoice is created
        self.assertEqual(response.status_code, 302)  # Redirect after failure
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(Prescription.objects.exists())

    def test_missing_medication_dispensing_service(self):
        """Test invoice creation when 'Medication Dispensing' service is missing."""
        Service.objects.filter(name__iexact="Medication Dispensing").delete()

        response = self.client.post(reverse('pharmacy:create_prescription'), {
            'patient': self.patient.id,
            'doctor': self.user.id,
            'diagnosis': 'Test Diagnosis',
            'notes': 'Test Notes',
            'medication[]': [self.medication.id],
            'quantity[]': ['2'],
            'dosage[]': ['1 tablet'],
            'frequency[]': ['Twice a day'],
            'duration[]': ['5 days'],
            'instructions[]': ['After meals']
        })

        self.assertEqual(response.status_code, 302)  # Redirect after failure
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(Prescription.objects.exists())

    def test_invalid_tax_percentage(self):
        """Test invoice creation with invalid tax percentage."""
        service = Service.objects.get(name__iexact="Medication Dispensing")
        service.tax_percentage = -1  # Simulate invalid tax percentage
        service.save()

        response = self.client.post(reverse('pharmacy:create_prescription'), {
            'patient': self.patient.id,
            'doctor': self.user.id,
            'diagnosis': 'Test Diagnosis',
            'notes': 'Test Notes',
            'medication[]': [self.medication.id],
            'quantity[]': ['2'],
            'dosage[]': ['1 tablet'],
            'frequency[]': ['Twice a day'],
            'duration[]': ['5 days'],
            'instructions[]': ['After meals']
        })

        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertFalse(Invoice.objects.exists())
