"""Self-check for the tenant engine. Run: python manage.py test saas"""
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from patients.models import Patient

from .current import clear_current_hospital, set_current_hospital
from .models import Hospital, Plan, Subscription, enforce_limit


def _make_patient():
    return Patient.objects.create(
        first_name="A", last_name="B", date_of_birth=date(1990, 1, 1),
        gender="M", address="x", city="y", state="z",
    )


class TenantEngineTests(TestCase):
    def setUp(self):
        self.h1 = Hospital.objects.create(name="H1", subdomain="h1")
        self.h2 = Hospital.objects.create(name="H2", subdomain="h2")
        self.addCleanup(clear_current_hospital)

    def test_scoping_and_autostamp(self):
        set_current_hospital(self.h1)
        p = _make_patient()
        self.assertEqual(p.hospital, self.h1)          # auto-stamped
        self.assertEqual(Patient.objects.count(), 1)   # h1 sees its row

        set_current_hospital(self.h2)
        self.assertEqual(Patient.objects.count(), 0)   # h2 isolated
        self.assertEqual(Patient.all_objects.count(), 1)  # escape hatch sees all

    def test_plan_limit(self):
        plan = Plan.objects.create(name="Tiny", max_patients=1)
        Subscription.objects.create(
            hospital=self.h1, plan=plan, status="active",
            current_period_end=timezone.now() + timedelta(days=30),
        )
        set_current_hospital(self.h1)
        enforce_limit(self.h1, Patient, "max_patients")  # 0 used, cap 1 -> ok
        _make_patient()
        with self.assertRaises(ValidationError):       # 1 used, cap 1 -> blocked
            enforce_limit(self.h1, Patient, "max_patients")
