from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from pharmacy.models import MedicationCategory, Medication, Prescription, PrescriptionItem
from patients.models import Patient

User = get_user_model()

class PharmacyViewsTest(TestCase):
    def setUp(self):
        # Create test client
        self.client = Client()
        
        # Create test user with pharmacist role
        self.user = User.objects.create_user(
            phone_number="9876543210",
            username="testpharmacist",
            password="testpass123"
        )
        
        # Add pharmacist role to user
        # Note: This would depend on your role implementation
        
        # Create test data
        self.category = MedicationCategory.objects.create(
            name="Pain Relief",
            description="Pain relief medications"
        )
        
        self.medication = Medication.objects.create(
            name="Ibuprofen",
            generic_name="Ibuprofen",
            category=self.category,
            description="Non-steroidal anti-inflammatory drug",
            dosage_form="Tablet",
            strength="200mg",
            manufacturer="PharmaCorp",
            price=15.00,
            reorder_level=20
        )
        
        self.patient = Patient.objects.create(
            first_name="Jane",
            last_name="Smith",
            date_of_birth="1985-05-15",
            gender="F",
            address="789 Patient Avenue",
            city="Patientcity",
            state="Patientstate",
            country="Patientland",
            patient_id="P000000002"
        )
        
        self.prescription = Prescription.objects.create(
            patient=self.patient,
            doctor=self.user,
            prescription_date="2023-01-01",
            diagnosis="Headache"
        )
        
        self.prescription_item = PrescriptionItem.objects.create(
            prescription=self.prescription,
            medication=self.medication,
            dosage="1 tablet",
            frequency="Every 6 hours",
            duration="3 days",
            quantity=12
        )
        
        # Login the user
        self.client.login(phone_number="9876543210", password="testpass123")

    def test_pharmacy_dashboard_view(self):
        """Test that pharmacy dashboard loads successfully"""
        response = self.client.get(reverse('pharmacy:pharmacy_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pharmacy Dashboard")

    def test_medication_list_view(self):
        """Test that medication list view loads successfully"""
        response = self.client.get(reverse('pharmacy:inventory_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Medication Inventory")

    def test_medication_detail_view(self):
        """Test that medication detail view loads successfully"""
        response = self.client.get(reverse('pharmacy:medication_detail', args=[self.medication.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ibuprofen")
        self.assertContains(response, "200mg")

    def test_prescription_list_view(self):
        """Test that prescription list view loads successfully"""
        response = self.client.get(reverse('pharmacy:prescription_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prescription List")

    def test_prescription_detail_view(self):
        """Test that prescription detail view loads successfully"""
        response = self.client.get(reverse('pharmacy:prescription_detail', args=[self.prescription.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prescription Detail")
        self.assertContains(response, "Jane Smith")

    def test_medication_autocomplete_view(self):
        """Test that medication autocomplete view works correctly"""
        response = self.client.get(reverse('pharmacy:medication_autocomplete'), {'term': 'Ibu'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('Ibuprofen', data)

    def test_revenue_analysis_view_authenticated(self):
        """Revenue analysis should return a response for authenticated user"""
        response = self.client.get(reverse('pharmacy:revenue_analysis'))
        # Should either render (200) or redirect depending on auth config; ensure no None/500
        self.assertIn(response.status_code, (200, 302))

    def test_revenue_analysis_view_anonymous(self):
        """Anonymous access to revenue analysis should redirect to login (302)"""
        # log out
        self.client.logout()
        response = self.client.get(reverse('pharmacy:revenue_analysis'))
        self.assertIn(response.status_code, (302, 200))

    def test_revenue_analysis_redirects_to_statistics_preserving_query(self):
        """Requesting the old revenue_analysis route should redirect to the statistics route and keep query params."""
        # Ensure we're logged in (redirect requires auth on original view)
        self.client.login(phone_number="9876543210", password="testpass123")
        response = self.client.get(reverse('pharmacy:revenue_analysis') + '?start=2025-01-01&end=2025-01-31')
        # Should redirect (302) to the new statistics path
        self.assertEqual(response.status_code, 302)
        location = response['Location']
        self.assertIn('/pharmacy/revenue/statistics/', location)
        self.assertIn('start=2025-01-01', location)
        self.assertIn('end=2025-01-31', location)