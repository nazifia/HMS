from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from pharmacy.models import (
    ActiveStore,
    ActiveStoreInventory,
    Dispensary,
    Medication,
    MedicationCategory,
)
from saas.models import Hospital


class PharmacyAlertsTenantTest(TestCase):
    """Each hospital's low-stock email must contain only its own stock."""

    def setUp(self):
        self.h1 = Hospital.objects.create(
            name="H1", subdomain="h1", email="h1@example.com"
        )
        self.h2 = Hospital.objects.create(
            name="H2", subdomain="h2", email="h2@example.com"
        )
        self.low_1 = self._low_stock(self.h1, "AlphaCillin")
        self.low_2 = self._low_stock(self.h2, "BetaCillin")

    def _low_stock(self, hospital, med_name):
        category = MedicationCategory.all_objects.create(
            name=f"Cat {hospital.subdomain}", hospital=hospital
        )
        medication = Medication.all_objects.create(
            name=med_name,
            category=category,
            dosage_form="Capsule",
            strength="500mg",
            price=Decimal("10.00"),
            reorder_level=10,
            hospital=hospital,
        )
        dispensary = Dispensary.all_objects.create(
            name=f"Disp {hospital.subdomain}", hospital=hospital
        )
        store = ActiveStore.all_objects.filter(dispensary=dispensary).first()
        if store is None:  # signal normally creates it
            store = ActiveStore.all_objects.create(
                name=f"Store {hospital.subdomain}",
                dispensary=dispensary,
                hospital=hospital,
            )
        return ActiveStoreInventory.all_objects.create(
            medication=medication,
            active_store=store,
            stock_quantity=1,
            reorder_level=10,
            expiry_date=timezone.now().date() + timedelta(days=365),
            hospital=hospital,
        )

    def test_one_email_per_hospital_with_only_its_own_stock(self):
        call_command("send_pharmacy_alerts")

        by_recipient = {m.to[0]: m.body for m in mail.outbox}
        self.assertEqual(set(by_recipient), {"h1@example.com", "h2@example.com"})
        self.assertIn("AlphaCillin", by_recipient["h1@example.com"])
        self.assertNotIn("BetaCillin", by_recipient["h1@example.com"])
        self.assertIn("BetaCillin", by_recipient["h2@example.com"])
        self.assertNotIn("AlphaCillin", by_recipient["h2@example.com"])

    def test_hospital_without_email_is_skipped(self):
        Hospital.objects.filter(pk=self.h2.pk).update(email="")

        call_command("send_pharmacy_alerts")

        self.assertEqual([m.to for m in mail.outbox], [["h1@example.com"]])
