"""Doctors must not create prescriptions from the pharmacy module."""

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from accounts.models import CustomUser
from pharmacy.views import no_doctor_prescribing


@no_doctor_prescribing
def _view(request):
    return "allowed"


class NoDoctorPrescribingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, user):
        request = self.factory.get("/pharmacy/prescriptions/create/")
        request.user = user
        request.session = {}
        setattr(request, "_messages", FallbackStorage(request))
        return request

    def _user(self, role, is_superuser=False):
        user = CustomUser(
            username=f"u-{role}-{is_superuser}", is_superuser=is_superuser
        )
        user._cached_roles = [role]
        return user

    def test_doctor_is_redirected(self):
        response = _view(self._request(self._user("doctor")))
        self.assertEqual(response.status_code, 302)

    def test_pharmacist_is_allowed(self):
        self.assertEqual(_view(self._request(self._user("pharmacist"))), "allowed")

    def test_superuser_is_allowed(self):
        self.assertEqual(
            _view(self._request(self._user("doctor", is_superuser=True))), "allowed"
        )
