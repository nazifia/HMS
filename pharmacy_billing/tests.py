from django.test import TestCase
from accounts.models import CustomUser
from django.utils import timezone
from decimal import Decimal
from patients.models import Patient
from pharmacy.models import Medication, Prescription
from billing.models import Service
from pharmacy_billing.utils import create_pharmacy_invoice

class PharmacyBillingNHIATest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='testuser', password='testpassword', phone_number='1234567890')
        self.pharmacist = CustomUser.objects.create_user(username='pharmacist', password='pharmacistpass', phone_number='0987654321')

        # Create a 'Medication Dispensing' service if it doesn't exist
        self.medication_service, created = Service.objects.get_or_create(
            name="Medication Dispensing",
            defaults={
                'description': 'Service for dispensing medications',
                'price': Decimal('0.00'), # Price is dynamic based on medication
                'tax_percentage': Decimal('0.05') # Example tax
            }
        )

        # Create a regular patient
        self.regular_patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            gender='Male',
            patient_type='regular'
        )

        # Create an NHIA patient
        self.nhia_patient = Patient.objects.create(
            first_name='Jane',
            last_name='Smith',
            date_of_birth='1985-05-10',
            gender='Female',
            patient_type='nhia'
        )

        # Create a medication
        self.medication = Medication.objects.create(
            name='Amoxicillin',
            generic_name='Amoxicillin',
            strength='250mg',
            dosage_form='Capsule',
            price=Decimal('100.00'),
            stock_quantity=100,
            reorder_level=20,
            expiry_date='2026-12-31'
        )

    def test_nhia_patient_10_percent_payment(self):
        # Create a prescription for the regular patient
        regular_prescription = Prescription.objects.create(
            patient=self.regular_patient,
            doctor=self.user,
            prescription_date=timezone.now().date(),
            diagnosis='Bacterial Infection',
            status='pending',
            payment_status='unpaid'
        )
        regular_prescription.items.create(
            medication=self.medication,
            quantity=10,
            dosage='1 capsule',
            frequency='TID',
            duration='7 days'
        )

        # Create a prescription for the NHIA patient
        nhia_prescription = Prescription.objects.create(
            patient=self.nhia_patient,
            doctor=self.user,
            prescription_date=timezone.now().date(),
            diagnosis='Bacterial Infection',
            status='pending',
            payment_status='unpaid'
        )
        nhia_prescription.items.create(
            medication=self.medication,
            quantity=10,
            dosage='1 capsule',
            frequency='TID',
            duration='7 days'
        )

        # Simulate a request object for create_pharmacy_invoice
        class MockMessages:
            def __init__(self):
                self.store = []
            def add(self, level, message, extra_tags=''):
                self.store.append((level, message, extra_tags))
            def info(self, message):
                self.add('info', message)
            def error(self, message):
                self.add('error', message)
            def success(self, message):
                self.add('success', message)
            def warning(self, message):
                self.add('warning', message)

        class MockRequest:
            def __init__(self, user):
                self.user = user
                self.method = 'POST'
                self.META = {'HTTP_REFERER': '/'} # Mock HTTP_REFERER
                self._messages = MockMessages() # Attach the mock messages object
            
            @property
            def messages(self):
                return self._messages

        mock_request = MockRequest(self.pharmacist)

        # Calculate expected total prescribed value for 10 units of medication
        expected_total_value = self.medication.price * 10 # 100.00 * 10 = 1000.00

        # Create invoice for regular patient
        regular_invoice = create_pharmacy_invoice(mock_request, regular_prescription, expected_total_value)
        self.assertIsNotNone(regular_invoice)
        
        # Recalculate total amount including tax for regular patient
        regular_subtotal = expected_total_value
        regular_tax_amount = (regular_subtotal * self.medication_service.tax_percentage) / Decimal('100.00')
        expected_regular_total = (regular_subtotal + regular_tax_amount).quantize(Decimal('0.01'))
        
        self.assertEqual(regular_invoice.subtotal, regular_subtotal)
        self.assertEqual(regular_invoice.total_amount, expected_regular_total)

        # Create invoice for NHIA patient
        nhia_invoice = create_pharmacy_invoice(mock_request, nhia_prescription, expected_total_value)
        self.assertIsNotNone(nhia_invoice)

        # NHIA patient should pay 10% of the subtotal
        expected_nhia_subtotal = expected_total_value * Decimal('0.10')
        nhia_tax_amount = (expected_nhia_subtotal * self.medication_service.tax_percentage) / Decimal('100.00')
        expected_nhia_total = (expected_nhia_subtotal + nhia_tax_amount).quantize(Decimal('0.01'))

        self.assertEqual(nhia_invoice.subtotal, expected_nhia_subtotal)
        self.assertEqual(nhia_invoice.total_amount, expected_nhia_total)

        # Verify that NHIA patient's total is 10% of regular patient's total (approximately)
        self.assertAlmostEqual(nhia_invoice.total_amount, regular_invoice.total_amount * Decimal('0.10'), places=2)

        # Verify invoice items
        self.assertEqual(regular_invoice.items.count(), 1)
        self.assertEqual(nhia_invoice.items.count(), 1)
        self.assertEqual(regular_invoice.items.first().unit_price, regular_subtotal)
        self.assertEqual(nhia_invoice.items.first().unit_price, expected_nhia_subtotal)