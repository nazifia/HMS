"""Every permission a view checks must be grantable from /accounts/roles/.

A @permission_required('x.y') string is only satisfiable if it resolves (via
PERMISSION_MAPPING or directly) to a real auth.Permission row — that row is
what the role editor lists as a checkbox. Anything else silently locks the
view to superusers forever, no matter what an admin ticks in the UI.
"""

import os
import re

from django.contrib.auth.models import Permission
from django.test import TestCase

from accounts.permissions import PERMISSION_MAPPING

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "staticfiles", "__pycache__", "static"}
CHECK_CALL = re.compile(
    r'(?:permission_required|user_has_permission|has_permission)\(\s*[\'"]([\w.]+)[\'"]'
)
# ponytail: UI-element ids (core.ui_permission_required) and test fixtures use
# the same call shape but are not auth permissions. Exempt by name.
EXEMPT = {"btn_create_invoice", "menu_pharmacy", "create_patient", "test.permission", "x.y"}


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _checked_permissions():
    found = set()
    for root, dirs, files in os.walk(_repo_root()):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if not name.endswith((".py", ".html")):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8", errors="ignore") as fh:
                found.update(CHECK_CALL.findall(fh.read()))
    return found - EXEMPT


class PermissionsAreGrantableTests(TestCase):
    def test_every_checked_permission_has_a_permission_row(self):
        existing = {
            f"{app_label}.{codename}"
            for app_label, codename in Permission.objects.values_list(
                "content_type__app_label", "codename"
            )
        }
        unsatisfiable = sorted(
            perm
            for perm in _checked_permissions()
            if PERMISSION_MAPPING.get(perm, perm) not in existing
        )
        self.assertEqual(
            unsatisfiable,
            [],
            "These permissions can never be granted from the role editor — add a "
            "Meta.permissions entry (plus migration) or a PERMISSION_MAPPING entry: "
            f"{unsatisfiable}",
        )
