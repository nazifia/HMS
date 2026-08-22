from django.test import TestCase
from django.urls import reverse

from accounts.forms import UserProfileForm
from accounts.models import CustomUser, Department, StaffDepartmentAssignment


class ProfileDepartmentsFormTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            username="admin", password="pass12345", phone_number="08000000101"
        )
        self.staff = CustomUser.objects.create_user(
            username="nurse1", password="pass12345", phone_number="08000000102",
            first_name="Nurse", last_name="One",
        )
        self.dept = Department.objects.create(name="Ward A")
        self.other_dept = Department.objects.create(name="Ward B")

    def test_checked_departments_are_saved(self):
        form = UserProfileForm(
            data={
                "first_name": "Nurse",
                "last_name": "One",
                "departments": [str(self.dept.id)],
            },
            instance=self.staff,
            request_user=self.admin,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertIn(self.dept, self.staff.profile.departments.all())

    def test_primary_department_also_grants_access(self):
        form = UserProfileForm(
            data={
                "first_name": "Nurse",
                "last_name": "One",
                "department": str(self.other_dept.id),
                "departments": [str(self.dept.id)],
            },
            instance=self.staff,
            request_user=self.admin,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertEqual(
            {self.dept, self.other_dept}, set(self.staff.profile.departments.all())
        )

    def test_edit_user_profile_page_saves_departments(self):
        self.client.login(username="admin", password="pass12345")
        url = reverse("accounts:superuser_edit_user_profile", args=[self.staff.id])
        self.assertEqual(self.client.get(url).status_code, 200)
        resp = self.client.post(
            url,
            {
                "first_name": "Nurse",
                "last_name": "One",
                "email": "nurse1@example.com",
                "departments": [str(self.dept.id)],
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.email, "nurse1@example.com")
        self.assertIn(self.dept, self.staff.profile.departments.all())

    def test_edit_pages_render_department_checkboxes(self):
        self.client.login(username="admin", password="pass12345")
        for url in (
            reverse("accounts:superuser_edit_user_profile", args=[self.staff.id]),
            reverse("accounts:edit_staff", args=[self.staff.profile.id]),
        ):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)
            self.assertContains(resp, 'name="departments"', msg_prefix=url)

    def test_departments_sync_assignment_rows(self):
        self.client.login(username="admin", password="pass12345")
        url = reverse("accounts:superuser_edit_user_profile", args=[self.staff.id])
        base = {"first_name": "Nurse", "last_name": "One", "phone_number": "08000000102"}

        self.client.post(url, dict(base, departments=[str(self.dept.id)]))
        assignment = StaffDepartmentAssignment.objects.get(
            staff=self.staff, department=self.dept
        )
        self.assertTrue(assignment.is_active)

        # unchecking ends the assignment instead of deleting the history
        self.client.post(url, dict(base, departments=[str(self.other_dept.id)]))
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)
        self.assertIsNotNone(assignment.end_date)
        self.assertTrue(
            StaffDepartmentAssignment.objects.get(
                staff=self.staff, department=self.other_dept
            ).is_active
        )

    def test_admin_can_change_login_phone(self):
        self.client.login(username="admin", password="pass12345")
        url = reverse("accounts:superuser_edit_user_profile", args=[self.staff.id])
        resp = self.client.post(
            url,
            {
                "first_name": "Nurse",
                "last_name": "One",
                "phone_number": "+234 806 123 4567",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.phone_number, "08061234567")

    def test_duplicate_or_bad_phone_rejected(self):
        self.client.login(username="admin", password="pass12345")
        url = reverse("accounts:superuser_edit_user_profile", args=[self.staff.id])
        for bad in ("08000000101", "12345"):
            resp = self.client.post(
                url, {"first_name": "Nurse", "last_name": "One", "phone_number": bad}
            )
            self.assertEqual(resp.status_code, 200, bad)
            self.staff.refresh_from_db()
            self.assertEqual(self.staff.phone_number, "08000000102")

    def test_non_staff_cannot_edit_own_login_phone(self):
        self.client.login(username="nurse1", password="pass12345")
        form = UserProfileForm(
            data={"first_name": "Nurse", "last_name": "One", "phone_number": "08061234567"},
            instance=self.staff,
            request_user=self.staff,
        )
        self.assertNotIn("phone_number", form.fields)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.phone_number, "08000000102")
