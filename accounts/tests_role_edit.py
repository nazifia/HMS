"""Role edit template must submit checked permissions and the view must persist
them on the role (name="permissions" checkboxes -> RoleForm -> role.permissions)."""
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser, Role


class RoleEditPermissionSaveTest(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            phone_number="9000", username="rootadmin", password="pw"
        )
        self.role = Role.objects.create(name="Test Role X")
        self.perm = Permission.objects.order_by("id").first()
        self.client.force_login(self.admin)
        self.url = reverse("accounts:edit_role", args=[self.role.id])

    def test_template_renders_checkbox_with_form_field_name(self):
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        content = resp.content.decode()
        assert 'name="permissions"' in content
        assert f'value="{self.perm.id}"' in content

    def test_checked_permission_is_saved_to_role(self):
        resp = self.client.post(
            self.url,
            {
                "name": "Test Role X",
                "description": "",
                "parent": "",
                "permissions": [self.perm.id],
            },
        )
        assert resp.status_code == 302, getattr(resp, "context", None) and resp.context["form"].errors
        assert self.perm in self.role.permissions.all()

    def test_unchecking_removes_permission(self):
        self.role.permissions.add(self.perm)
        resp = self.client.post(
            self.url,
            {"name": "Test Role X", "description": "", "parent": "", "permissions": []},
        )
        assert resp.status_code == 302
        assert self.perm not in self.role.permissions.all()
