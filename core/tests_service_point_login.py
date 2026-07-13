"""Smoke tests: service-point sign-in flow for desk staff."""
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from core.models import ServicePoint


class ServicePointLoginTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="recep1", phone_number="08011112222", password="pass12345"
        )
        profile = self.user.profile
        profile.role = "receptionist"
        profile.save()
        self.point_a = ServicePoint.objects.create(name="Front Desk A", point_type="reception")
        self.point_b = ServicePoint.objects.create(name="Front Desk B", point_type="reception")

    def _login(self):
        return self.client.post(
            reverse("accounts:login"),
            {"username": "08011112222", "password": "pass12345"},
        )

    def test_login_without_points_goes_to_dashboard(self):
        response = self._login()
        self.assertNotIn("selected_service_point_id", self.client.session)
        self.assertEqual(response.url, reverse("dashboard:dashboard"))

    def test_login_with_one_point_auto_selects(self):
        self.point_a.staff.add(self.user)
        response = self._login()
        self.assertEqual(response.url, reverse("core:select_service_point"))
        response = self.client.get(response.url)
        self.assertEqual(self.client.session["selected_service_point_id"], self.point_a.id)

    def test_login_with_two_points_shows_chooser_then_sets_session(self):
        self.point_a.staff.add(self.user)
        self.point_b.staff.add(self.user)
        response = self._login()
        self.assertEqual(response.url, reverse("core:select_service_point"))
        response = self.client.get(response.url)
        self.assertContains(response, "Front Desk A")
        response = self.client.post(
            reverse("core:select_service_point"),
            {"service_point_id": self.point_b.id},
        )
        self.assertEqual(self.client.session["selected_service_point_id"], self.point_b.id)

    def test_register_patient_requires_desk_when_assigned(self):
        self.point_a.staff.add(self.user)
        self.point_b.staff.add(self.user)
        self._login()  # two points: nothing auto-selected yet
        response = self.client.get(reverse("patients:register"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("core:select_service_point"), response.url)
        # After choosing a desk, registration opens normally.
        self.client.post(
            reverse("core:select_service_point"), {"service_point_id": self.point_a.id}
        )
        response = self.client.get(reverse("patients:register"))
        self.assertEqual(response.status_code, 200)

    def test_cannot_select_unassigned_point(self):
        self.point_a.staff.add(self.user)
        self.point_b.staff.add(self.user)
        self._login()
        other = ServicePoint.objects.create(name="Cash Desk", point_type="billing")
        self.client.post(
            reverse("core:select_service_point"), {"service_point_id": other.id}
        )
        self.assertNotEqual(
            self.client.session.get("selected_service_point_id"), other.id
        )
