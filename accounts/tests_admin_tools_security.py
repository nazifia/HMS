"""Guards on the two admin tools that reach outside the ORM.

- the superuser log reader interpolates a client-supplied path into open()
- the admin user API writes is_staff / is_superuser from client-supplied JSON
"""

import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser, CustomUserProfile
from saas.models import Hospital, Plan, Subscription


class LogFileTraversalTest(TestCase):
    def setUp(self):
        self.url = reverse("accounts:superuser_read_log_file")
        self.admin = CustomUser.objects.create_superuser(
            phone_number="08000000010", username="root", password="pw"
        )
        self.client.force_login(self.admin)

    def _read(self, path):
        return self.client.post(
            self.url, {"file_path": path}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def test_traversal_out_of_the_log_directory_is_refused(self):
        from django.conf import settings

        escaped = str(settings.BASE_DIR) + "/logs/../manage.py"
        self.assertEqual(self._read(escaped).status_code, 403)

    def test_non_log_extension_is_refused(self):
        from django.conf import settings

        self.assertEqual(self._read(str(settings.BASE_DIR) + "/.env").status_code, 403)


class AdminUserApiPrivilegeTest(TestCase):
    """A hospital admin passes is_admin() but must not mint platform accounts."""

    def setUp(self):
        self.hospital = Hospital.objects.create(name="H", subdomain="h")
        Subscription.objects.create(
            hospital=self.hospital,
            plan=Plan.objects.create(name="P", price=0),
            status="active",
            current_period_end=timezone.now() + timedelta(days=30),
        )
        self.admin = CustomUser.objects.create_user(
            phone_number="08000000011",
            username="hospadmin",
            password="pw",
            hospital=self.hospital,
        )
        CustomUserProfile.objects.update_or_create(
            user=self.admin, defaults={"role": "admin"}
        )
        self.target = CustomUser.objects.create_user(
            phone_number="08000000012",
            username="target",
            password="pw",
            hospital=self.hospital,
        )
        self.client.force_login(self.admin)

    def test_hospital_admin_cannot_grant_superuser(self):
        response = self.client.put(
            reverse("core:api_admin_user_detail", args=[self.target.id]),
            data=json.dumps({"is_superuser": True, "is_staff": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_superuser)
        self.assertFalse(self.target.is_staff)

    def test_hospital_admin_cannot_create_a_superuser(self):
        self.client.post(
            reverse("core:api_admin_users"),
            data=json.dumps(
                {
                    "username": "sneaky",
                    "phone_number": "08000000013",
                    "first_name": "S",
                    "last_name": "S",
                    "is_superuser": True,
                }
            ),
            content_type="application/json",
        )
        created = CustomUser.objects.filter(username="sneaky").first()
        self.assertIsNotNone(created)
        self.assertFalse(created.is_superuser)
