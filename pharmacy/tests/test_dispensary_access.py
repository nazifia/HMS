"""Hospital admins can pick any dispensary; pharmacists only assigned ones."""

from django.test import TestCase

from accounts.models import CustomUser, Role
from pharmacy.models import Dispensary
from saas.current import clear_current_hospital, set_current_hospital
from saas.models import Hospital


class DispensaryAccessTest(TestCase):
    def setUp(self):
        self.hospital = Hospital.objects.create(
            name="Health Care", subdomain="healthcare"
        )
        set_current_hospital(self.hospital)
        self.addCleanup(clear_current_hospital)
        self.dispensary = Dispensary.objects.create(
            name="Main Dispensary", hospital=self.hospital
        )

    def staff(self, phone, username, role_name):
        user = CustomUser.objects.create_user(
            phone_number=phone, username=username, password="pw12345"
        )
        role, _ = Role.objects.get_or_create(name=role_name)
        user.roles.add(role)
        return user

    def test_admin_sees_every_active_dispensary(self):
        admin = self.staff("08016000001", "hcadmin", "admin")
        self.assertEqual(admin.get_all_assigned_dispensaries(), [self.dispensary])
        self.assertTrue(admin.can_access_dispensary(self.dispensary))

    def test_unassigned_pharmacist_still_blocked(self):
        pharmacist = self.staff("08016000002", "pharm", "pharmacist")
        self.assertEqual(pharmacist.get_all_assigned_dispensaries(), [])
        self.assertFalse(pharmacist.can_access_dispensary(self.dispensary))
