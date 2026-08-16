"""Token auth for the Flutter client.

StrictAccessControlMiddleware runs in process_view, before DRF authenticates,
so without TokenAuthUserMiddleware every token request is redirected to the
HTML login page. These tests fail if that ordering breaks.
"""
from django.test import TestCase, override_settings

from accounts.models import CustomUser
from patients.models import Patient
from pharmacy.models import Prescription



@override_settings(STRICT_ACCESS_CONTROL=True)
class MobileTokenApiTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            phone_number="08010000001", username="mobiletest", password="pw12345",
        )

    def login(self):
        response = self.client.post(
            "/api/accounts/login/",
            {"phone_number": "08010000001", "password": "pw12345"},
            content_type="application/json",
        )
        assert response.status_code == 200, response.status_code
        return response.json()["token"]

    def test_login_returns_token(self):
        assert self.login()

    def test_bad_password_rejected(self):
        response = self.client.post(
            "/api/accounts/login/",
            {"phone_number": "08010000001", "password": "wrong"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_prescriptions_require_auth(self):
        # No credentials: must not hand back data.
        response = self.client.get("/pharmacy/api/prescriptions/")
        assert response.status_code != 200, response.status_code

    def test_prescriptions_with_token(self):
        patient = Patient.objects.create(
            first_name="Ada", last_name="Obi", date_of_birth="1990-01-01",
            gender="female", phone_number="08020000002",
        )
        Prescription.objects.create(patient=patient, doctor=self.user)

        response = self.client.get(
            "/pharmacy/api/prescriptions/",
            HTTP_AUTHORIZATION=f"Token {self.login()}",
        )
        assert response.status_code == 200, response.status_code
        row = response.json()["results"][0]
        assert row["patient_name"] == "Ada Obi"
        assert row["status_display"] == "Pending"

    def test_medication_stock_endpoint(self):
        from pharmacy.models import Medication, MedicationCategory

        category = MedicationCategory.objects.create(name="Analgesic")
        medication = Medication.objects.create(
            name="Paracetamol", category=category, dosage_form="tablet",
            strength="500mg", price=100,
        )
        response = self.client.get(
            f"/pharmacy/api/medications/{medication.id}/stock/",
            HTTP_AUTHORIZATION=f"Token {self.login()}",
        )
        assert response.status_code == 200, response.status_code
        assert isinstance(response.json(), list)
