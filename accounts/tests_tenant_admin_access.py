"""A hospital's own admin reaches every feature of that hospital — and only
that hospital's rows."""
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from django.contrib.messages.storage.fallback import FallbackStorage

from accounts.models import CustomUser, Role
from accounts.permissions import is_tenant_admin, user_has_permission
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
