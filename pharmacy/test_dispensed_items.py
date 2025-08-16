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

class DispensedItemsTrackerTestCase(TestCase):

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

        self.patient = Patient.objects.create(first_name='Test', last_name='Patient', date_of_birth='1995-01-01', gender='M', phone_number='+1234567890', address='123 Test St', city='Test City', state='Test State', country='Test Country')
        self.category = MedicationCategory.objects.create(name='Test Category')
        self.medication = Medication.objects.create(name='Test Medication', price=Decimal('50.00'), category=self.category)
        self.dispensary = Dispensary.objects.create(name='Test Dispensary')
        self.service = Service.objects.create(name='Medication Dispensing', tax_percentage=Decimal('0.00'), price=Decimal('0.00'))

    def test_dispensed_items_tracker_view(self):
        # Test that the dispensed items tracker page loads
        response = self.client.get(reverse('pharmacy:dispensed_items_tracker'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dispensed Items Tracker')

    def test_dispensed_items_tracker_with_data(self):
        # Create a prescription
        prescription = Prescription.objects.create(
            patient=self.patient,
            doctor=self.user,
            prescription_date=timezone.now().date(),
            diagnosis='Test Diagnosis'
        )
        
        # Create a prescription item
        prescription_item = PrescriptionItem.objects.create(
            prescription=prescription,
            medication=self.medication,
            dosage='1 tablet',
            frequency='Twice a day',
            duration='5 days',
            instructions='After meals',
            quantity=2
        )
        
        # Create a dispensing log
        dispensing_log = DispensingLog.objects.create(
            prescription_item=prescription_item,
            dispensed_by=self.user,
            dispensed_quantity=2,
            unit_price_at_dispense=self.medication.price,
            total_price_for_this_log=self.medication.price * 2,
            dispensary=self.dispensary
        )
        
        # Test that the dispensed items tracker page loads with data
        response = self.client.get(reverse('pharmacy:dispensed_items_tracker'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Medication')
        
        # Test detail view
        response = self.client.get(reverse('pharmacy:dispensed_item_detail', args=[dispensing_log.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Medication')
        
        # Test export view
        response = self.client.get(reverse('pharmacy:dispensed_items_export'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_dispensed_items_search_functionality(self):
        # Create test data
        patient2 = Patient.objects.create(first_name='Another', last_name='Patient', date_of_birth='1990-01-01', gender='F', phone_number='+1234567892', address='456 Test Ave', city='Test City', state='Test State', country='Test Country')
        
        medication2 = Medication.objects.create(name='Another Medication', price=Decimal('75.00'), category=self.category)
        
        # Create prescriptions
        prescription1 = Prescription.objects.create(
            patient=self.patient,
            doctor=self.user,
            prescription_date=timezone.now().date(),
            diagnosis='Test Diagnosis'
        )
        
        prescription2 = Prescription.objects.create(
            patient=patient2,
            doctor=self.user,
            prescription_date=timezone.now().date(),
            diagnosis='Another Diagnosis'
        )
        
        # Create prescription items
        prescription_item1 = PrescriptionItem.objects.create(
            prescription=prescription1,
            medication=self.medication,
            dosage='1 tablet',
            frequency='Twice a day',
            duration='5 days',
            instructions='After meals',
            quantity=2
        )
        
        prescription_item2 = PrescriptionItem.objects.create(
            prescription=prescription2,
            medication=medication2,
            dosage='2 tablets',
            frequency='Once a day',
            duration='10 days',
            instructions='Before meals',
            quantity=5
        )
        
        # Create dispensing logs
        dispensing_log1 = DispensingLog.objects.create(
            prescription_item=prescription_item1,
            dispensed_by=self.user,
            dispensed_quantity=2,
            unit_price_at_dispense=self.medication.price,
            total_price_for_this_log=self.medication.price * 2,
            dispensary=self.dispensary
        )
        
        dispensing_log2 = DispensingLog.objects.create(
            prescription_item=prescription_item2,
            dispensed_by=self.user,
            dispensed_quantity=5,
            unit_price_at_dispense=medication2.price,
            total_price_for_this_log=medication2.price * 5,
            dispensary=self.dispensary
        )
        
        # Test search by medication name
        response = self.client.get(reverse('pharmacy:dispensed_items_tracker'), {'medication_name': 'Test Medication'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Medication')
        self.assertNotContains(response, 'Another Medication')
        
        # Test search by patient name
        response = self.client.get(reverse('pharmacy:dispensed_items_tracker'), {'patient_name': 'Another'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Another Medication')
        self.assertNotContains(response, 'Test Medication')
        
        # Test search by quantity range
        response = self.client.get(reverse('pharmacy:dispensed_items_tracker'), {'min_quantity': 3})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Another Medication')
        self.assertNotContains(response, 'Test Medication')
        
        # Test search by category
        response = self.client.get(reverse('pharmacy:dispensed_items_tracker'), {'category': self.category.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Medication')
        self.assertContains(response, 'Another Medication')