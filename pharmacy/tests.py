from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from pharmacy.models import Patient, Prescription, Medication, PrescriptionItem
from pharmacy_billing.models import Invoice, Service
from decimal import Decimal

class CreatePrescriptionTestCase(TestCase):

    def setUp(self):
        # Create test user, patient, and service
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

        self.patient = Patient.objects.create(name='Test Patient', age=30, gender='M')
        self.service = Service.objects.create(name='Medication Dispensing', tax_percentage=10)
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
        self.assertTrue(Prescription.objects.exists())

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
        self.assertTrue(Prescription.objects.exists())

    def test_invalid_tax_percentage(self):
        """Test invoice creation with invalid tax percentage."""
        service = Service.objects.get(name__iexact="Medication Dispensing")
        service.tax_percentage = None  # Simulate invalid tax percentage
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
        self.assertTrue(Invoice.objects.exists())
        invoice = Invoice.objects.first()
        self.assertEqual(invoice.tax_amount, Decimal('0.00'))
