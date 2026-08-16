"""Denials aimed at API clients must be JSON, not an HTML redirect.

Access control runs in middleware, before DRF. When it refuses a request it has
to answer in the caller's language: a mobile client that follows a 302 to the
login page sees a 200 full of markup and cannot tell it was denied.
"""
from django.test import TestCase, override_settings

from accounts.models import CustomUser, Role
from pharmacy.models import Dispensary


@override_settings(STRICT_ACCESS_CONTROL=True)
class ApiDenialTest(TestCase):
    def test_unauthenticated_api_request_gets_401_json(self):
        response = self.client.get("/pharmacy/api/medications/")
        assert response.status_code == 401, response.status_code
        assert response["content-type"].startswith("application/json")
        assert response.json()["error"] == "Authentication required"

    def test_unauthenticated_browser_request_still_redirects(self):
        response = self.client.get("/pharmacy/dashboard/")
        assert response.status_code == 302, response.status_code
        assert "/accounts/login/" in response["location"]

    def test_wrong_role_gets_403_json_with_reason(self):
        # A lab technician holds no pharmacy role. PharmacyAccessMiddleware
        # refuses first (it runs before StrictAccessControl's process_view),
        # so the reason names the module rather than the permission.
        user = CustomUser.objects.create_user(
            phone_number="08019000001", username="labguy", password="pw12345",
        )
        role, _ = Role.objects.get_or_create(name="lab_technician")
        user.roles.add(role)
        token = self.client.post(
            "/api/accounts/login/",
            {"phone_number": "08019000001", "password": "pw12345"},
            content_type="application/json",
        ).json()["token"]

        response = self.client.get(
            "/pharmacy/api/medications/", HTTP_AUTHORIZATION=f"Token {token}"
        )
        assert response.status_code == 403, response.status_code
        assert response["content-type"].startswith("application/json")
        assert "Pharmacy module" in response.json()["detail"], response.content

    def test_pharmacist_without_dispensary_gets_json_not_redirect(self):
        """PharmacyAccessMiddleware's own refusal, the second gate."""
        Dispensary.objects.create(name="Main")
        user = CustomUser.objects.create_user(
            phone_number="08019000002", username="newpharm", password="pw12345",
        )
        role, _ = Role.objects.get_or_create(name="pharmacist")
        user.roles.add(role)
        token = self.client.post(
            "/api/accounts/login/",
            {"phone_number": "08019000002", "password": "pw12345"},
            content_type="application/json",
        ).json()["token"]

        response = self.client.get(
            "/pharmacy/api/medications/", HTTP_AUTHORIZATION=f"Token {token}"
        )
        assert response["content-type"].startswith("application/json"), (
            response.status_code, response["content-type"],
        )
        assert response.status_code in (200, 403), response.status_code
        if response.status_code == 403:
            assert "dispensary" in response.json()["detail"].lower()

    def test_accept_json_header_is_enough(self):
        response = self.client.get(
            "/pharmacy/dashboard/", HTTP_ACCEPT="application/json"
        )
        assert response.status_code == 401, response.status_code
        assert response["content-type"].startswith("application/json")
