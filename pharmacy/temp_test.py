from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
User = get_user_model()
from patients.models import Patient
from pharmacy.models import Prescription, Medication, PrescriptionItem
from pharmacy_billing.models import Invoice
from billing.models import Service
from decimal import Decimal
from accounts.models import CustomUserProfile

class IsolatedCreatePrescriptionTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(phone_number='+1234567891', password='testpass', username='testdoctor', is_staff=True)
        self.user.profile.role = 'doctor'
        self.user.profile.save()
        self.client.login(phone_number='+1234567891', password='testpass')

        self.patient = Patient.objects.create(first_name='Test', last_name='Patient', date_of_birth='1995-01-01', gender='M', phone_number='+1234567890', address='123 Test St', city='Test City', state='Test State', country='Test Country')
        self.service = Service.objects.create(name='Medication Dispensing', tax_percentage=Decimal('10.00'), price=Decimal('0.00'))
        self.medication = Medication.objects.create(name='Test Medication', price=Decimal('50.00'))

    def test_successful_prescription_creation(self):
        post_data = {
            'patient': self.patient.id,
            'doctor': self.user.id,
            'prescription_date': timezone.now().date(),
            'prescription_type': 'outpatient',
            'diagnosis': 'Test Diagnosis',
            'notes': 'Test Notes',
            'medication[]': [self.medication.id],
            'quantity[]': ['2'],
            'dosage[]': ['1 tablet'],
            'frequency[]': ['Twice a day'],
            'duration[]': ['5 days'],
            'instructions[]': ['After meals']
        }
        response = self.client.post(reverse('pharmacy:create_prescription'), post_data)

        if response.status_code != 302:
            print(f"Expected status 302, got {response.status_code}")
            print(f"Response content: {response.content.decode()}")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Prescription.objects.filter(patient=self.patient).exists())
        prescription = Prescription.objects.get(patient=self.patient)
        self.assertTrue(Invoice.objects.filter(prescription=prescription).exists())
        invoice = Invoice.objects.get(prescription=prescription)
        self.assertEqual(invoice.subtotal, Decimal('100.00'))
