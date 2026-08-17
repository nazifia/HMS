from django.test import TestCase

from accounts.models import CustomUser

from .forms import DoctorForm
from .models import Doctor


class DoctorFormLicenseUniquenessTests(TestCase):
    """license_number is unique in the DB; the form must catch clashes itself."""

    def setUp(self):
        self.existing_user = CustomUser.objects.create_user(
            phone_number="08000000001", username="doc1", password="x"
        )
        self.existing = Doctor.objects.create(
            user=self.existing_user,
            license_number="LIC-1",
            experience="0-2",
            qualification="MBBS",
        )

    def _data(self, **overrides):
        data = {
            "license_number": "LIC-1",
            "experience": "0-2",
            "qualification": "MBBS",
            "consultation_fee": "0",
        }
        data.update(overrides)
        return data

    def test_duplicate_license_is_a_form_error(self):
        form = DoctorForm(data=self._data())
        self.assertFalse(form.is_valid())
        self.assertIn("license_number", form.errors)

    def test_blank_license_is_a_form_error(self):
        form = DoctorForm(data=self._data(license_number=""))
        self.assertFalse(form.is_valid())
        self.assertIn("license_number", form.errors)

    def test_editing_own_record_keeps_its_license(self):
        form = DoctorForm(data=self._data(), instance=self.existing)
        self.assertTrue(form.is_valid(), form.errors)


class DoctorFormRequiredFieldTests(TestCase):
    """experience and qualification are non-blank on the model."""

    def _data(self, **overrides):
        data = {
            "license_number": "LIC-2",
            "experience": "0-2",
            "qualification": "MBBS",
            "consultation_fee": "0",
        }
        data.update(overrides)
        return data

    def test_blank_experience_is_a_form_error(self):
        form = DoctorForm(data=self._data(experience=""))
        self.assertFalse(form.is_valid())
        self.assertIn("experience", form.errors)

    def test_blank_qualification_is_a_form_error(self):
        form = DoctorForm(data=self._data(qualification=""))
        self.assertFalse(form.is_valid())
        self.assertIn("qualification", form.errors)

    def test_experience_outside_choices_is_a_form_error(self):
        form = DoctorForm(data=self._data(experience="99+"))
        self.assertFalse(form.is_valid())
        self.assertIn("experience", form.errors)

    def test_complete_data_is_valid(self):
        form = DoctorForm(data=self._data())
        self.assertTrue(form.is_valid(), form.errors)
