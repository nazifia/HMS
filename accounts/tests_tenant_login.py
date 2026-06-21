"""Login gate: hospital staff may only authenticate on their own subdomain."""
from types import SimpleNamespace

from django.test import TestCase

from accounts.backends import PhoneNumberBackend
from accounts.models import CustomUser
from saas.models import Hospital


class TenantLoginGateTest(TestCase):
    def setUp(self):
        self.backend = PhoneNumberBackend()
        self.h1 = Hospital.objects.create(name="H1", subdomain="h1")
        self.h2 = Hospital.objects.create(name="H2", subdomain="h2")
        self.staff = CustomUser.objects.create_user(
            phone_number="111", username="staff1", password="pw", hospital=self.h1
        )
        self.platform = CustomUser.objects.create_user(
            phone_number="999", username="ops", password="pw", hospital=None
        )

    def _req(self, hospital, path="/"):
        return SimpleNamespace(hospital=hospital, path=path)

    def auth(self, req):
        return self.backend.authenticate(req, username="111", password="pw")

    def test_staff_allowed_on_own_subdomain(self):
        assert self.auth(self._req(self.h1)) == self.staff

    def test_staff_blocked_on_other_subdomain(self):
        assert self.auth(self._req(self.h2)) is None

    def test_staff_blocked_on_base_domain(self):
        assert self.auth(self._req(None)) is None

    def test_platform_user_allowed_anywhere(self):
        req = self._req(self.h1)
        u = self.backend.authenticate(req, username="999", password="pw")
        assert u == self.platform
        assert self.backend.authenticate(self._req(None), username="999", password="pw") == self.platform
