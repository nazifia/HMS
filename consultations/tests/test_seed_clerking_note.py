"""Saving a consultation lands its content in the clinical record."""

from django.test import TestCase

from accounts.models import CustomUser
from consultations.models import Consultation, SOAPNote
from consultations.views import seed_clerking_note
from patients.models import Patient


class SeedClerkingNoteTests(TestCase):
    def setUp(self):
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
        self.consultation = Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Headache x 3 days",
            symptoms="Throbbing, photophobia",
            diagnosis="Migraine",
            consultation_notes="Analgesia, review in 1 week",
        )

    def test_creates_note_from_consultation_fields(self):
        note = seed_clerking_note(self.consultation, self.doctor)
        self.assertEqual(note.presenting_complaint, "Headache x 3 days")
        self.assertEqual(note.history_of_presenting_complaint, "Throbbing, photophobia")
        self.assertEqual(note.provisional_diagnosis, "Migraine")
        self.assertEqual(note.management_plan, "Analgesia, review in 1 week")

    def test_does_not_duplicate_or_clobber_existing_note(self):
        SOAPNote.objects.create(
            consultation=self.consultation,
            created_by=self.doctor,
            presenting_complaint="Written by hand",
        )
        self.assertIsNone(seed_clerking_note(self.consultation, self.doctor))
        self.assertEqual(self.consultation.soap_notes.count(), 1)
