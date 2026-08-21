"""A hospital's own admin reaches every feature of that hospital — and only
that hospital's rows."""
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from django.contrib.messages.storage.fallback import FallbackStorage

from django.http import Http404

from accounts.models import CustomUser, Role
from accounts.permissions import is_tenant_admin, user_has_permission
from accounts.views import get_manageable_user
from core.decorators import role_required
from saas.models import Hospital


def _request(user):
    req = RequestFactory().get("/")
    req.user = user
    req.session = {}
    setattr(req, "_messages", FallbackStorage(req))
    return req


class TenantAdminAccessTest(TestCase):
    def setUp(self):
        self.h1 = Hospital.objects.create(name="H1", subdomain="h1")
        self.admin_role = Role.objects.create(name="admin")
        self.nurse_role = Role.objects.create(name="nurse")

        self.admin = CustomUser.objects.create_user(
            phone_number="100", username="adm", password="pw", hospital=self.h1
        )
        self.admin.roles.add(self.admin_role)
        self.nurse = CustomUser.objects.create_user(
            phone_number="200", username="nur", password="pw", hospital=self.h1
        )
        self.nurse.roles.add(self.nurse_role)

    def test_admin_is_tenant_admin_nurse_is_not(self):
        self.assertTrue(is_tenant_admin(self.admin))
        self.assertFalse(is_tenant_admin(self.nurse))

    def test_admin_has_every_permission(self):
        self.assertTrue(user_has_permission(self.admin, "pharmacy.dispense"))
        self.assertFalse(user_has_permission(self.nurse, "pharmacy.dispense"))

    def test_admin_passes_django_has_perm(self):
        # A permission nobody granted: only the tenant-admin backend can say yes.
        perm = Permission.objects.first()
        codename = f"{perm.content_type.app_label}.{perm.codename}"
        self.assertTrue(self.admin.has_perm(codename))
        self.assertFalse(self.nurse.has_perm(codename))

    def test_admin_passes_role_gate_for_a_role_it_does_not_hold(self):
        @role_required(["pharmacist"])
        def view(request):
            return "ok"

        self.assertEqual(view(_request(self.admin)), "ok")
        self.assertNotEqual(view(_request(self.nurse)), "ok")

    def test_admin_is_not_cross_tenant(self):
        # Full function, one hospital: the admin flag must never imply superuser.
        self.assertFalse(self.admin.is_superuser)
        self.assertEqual(self.admin.hospital, self.h1)


class ManageableUserTest(TestCase):
    """Staff administration is open to a hospital admin, but only over that
    hospital's own people."""

    def setUp(self):
        self.h1 = Hospital.objects.create(name="H1", subdomain="h1")
        self.h2 = Hospital.objects.create(name="H2", subdomain="h2")
        Role.objects.create(name="admin")

        self.admin = CustomUser.objects.create_user(
            phone_number="100", username="adm", password="pw", hospital=self.h1
        )
        self.admin.roles.add(Role.objects.get(name="admin"))
        self.colleague = CustomUser.objects.create_user(
            phone_number="101", username="nurse1", password="pw", hospital=self.h1
        )
        self.outsider = CustomUser.objects.create_user(
            phone_number="200", username="nurse2", password="pw", hospital=self.h2
        )
        self.platform = CustomUser.objects.create_superuser(
            phone_number="900", username="ops", password="pw"
        )

    def _as(self, user):
        req = RequestFactory().get("/")
        req.user = user
        return req

    def test_admin_may_manage_own_hospital_staff(self):
        from saas.current import set_current_hospital

        set_current_hospital(self.h1)
        try:
            got = get_manageable_user(self._as(self.admin), self.colleague.id)
            self.assertEqual(got, self.colleague)

            # Another hospital's staff: not visible through tenant_objects.
            with self.assertRaises(Http404):
                get_manageable_user(self._as(self.admin), self.outsider.id)

            # Platform accounts sit above the tenant, so they stay off limits.
            with self.assertRaises(Http404):
                get_manageable_user(self._as(self.admin), self.platform.id)
        finally:
            set_current_hospital(None)

    def test_superuser_may_manage_anyone(self):
        req = self._as(self.platform)
        self.assertEqual(get_manageable_user(req, self.colleague.id), self.colleague)
        self.assertEqual(get_manageable_user(req, self.outsider.id), self.outsider)
