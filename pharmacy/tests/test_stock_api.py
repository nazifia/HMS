"""Inventory, transfers and dispensing history over the mobile API."""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, override_settings

from accounts.models import CustomUser
from pharmacy.models import (
    ActiveStoreBatch, ActiveStoreInventory, Dispensary,
    InterDispensaryTransfer, Medication, MedicationCategory,
)



@override_settings(STRICT_ACCESS_CONTROL=True)
class StockApiTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            phone_number="08010000005", username="stocktest", password="pw12345",
        )
        category = MedicationCategory.objects.create(name="Antimalarial")
        self.medication = Medication.objects.create(
            name="Artemether", category=category, dosage_form="tablet",
            strength="20mg", price=Decimal("120.00"), reorder_level=10,
        )
        self.low = Medication.objects.create(
            name="Quinine", category=category, dosage_form="tablet",
            strength="300mg", price=Decimal("90.00"), reorder_level=10,
        )
        self.main = Dispensary.objects.create(name="Main")
        self.annex = Dispensary.objects.create(name="Annex")
        inventory = ActiveStoreInventory.objects.create(
            medication=self.medication, active_store=self.main.active_store,
            stock_quantity=50, reorder_level=10,
        )
        # Transfers move batches, not just the summary column.
        ActiveStoreBatch.objects.create(
            active_inventory=inventory, batch_number="B1", quantity=50,
            expiry_date=date.today() + timedelta(days=365),
            unit_cost=Decimal("100.00"),
        )
        ActiveStoreInventory.objects.create(
            medication=self.low, active_store=self.main.active_store,
            stock_quantity=5, reorder_level=10,
        )
        response = self.client.post(
            "/api/accounts/login/",
            {"phone_number": "08010000005", "password": "pw12345"},
            content_type="application/json",
        )
        self.auth = {"HTTP_AUTHORIZATION": f"Token {response.json()['token']}"}

    def get(self, path):
        return self.client.get(path, **self.auth)

    def post(self, path, payload=None):
        return self.client.post(
            path, payload or {}, content_type="application/json", **self.auth
        )

    def test_inventory_filters_by_dispensary(self):
        response = self.get(f"/pharmacy/api/inventory/?dispensary={self.main.id}")
        assert response.status_code == 200, response.content
        assert response.json()["count"] == 2
        assert self.get(
            f"/pharmacy/api/inventory/?dispensary={self.annex.id}"
        ).json()["count"] == 0

    def test_inventory_low_stock_and_search(self):
        rows = self.get("/pharmacy/api/inventory/?low_stock=true").json()["results"]
        assert [row["medication"]["name"] for row in rows] == ["Quinine"]
        assert rows[0]["is_low_stock"] is True

        rows = self.get("/pharmacy/api/inventory/?search=artem").json()["results"]
        assert [row["medication"]["name"] for row in rows] == ["Artemether"]

    def test_transfer_approve_then_execute_moves_stock(self):
        response = self.post("/pharmacy/api/transfers/", {
            "medication": self.medication.id,
            "from_dispensary": self.main.id,
            "to_dispensary": self.annex.id,
            "quantity": 20,
        })
        assert response.status_code == 201, response.content
        assert response.json()["available"] is True
        transfer_id = response.json()["id"]

        assert self.post(
            f"/pharmacy/api/transfers/{transfer_id}/approve/"
        ).status_code == 200
        response = self.post(f"/pharmacy/api/transfers/{transfer_id}/execute/")
        assert response.status_code == 200, response.content
        assert response.json()["status"] == "completed"

        source = ActiveStoreInventory.objects.get(
            medication=self.medication, active_store=self.main.active_store,
        )
        destination = ActiveStoreInventory.objects.get(
            medication=self.medication, active_store=self.annex.active_store,
        )
        assert source.stock_quantity == 30, source.stock_quantity
        assert destination.stock_quantity == 20, destination.stock_quantity

    def test_transfer_over_stock_cannot_be_approved(self):
        response = self.post("/pharmacy/api/transfers/", {
            "medication": self.medication.id,
            "from_dispensary": self.main.id,
            "to_dispensary": self.annex.id,
            "quantity": 500,
        })
        assert response.json()["available"] is False
        transfer_id = response.json()["id"]

        response = self.post(f"/pharmacy/api/transfers/{transfer_id}/approve/")
        assert response.status_code == 400
        assert "insufficient stock" in response.json()["error"].lower()

    def test_transfer_reject_records_reason(self):
        transfer_id = self.post("/pharmacy/api/transfers/", {
            "medication": self.medication.id,
            "from_dispensary": self.main.id,
            "to_dispensary": self.annex.id,
            "quantity": 5,
        }).json()["id"]

        response = self.post(
            f"/pharmacy/api/transfers/{transfer_id}/reject/",
            {"reason": "Annex restocking tomorrow"},
        )
        assert response.status_code == 200, response.content
        transfer = InterDispensaryTransfer.objects.get(id=transfer_id)
        assert transfer.status == "rejected"
        assert transfer.rejection_reason == "Annex restocking tomorrow"

    def test_dispensing_log_summary(self):
        from pharmacy.models import (
            DispensingLog, Prescription, PrescriptionItem,
        )
        from patients.models import Patient

        patient = Patient.objects.create(
            first_name="Uche", last_name="Nwosu", date_of_birth="1985-05-05",
            gender="male", phone_number="08020000006",
        )
        prescription = Prescription.objects.create(patient=patient, doctor=self.user)
        item = PrescriptionItem.objects.create(
            prescription=prescription, medication=self.medication, quantity=6,
        )
        DispensingLog.objects.create(
            prescription_item=item, dispensed_by=self.user, dispensed_quantity=6,
            unit_price_at_dispense=Decimal("120.00"),
            total_price_for_this_log=Decimal("720.00"), dispensary=self.main,
        )

        rows = self.get("/pharmacy/api/dispensing-logs/?mine=true").json()["results"]
        assert rows[0]["patient_name"] == "Uche Nwosu"
        assert rows[0]["medication_name"] == "Artemether"

        summary = self.get("/pharmacy/api/dispensing-logs/summary/").json()
        assert summary["entries"] == 1, summary
        assert summary["quantity"] == 6, summary
        assert Decimal(summary["value"]) == Decimal("720.00"), summary
