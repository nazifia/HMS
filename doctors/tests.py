from django.test import TestCase
from django.urls import reverse

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


class EditDoctorViewTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            phone_number="08000000009", username="admin", password="x"
        )
        self.client.force_login(self.admin)
        self.doctor = Doctor.objects.create(
            user=CustomUser.objects.create_user(
                phone_number="08000000010",
                username="doc",
                password="x",
                first_name="Ada",
                last_name="Obi",
            ),
            license_number="LIC-3",
            experience="0-2",
            qualification="MBBS",
        )
        self.url = reverse("doctors:edit_doctor", args=[self.doctor.pk])

    def test_page_renders_every_required_field(self):
        """A field missing from the template can never be submitted, so the POST
        fails validation with an error the page has nowhere to show."""
        html = self.client.get(self.url).content.decode()
        missing = [
            name
            for name, field in DoctorForm().fields.items()
            if field.required and f'name="{name}"' not in html
        ]
        self.assertEqual(missing, [])

    def test_post_saves_doctor_and_user(self):
        response = self.client.post(
            self.url,
            {
                "first_name": "Ada",
                "last_name": "Okoro",
                "email": "ada@example.com",
                "phone_number": "08000000010",
                "license_number": "LIC-3b",
                "experience": "3-5",
                "qualification": "MBBS, FMCP",
                "consultation_fee": "5000",
            },
        )
        self.assertRedirects(response, reverse("doctors:manage_doctors"))
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.license_number, "LIC-3b")
        self.assertEqual(self.doctor.experience, "3-5")
        self.assertEqual(self.doctor.user.last_name, "Okoro")

    def test_invalid_post_reports_an_error(self):
        response = self.client.post(self.url, {"first_name": "Ada"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please correct the errors below.")
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.license_number, "LIC-3")
