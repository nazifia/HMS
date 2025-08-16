from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
User = get_user_model()
from patients.models import Patient
from pharmacy.models import Prescription, Medication, PrescriptionItem
from billing.models import Service, Invoice
from decimal import Decimal
from accounts.models import CustomUserProfile

class DebugPrescriptionTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(phone_number='+1234567891', password='testpass', username='testdoctor', is_staff=True)
        # Create profile if it doesn't exist
        if not hasattr(self.user, 'profile'):
            CustomUserProfile.objects.create(user=self.user, role='doctor')
        else:
            self.user.profile.role = 'doctor'
            self.user.profile.save()
        
        self.patient = Patient.objects.create(first_name='Test', last_name='Patient', date_of_birth='1995-01-01', gender='M', phone_number='+1234567890', address='123 Test St', city='Test City', state='Test State', country='Test Country')
        self.service = Service.objects.create(name='Medication Dispensing', tax_percentage=Decimal('0.00'), price=Decimal('0.00'))
        self.medication = Medication.objects.create(name='Test Medication', price=Decimal('50.00'))

    def test_simple_get_request(self):
        # First login
        login_result = self.client.login(phone_number='+1234567891', password='testpass')
        print(f"Login result: {login_result}")
        
        # Check if user is authenticated
        response = self.client.get('/accounts/profile/')
        print(f"Profile response status: {response.status_code}")
        
        # Try to access the prescription creation page
        response = self.client.get(reverse('pharmacy:create_prescription'))
        print(f"Create prescription GET response status: {response.status_code}")
        print(f"Response content preview: {response.content[:200]}")
        
        # Try POST request
        post_data = {
            'patient': self.patient.id,
            'doctor': self.user.id,
            'prescription_date': timezone.now().date(),
            'prescription_type': 'outpatient',
            'diagnosis': 'Test Diagnosis',
            'notes': 'Test Notes',
            'medication[]': [str(self.medication.id)],
            'quantity[]': ['2'],
            'dosage[]': ['1 tablet'],
            'frequency[]': ['Twice a day'],
            'duration[]': ['5 days'],
            'instructions[]': ['After meals']
        }
        response = self.client.post(reverse('pharmacy:create_prescription'), post_data)
        print(f"Create prescription POST response status: {response.status_code}")
        if hasattr(response, 'content'):
            print(f"Response content: {response.content}")
        print(f"Prescriptions count: {Prescription.objects.count()}")
        print(f"Invoices count: {Invoice.objects.count()}")