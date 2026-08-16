"""Procurement over the mobile API.

Covers the money path: draft -> approval -> goods received into bulk stock ->
supplier payment. `purchase_services` is shared with the HTML views, so a break
here is a break there too.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import CustomUser
from pharmacy.models import (
    BulkStoreInventory, Medication, MedicationCategory, Purchase, Supplier,
)



@override_settings(STRICT_ACCESS_CONTROL=True)
class PurchaseApiTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            phone_number="08010000007", username="buyer", password="pw12345",
        )
        category = MedicationCategory.objects.create(name="Antihypertensive")
        self.medication = Medication.objects.create(
            name="Amlodipine", category=category, dosage_form="tablet",
            strength="5mg", price=Decimal("30.00"),
        )
        self.supplier = Supplier.objects.create(name="Zenith Pharma")
        response = self.client.post(
            "/api/accounts/login/",
            {"phone_number": "08010000007", "password": "pw12345"},
            content_type="application/json",
        )
        self.auth = {"HTTP_AUTHORIZATION": f"Token {response.json()['token']}"}

    def post(self, path, payload=None):
        return self.client.post(
            path, payload or {}, content_type="application/json", **self.auth
        )

    def get(self, path):
        return self.client.get(path, **self.auth)

    def draft_with_item(self, quantity=100):
        response = self.post("/pharmacy/api/purchases/", {
            "supplier": self.supplier.id,
            "purchase_date": timezone.now().isoformat(),
            "invoice_number": f"PO-{quantity}",
        })
        assert response.status_code == 201, response.content
        purchase_id = response.json()["id"]

        response = self.post("/pharmacy/api/purchase-items/", {
            "purchase": purchase_id,
            "medication": self.medication.id,
            "quantity": quantity,
            "unit_price": "25.00",
            "expiry_date": str(date.today() + timedelta(days=365)),
        })
        assert response.status_code == 201, response.content
        return purchase_id

    def test_adding_items_updates_total(self):
        purchase_id = self.draft_with_item(quantity=100)
        purchase = self.get(f"/pharmacy/api/purchases/{purchase_id}/").json()
        assert Decimal(purchase["total_amount"]) == Decimal("2500.00")
        assert purchase["approval_status"] == "draft"

    def test_empty_purchase_cannot_be_submitted(self):
        purchase_id = self.post("/pharmacy/api/purchases/", {
            "supplier": self.supplier.id,
            "purchase_date": timezone.now().isoformat(),
            "invoice_number": "PO-EMPTY",
        }).json()["id"]
        response = self.post(f"/pharmacy/api/purchases/{purchase_id}/submit/")
        assert response.status_code == 400
        assert "without items" in response.json()["error"]

    def test_full_flow_submit_approve_receive_pay(self):
        purchase_id = self.draft_with_item(quantity=100)

        assert self.post(
            f"/pharmacy/api/purchases/{purchase_id}/submit/"
        ).json()["approval_status"] == "pending"

        # Payment is blocked until goods actually arrive.
        response = self.post(f"/pharmacy/api/purchases/{purchase_id}/pay/", {
            "amount": "100.00", "payment_method": "cash",
        })
        assert response.status_code == 400
        assert "approved" in response.json()["error"].lower()

        purchase = self.post(
            f"/pharmacy/api/purchases/{purchase_id}/approve/"
        ).json()
        assert purchase["approval_status"] == "approved"
        assert purchase["can_receive_delivery"] is True

        response = self.post(f"/pharmacy/api/purchases/{purchase_id}/pay/", {
            "amount": "100.00", "payment_method": "cash",
        })
        assert response.status_code == 400
        assert "received" in response.json()["error"].lower()

        # Partial delivery: 40 of 100 into the bulk store.
        item_id = purchase["items"][0]["id"]
        purchase = self.post(
            f"/pharmacy/api/purchases/{purchase_id}/receive-delivery/",
            {"quantities": {str(item_id): 40}},
        ).json()
        assert purchase["delivery_status"] == "partial"
        assert purchase["items"][0]["quantity_outstanding"] == 60
        stock = BulkStoreInventory.objects.filter(
            medication=self.medication
        ).first()
        assert stock.stock_quantity == 40, stock.stock_quantity

        # Part-pay, then settle the rest.
        purchase = self.post(f"/pharmacy/api/purchases/{purchase_id}/pay/", {
            "amount": "1000.00", "payment_method": "bank_transfer",
        }).json()["purchase"]
        assert purchase["payment_status"] == "partial"
        assert Decimal(purchase["outstanding"]) == Decimal("1500.00")

        purchase = self.post(f"/pharmacy/api/purchases/{purchase_id}/pay/", {
            "amount": "1500.00", "payment_method": "cash",
        }).json()["purchase"]
        assert purchase["payment_status"] == "paid"
        assert Decimal(purchase["outstanding"]) == Decimal("0.00")
        assert len(purchase["payments"]) == 2

    def test_overpayment_refused(self):
        purchase_id = self.draft_with_item(quantity=10)  # total 250.00
        self.post(f"/pharmacy/api/purchases/{purchase_id}/submit/")
        purchase = self.post(
            f"/pharmacy/api/purchases/{purchase_id}/approve/"
        ).json()
        self.post(
            f"/pharmacy/api/purchases/{purchase_id}/receive-delivery/",
            {"quantities": {str(purchase["items"][0]["id"]): 10}},
        )
        response = self.post(f"/pharmacy/api/purchases/{purchase_id}/pay/", {
            "amount": "9999.00", "payment_method": "cash",
        })
        assert response.status_code == 400
        assert "outstanding balance" in response.json()["error"]

    def test_receiving_more_than_ordered_refused(self):
        purchase_id = self.draft_with_item(quantity=10)
        self.post(f"/pharmacy/api/purchases/{purchase_id}/submit/")
        purchase = self.post(
            f"/pharmacy/api/purchases/{purchase_id}/approve/"
        ).json()
        response = self.post(
            f"/pharmacy/api/purchases/{purchase_id}/receive-delivery/",
            {"quantities": {str(purchase["items"][0]["id"]): 50}},
        )
        assert response.status_code == 400
        assert "exceeds outstanding" in response.json()["error"]
        assert not BulkStoreInventory.objects.filter(
            medication=self.medication
        ).exists()

    def test_reject_needs_reason_and_blocks_approval(self):
        purchase_id = self.draft_with_item(quantity=5)
        self.post(f"/pharmacy/api/purchases/{purchase_id}/submit/")

        response = self.post(f"/pharmacy/api/purchases/{purchase_id}/reject/")
        assert response.status_code == 400
        assert "reason" in response.json()["error"].lower()

        purchase = self.post(
            f"/pharmacy/api/purchases/{purchase_id}/reject/",
            {"reason": "Price too high"},
        ).json()
        assert purchase["approval_status"] == "rejected"
        assert purchase["approval_notes"] == "Price too high"

        response = self.post(f"/pharmacy/api/purchases/{purchase_id}/approve/")
        assert response.status_code == 400

    def test_items_locked_once_submitted(self):
        purchase_id = self.draft_with_item(quantity=5)
        self.post(f"/pharmacy/api/purchases/{purchase_id}/submit/")

        response = self.post("/pharmacy/api/purchase-items/", {
            "purchase": purchase_id,
            "medication": self.medication.id,
            "quantity": 1,
            "unit_price": "25.00",
            "expiry_date": str(date.today() + timedelta(days=365)),
        })
        assert response.status_code == 400
        assert "draft" in response.json()["error"]

    def test_purchase_filters(self):
        self.draft_with_item(quantity=7)
        assert self.get(
            "/pharmacy/api/purchases/?approval_status=draft"
        ).json()["count"] == 1
        assert self.get(
            "/pharmacy/api/purchases/?approval_status=approved"
        ).json()["count"] == 0
        assert self.get(
            "/pharmacy/api/purchases/?search=zenith"
        ).json()["count"] == 1
