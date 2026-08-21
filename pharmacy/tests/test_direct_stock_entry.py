from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from pharmacy.models import (
    ActiveStoreInventory,
    Dispensary,
    Medication,
    MedicationCategory,
)

User = get_user_model()


class DirectStockEntryTest(TestCase):
    """Adding stock to a dispensary without a purchase or transfer."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            phone_number="9876500011", username="storekeeper", password="testpass123"
        )
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username="storekeeper", password="testpass123")

        self.dispensary = Dispensary.objects.create(name="Main Dispensary")
        # A dispensary gets its active store automatically.
        self.active_store = self.dispensary.active_store
        category = MedicationCategory.objects.create(name="Analgesics")
        self.medication = Medication.objects.create(
            name="Paracetamol", category=category, price=100, dosage_form="tablet"
        )
        self.url = reverse(
            "pharmacy:add_dispensary_inventory_item", args=[self.dispensary.id]
        )
        self.payload = {
            "medication": self.medication.id,
            "stock_quantity": 50,
            "reorder_level": 10,
            "batch_number": "DON-001",
            "expiry_date": (timezone.now().date() + timezone.timedelta(days=180)),
            "unit_cost": "80.00",
        }

    def stock(self):
        return ActiveStoreInventory.objects.get(
            medication=self.medication, active_store=self.active_store
        ).stock_quantity

    def test_first_entry_creates_inventory(self):
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.stock(), 50)

    def test_second_entry_tops_up_instead_of_failing(self):
        self.client.post(self.url, self.payload)
        self.client.post(self.url, dict(self.payload, stock_quantity=30))
        self.assertEqual(self.stock(), 80)
        self.assertEqual(
            ActiveStoreInventory.objects.filter(
                medication=self.medication, active_store=self.active_store
            ).count(),
            1,
        )

    def test_zero_quantity_rejected(self):
        response = self.client.post(self.url, dict(self.payload, stock_quantity=0))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ActiveStoreInventory.objects.exists())

    def test_expired_stock_rejected(self):
        response = self.client.post(
            self.url,
            dict(
                self.payload,
                expiry_date=timezone.now().date() - timezone.timedelta(days=1),
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ActiveStoreInventory.objects.exists())

    def test_entry_is_audited(self):
        from core.models import AuditLog

        self.client.post(self.url, self.payload)
        self.assertTrue(
            AuditLog.all_objects.filter(action="direct_stock_entry").exists()
        )

    def test_dashboard_offers_the_dispensary(self):
        response = self.client.get(reverse("pharmacy:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.url)
        self.assertContains(response, self.dispensary.name)


class TenantAdminInventoryPermissionTest(TestCase):
    """A tenant admin has profile.role='admin' and no Role rows."""

    def test_profile_role_admin_may_add_stock(self):
        from pharmacy.views import user_has_inventory_edit_permission

        user = User.objects.create_user(
            phone_number="9876500022", username="tenantowner", password="testpass123"
        )
        user.profile.role = "admin"
        user.profile.save(update_fields=["role"])
        dispensary = Dispensary.objects.create(name="Tenant Dispensary")

        self.assertTrue(user_has_inventory_edit_permission(user, dispensary))
