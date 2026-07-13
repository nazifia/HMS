from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser, Department, StaffDepartmentAssignment


class StaffDepartmentAssignmentTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            username="admin", password="pass12345", phone_number="08000000001"
        )
        self.staff = CustomUser.objects.create_user(
            username="nurse1", password="pass12345", phone_number="08000000002",
            first_name="Nurse", last_name="One",
        )
        self.department = Department.objects.create(name="Test Ward")
        self.client.login(username="admin", password="pass12345")

    def test_add_end_delete_flow(self):
        # add
        resp = self.client.post(
            reverse("accounts:add_department_assignment"),
            {
                "staff": self.staff.id,
                "department": self.department.id,
                "start_date": "2026-07-13",
                "is_active": "true",
            },
        )
        self.assertEqual(resp.status_code, 302)
        assignment = StaffDepartmentAssignment.objects.get(staff=self.staff)
        self.assertTrue(assignment.is_active)

        # duplicate active blocked
        self.client.post(
            reverse("accounts:add_department_assignment"),
            {
                "staff": self.staff.id,
                "department": self.department.id,
                "start_date": "2026-07-13",
                "is_active": "true",
            },
        )
        self.assertEqual(StaffDepartmentAssignment.objects.count(), 1)

        # manage + reports pages render
        self.assertEqual(
            self.client.get(reverse("accounts:manage_department_assignments")).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("accounts:department_assignment_reports")).status_code, 200
        )

        # end (POST only)
        self.client.post(
            reverse("accounts:end_department_assignment", args=[assignment.id])
        )
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)
        self.assertIsNotNone(assignment.end_date)

        # delete
        self.client.post(
            reverse("accounts:delete_department_assignment", args=[assignment.id])
        )
        self.assertEqual(StaffDepartmentAssignment.objects.count(), 0)
