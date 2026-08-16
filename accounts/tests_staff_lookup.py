"""The staff picker behind "choose a doctor".

It has to work for the people who actually book appointments — reception,
nurses, doctors — none of whom hold users.view, while still not turning into a
back door onto the admin-only user API.
"""
from django.test import Client, TestCase, override_settings

from accounts.models import CustomUser, Role


@override_settings(STRICT_ACCESS_CONTROL=True)
class StaffLookupTest(TestCase):
    def setUp(self):
        self.doctor = self.staff(
            "08015000001", "drchike", "doctor", "Chike", "Obi",
        )
        self.nurse = self.staff(
            "08015000002", "nursebisi", "nurse", "Bisi", "Ade",
        )
        self.receptionist = self.staff(
            "08015000003", "frontdesk", "receptionist", "Ken", "Uba",
        )
        self.auth = self.token_for("08015000003")

    def staff(self, phone, username, role_name, first, last):
        user = CustomUser.objects.create_user(
            phone_number=phone, username=username, password="pw12345",
            first_name=first, last_name=last,
        )
        role, _ = Role.objects.get_or_create(name=role_name)
        user.roles.add(role)
        return user

    def token_for(self, phone):
        response = Client().post(
            "/api/accounts/login/",
            {"phone_number": phone, "password": "pw12345"},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        return {"HTTP_AUTHORIZATION": f"Token {response.json()['token']}"}

    def test_receptionist_can_list_staff(self):
        response = self.client.get("/api/accounts/staff/", **self.auth)
        assert response.status_code == 200, response.content
        names = {row["username"] for row in response.json()}
        assert {"drchike", "nursebisi", "frontdesk"} <= names

    def test_role_filter_returns_only_that_role(self):
        response = self.client.get("/api/accounts/staff/?role=doctor", **self.auth)
        assert response.status_code == 200, response.content
        rows = response.json()
        assert [row["username"] for row in rows] == ["drchike"]
        assert rows[0]["full_name"] == "Chike Obi"
        assert rows[0]["role"] == "doctor"

    def test_search_matches_name_and_username(self):
        for term in ("chike", "obi", "drchike"):
            rows = self.client.get(
                f"/api/accounts/staff/?role=doctor&search={term}", **self.auth
            ).json()
            assert [row["username"] for row in rows] == ["drchike"], term

    def test_inactive_staff_hidden(self):
        self.doctor.is_active = False
        self.doctor.save()
        rows = self.client.get("/api/accounts/staff/?role=doctor", **self.auth).json()
        assert rows == []

    def test_no_contact_details_leak(self):
        rows = self.client.get("/api/accounts/staff/", **self.auth).json()
        leaked = set(rows[0]) & {
            "phone_number", "email", "password", "is_superuser", "is_staff",
            "profile", "roles",
        }
        assert not leaked, leaked

    def test_unauthenticated_is_refused_in_json(self):
        # DRF answers this one (the path skips the module gate), and with
        # SessionAuthentication first in the list that is a 403, not a 401.
        response = self.client.get("/api/accounts/staff/")
        assert response.status_code in (401, 403), response.status_code
        assert response["content-type"].startswith("application/json")

    def test_admin_user_api_stays_admin_only(self):
        """The picker must not become a way around UserViewSet's gate."""
        response = self.client.get("/api/accounts/users/", **self.auth)
        assert response.status_code == 403, response.status_code
