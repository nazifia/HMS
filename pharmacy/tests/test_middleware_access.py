"""Doctors must not reach the pharmacy module through prescription permissions."""

from django.test import SimpleTestCase, RequestFactory

from pharmacy.middleware import PharmacyAccessMiddleware


class _Roles:
    def __init__(self, names):
        self._names = names

    def values_list(self, *_args, **_kwargs):
        return self._names


class _StubUser:
    """ponytail: no DB — middleware only touches these attributes."""

    is_authenticated = True
    is_superuser = False
    profile = None
    username = "stub"

    def __init__(self, role, perms):
        self.roles = _Roles([role])
        self._perms = set(perms)

    def has_perm(self, perm):
        return perm in self._perms

    def is_pharmacist(self):
        return "pharmacist" in self.roles.values_list("name", flat=True)

    def get_assigned_dispensary(self):
        return None


DOCTOR_PERMS = [
    "pharmacy.view_prescription",
    "pharmacy.add_prescription",
    "pharmacy.change_prescription",
]


class PharmacyAccessMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = PharmacyAccessMiddleware(lambda r: "PASSED")

    def _run(self, path, user):
        request = self.factory.get(path)
        request.user = user
        request.session = {}
        # messages framework needs a backend; middleware only calls messages.error
        setattr(request, "_messages", type("M", (), {"add": lambda *a, **k: None})())
        return self.middleware(request)

    def test_doctor_blocked_from_pharmacy_inventory(self):
        user = _StubUser("doctor", DOCTOR_PERMS)
        response = self._run("/pharmacy/inventory/", user)
        self.assertNotEqual(response, "PASSED")
        self.assertEqual(response.status_code, 302)

    def test_doctor_allowed_on_prescriptions(self):
        user = _StubUser("doctor", DOCTOR_PERMS)
        self.assertEqual(self._run("/pharmacy/prescriptions/", user), "PASSED")

    def test_strict_middleware_maps_prescriptions_off_pharmacy_view(self):
        from accounts.strict_access_control import StrictAccessControlMiddleware

        strict = StrictAccessControlMiddleware(lambda r: None)
        self.assertEqual(
            strict._get_required_permission(self.factory.get("/pharmacy/prescriptions/")),
            "prescriptions.view",
        )
        self.assertEqual(
            strict._get_required_permission(self.factory.get("/pharmacy/inventory/")),
            "pharmacy.view",
        )

    def test_pharmacist_still_allowed(self):
        user = _StubUser("pharmacist", ["pharmacy.view_dispensary"])
        # No assigned dispensary -> redirected to selection, but not role-denied.
        response = self._run("/pharmacy/inventory/", user)
        self.assertEqual(response.status_code, 302)
        self.assertIn("dispensary", response.url)
