from django.core.cache import cache
from django.test import TestCase, override_settings

from dashboard.cache import bump, get_version
from patients.models import Patient
from saas.models import Hospital

# The project's default test cache is DatabaseCache, whose rows roll back with
# the test transaction; use a plain in-memory cache so versions behave normally.
LOCMEM = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "dashboard-tests",
    }
}


@override_settings(CACHES=LOCMEM)
class DashboardCacheVersionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.hospital = Hospital.objects.create(name="A", subdomain="a")
        self.other = Hospital.objects.create(name="B", subdomain="b")

    def test_bump_only_moves_its_own_hospital(self):
        before, other_before = get_version(self.hospital.id), get_version(self.other.id)
        bump(self.hospital.id)
        self.assertEqual(get_version(self.hospital.id), before + 1)
        self.assertEqual(get_version(self.other.id), other_before)

    def test_write_to_watched_model_bumps_version(self):
        # Creating a Hospital seeds its own tenant rows, so compare deltas.
        before, other_before = get_version(self.hospital.id), get_version(self.other.id)
        Patient.all_objects.create(
            hospital=self.hospital,
            first_name="Ada",
            last_name="Obi",
            date_of_birth="1990-01-01",
            gender="female",
            phone_number="08000000000",
        )
        self.assertGreater(get_version(self.hospital.id), before)
        self.assertEqual(get_version(self.other.id), other_before)
