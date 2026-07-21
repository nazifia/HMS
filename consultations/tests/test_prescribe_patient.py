"""Doctors can prescribe straight from a patient's detail page, no consultation needed."""

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.models import CustomUser
from consultations.views import prescribe_patient
from patients.models import Patient
from pharmacy.models import Prescription


class PrescribePatientTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        # Superuser passes the permission decorator without seeding role permissions.
        self.doctor = CustomUser.objects.create_superuser(
            username="doc", password="x", phone_number="08000000001"
        )
        self.patient = Patient.objects.create(
            first_name="Jane",
            last_name="Doe",
            date_of_birth="1985-05-15",
            gender="F",
            address="1 Test Street",
            city="Testville",
            state="Teststate",
        )

    def _post(self):
        request = self.factory.post(
            reverse("consultations:prescribe_patient", args=[self.patient.id])
        )
        request.user = self.doctor
        request.session = {}
        setattr(request, "_messages", FallbackStorage(request))
        return prescribe_patient(request, self.patient.id)

    def test_creates_prescription_without_consultation(self):
        response = self._post()
        prescription = Prescription.objects.get(patient=self.patient)
        self.assertEqual(prescription.doctor, self.doctor)
        self.assertIsNone(prescription.consultation)
        self.assertEqual(prescription.status, "pending")
        self.assertEqual(
            response["Location"],
            reverse("pharmacy:prescription_detail", args=[prescription.id]),
        )

    def test_get_is_rejected(self):
        request = self.factory.get(
            reverse("consultations:prescribe_patient", args=[self.patient.id])
        )
        request.user = self.doctor
        response = prescribe_patient(request, self.patient.id)
        self.assertEqual(response.status_code, 405)
        self.assertFalse(Prescription.objects.exists())
