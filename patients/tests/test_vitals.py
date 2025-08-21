"""
Tests for patient vitals functionality
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from patients.models import Patient, Vitals
from patients.forms import VitalsForm
from patients.utils import get_safe_vitals_for_patient, get_latest_safe_vitals_for_patient
from django.db import connection

User = get_user_model()


class VitalsModelTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            gender="M",
            phone_number="1234567890"
        )

    def test_vitals_creation(self):
        """Test creating a vitals record"""
        vitals = Vitals.objects.create(
            patient=self.patient,
            temperature=Decimal('36.5'),
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            pulse_rate=72,
            height=Decimal('175.0'),
            weight=Decimal('70.0'),
            recorded_by="Dr. Smith"
        )
        self.assertEqual(vitals.patient, self.patient)
        self.assertEqual(vitals.temperature, Decimal('36.5'))
        self.assertEqual(vitals.pulse_rate, 72)

    def test_bmi_calculation(self):
        """Test BMI calculation"""
        vitals = Vitals.objects.create(
            patient=self.patient,
            height=Decimal('175.0'),  # 175 cm
            weight=Decimal('70.0'),   # 70 kg
            recorded_by="Dr. Smith"
        )
        # BMI = weight(kg) / (height(m))^2 = 70 / (1.75)^2 = 22.86
        expected_bmi = Decimal('22.86')
        self.assertEqual(vitals.bmi, expected_bmi)

    def test_bmi_calculation_with_zero_height(self):
        """Test BMI calculation with zero height"""
        vitals = Vitals(
            patient=self.patient,
            height=Decimal('0'),
            weight=Decimal('70.0'),
            recorded_by="Dr. Smith"
        )
        self.assertIsNone(vitals.calculate_bmi())


class VitalsFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='1234567890',
            username='testuser',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )

    def test_form_auto_population_with_user(self):
        """Test that recorded_by field is auto-populated with user's full name"""
        form = VitalsForm(user=self.user)
        self.assertEqual(form.fields['recorded_by'].initial, 'Test User')

    def test_form_auto_population_with_username_only(self):
        """Test auto-population with username when no full name"""
        user = User.objects.create_user(
            phone_number='9876543210',
            username='testuser2',
            password='testpass123'
        )
        form = VitalsForm(user=user)
        self.assertEqual(form.fields['recorded_by'].initial, 'testuser2')

    def test_form_without_user(self):
        """Test form creation without user"""
        form = VitalsForm()
        self.assertIsNone(form.fields['recorded_by'].initial)

    def test_form_validation(self):
        """Test form validation with valid data"""
        form_data = {
            'temperature': '36.5',
            'blood_pressure_systolic': '120',
            'blood_pressure_diastolic': '80',
            'pulse_rate': '72',
            'height': '175.0',
            'weight': '70.0',
            'recorded_by': 'Dr. Smith'
        }
        form = VitalsForm(data=form_data)
        self.assertTrue(form.is_valid())


class VitalsUtilsTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="Jane",
            last_name="Smith",
            date_of_birth="1985-05-15",
            gender="F",
            phone_number="9876543210"
        )

    def test_get_safe_vitals_for_patient(self):
        """Test safe vitals retrieval"""
        # Create valid vitals
        vitals1 = Vitals.objects.create(
            patient=self.patient,
            temperature=Decimal('36.5'),
            recorded_by="Dr. Smith"
        )
        vitals2 = Vitals.objects.create(
            patient=self.patient,
            temperature=Decimal('37.0'),
            recorded_by="Dr. Jones"
        )

        safe_vitals = get_safe_vitals_for_patient(self.patient)
        self.assertEqual(len(safe_vitals), 2)
        self.assertIn(vitals1, safe_vitals)
        self.assertIn(vitals2, safe_vitals)

    def test_get_latest_safe_vitals_for_patient(self):
        """Test getting latest safe vitals"""
        # Create vitals with different timestamps
        vitals1 = Vitals.objects.create(
            patient=self.patient,
            temperature=Decimal('36.5'),
            recorded_by="Dr. Smith",
            date_time=timezone.now() - timezone.timedelta(hours=2)
        )
        vitals2 = Vitals.objects.create(
            patient=self.patient,
            temperature=Decimal('37.0'),
            recorded_by="Dr. Jones",
            date_time=timezone.now()
        )

        latest_vitals = get_latest_safe_vitals_for_patient(self.patient)
        self.assertEqual(latest_vitals, vitals2)

    def test_get_safe_vitals_with_limit(self):
        """Test safe vitals retrieval with limit"""
        # Create multiple vitals
        for i in range(5):
            Vitals.objects.create(
                patient=self.patient,
                temperature=Decimal('36.5'),
                recorded_by=f"Dr. {i}"
            )

        safe_vitals = get_safe_vitals_for_patient(self.patient, limit=3)
        self.assertEqual(len(safe_vitals), 3)


class VitalsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            phone_number='1234567890',
            username='testuser',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            gender="M",
            phone_number="1234567890"
        )

    def test_vitals_view_requires_login(self):
        """Test that vitals view requires authentication"""
        url = reverse('patients:vitals', args=[self.patient.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_vitals_view_get(self):
        """Test GET request to vitals view"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('patients:vitals', args=[self.patient.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Patient Vitals')

    def test_vitals_view_post_valid_data(self):
        """Test POST request with valid vitals data"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('patients:vitals', args=[self.patient.id])
        
        form_data = {
            'temperature': '36.5',
            'blood_pressure_systolic': '120',
            'blood_pressure_diastolic': '80',
            'pulse_rate': '72',
            'height': '175.0',
            'weight': '70.0',
            'recorded_by': 'Test User'
        }
        
        response = self.client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful save
        
        # Check that vitals were created
        vitals = Vitals.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(vitals)
        self.assertEqual(vitals.temperature, Decimal('36.5'))
        self.assertEqual(vitals.recorded_by, 'Test User')

    def test_vitals_view_auto_populate_recorded_by(self):
        """Test that recorded_by is auto-populated when not provided"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('patients:vitals', args=[self.patient.id])
        
        form_data = {
            'temperature': '36.5',
            'pulse_rate': '72',
            # recorded_by is intentionally omitted
        }
        
        response = self.client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)
        
        # Check that recorded_by was auto-populated
        vitals = Vitals.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(vitals)
        # The recorded_by should be auto-populated with user's full name or username
        self.assertIn(vitals.recorded_by, ['Test User', 'testuser', 'System'])
