"""Cart + dispensing over the mobile API.

These cover the money path: cart creation, quantity edits against stock, and
stock deduction on dispense. `cart_services` is shared with the HTML views, so
a break here is a break there too.
"""
from decimal import Decimal

from django.test import TestCase, override_settings

from accounts.models import CustomUser
from patients.models import Patient
from pharmacy.cart_models import PrescriptionCart
from pharmacy.models import (
    ActiveStore, ActiveStoreInventory, Dispensary, Medication,
    MedicationCategory, Prescription, PrescriptionItem,
)



@override_settings(STRICT_ACCESS_CONTROL=True)
class CartApiTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            phone_number="08010000003", username="carttest", password="pw12345",
        )
        self.patient = Patient.objects.create(
            first_name="Bola", last_name="Ade", date_of_birth="1990-01-01",
            gender="female", phone_number="08020000004",
        )
        category = MedicationCategory.objects.create(name="Antibiotic")
        self.medication = Medication.objects.create(
            name="Amoxicillin", category=category, dosage_form="capsule",
            strength="500mg", price=Decimal("50.00"),
        )
        self.dispensary = Dispensary.objects.create(name="Main Dispensary")
        active_store = self.dispensary.active_store  # created with the dispensary
        ActiveStoreInventory.objects.create(
            medication=self.medication, active_store=active_store, stock_quantity=20,
        )
        self.prescription = Prescription.objects.create(
            patient=self.patient, doctor=self.user,
        )
        self.item = PrescriptionItem.objects.create(
            prescription=self.prescription, medication=self.medication, quantity=10,
        )
        response = self.client.post(
            "/api/accounts/login/",
            {"phone_number": "08010000003", "password": "pw12345"},
            content_type="application/json",
        )
        self.auth = {"HTTP_AUTHORIZATION": f"Token {response.json()['token']}"}

    def pay(self, invoice):
        """Settle an invoice the way the billing office would."""
        from billing.models import Payment

        Payment.objects.create(
            invoice=invoice, amount=invoice.total_amount,
            payment_method="cash", received_by=self.user,
        )
        invoice.refresh_from_db()
        assert invoice.status == "paid", invoice.status
        return invoice

    def post(self, path, payload=None):
        return self.client.post(
            path, payload or {}, content_type="application/json", **self.auth
        )

    def create_cart(self):
        response = self.post("/pharmacy/api/carts/", {"prescription": self.prescription.id})
        assert response.status_code == 201, response.content
        return response.json()["cart"]

    def test_create_cart_holds_prescribed_quantity(self):
        cart = self.create_cart()
        assert len(cart["items"]) == 1
        assert cart["items"][0]["quantity"] == 10
        assert Decimal(cart["subtotal"]) == Decimal("500.00")

    def test_second_cart_returns_existing(self):
        self.create_cart()
        response = self.post(
            "/pharmacy/api/carts/", {"prescription": self.prescription.id}
        )
        assert response.status_code == 409, response.content
        assert response.json()["cart"]["id"]

    def test_quantity_cannot_exceed_stock(self):
        cart = self.create_cart()
        self.post(f"/pharmacy/api/carts/{cart['id']}/dispensary/",
                  {"dispensary": self.dispensary.id})
        item_id = cart["items"][0]["id"]
        response = self.client.patch(
            f"/pharmacy/api/cart-items/{item_id}/",
            {"quantity": 999},
            content_type="application/json",
            **self.auth,
        )
        assert response.status_code == 400
        assert "stock" in response.json()["error"].lower()

    def test_dispense_blocked_until_invoice_paid(self):
        cart = self.create_cart()
        self.post(f"/pharmacy/api/carts/{cart['id']}/dispensary/",
                  {"dispensary": self.dispensary.id})
        response = self.post(f"/pharmacy/api/carts/{cart['id']}/dispense/")
        assert response.status_code == 400, response.content

    def test_dispense_deducts_stock_and_updates_prescription(self):
        cart_json = self.create_cart()
        self.post(f"/pharmacy/api/carts/{cart_json['id']}/dispensary/",
                  {"dispensary": self.dispensary.id})

        response = self.post(f"/pharmacy/api/carts/{cart_json['id']}/invoice/")
        assert response.status_code == 200, response.content

        cart = PrescriptionCart.objects.get(id=cart_json["id"])
        assert cart.invoice, "invoice action should have billed the cart"
        self.pay(cart.invoice)
        cart.refresh_from_db()

        response = self.post(f"/pharmacy/api/carts/{cart.id}/dispense/")
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["completed"] is True, body

        total_stock = sum(
            row.stock_quantity
            for row in ActiveStoreInventory.objects.filter(medication=self.medication)
        )
        assert total_stock == 10, total_stock  # 20 on hand - 10 dispensed

        self.item.refresh_from_db()
        self.prescription.refresh_from_db()
        assert self.item.quantity_dispensed_so_far == 10
        assert self.item.is_dispensed is True
        assert self.prescription.status == "dispensed"

    def test_wallet_payment_requires_funds(self):
        cart = self.create_cart()
        self.post(f"/pharmacy/api/carts/{cart['id']}/dispensary/",
                  {"dispensary": self.dispensary.id})
        response = self.post(
            f"/pharmacy/api/carts/{cart['id']}/pay-from-wallet/"
        )
        assert response.status_code == 400, response.content
        assert "wallet balance" in response.json()["error"].lower()

    def test_wallet_payment_settles_cart(self):
        from patients.models import PatientWallet

        PatientWallet.objects.update_or_create(
            patient=self.patient, defaults={"balance": Decimal("1000.00")},
        )
        cart_json = self.create_cart()
        self.post(f"/pharmacy/api/carts/{cart_json['id']}/dispensary/",
                  {"dispensary": self.dispensary.id})

        response = self.post(
            f"/pharmacy/api/carts/{cart_json['id']}/pay-from-wallet/"
        )
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["paid"] is True
        assert body["cart"]["can_dispense"] is True

        wallet = PatientWallet.objects.get(patient=self.patient)
        assert wallet.balance == Decimal("500.00"), wallet.balance

        cart = PrescriptionCart.objects.get(id=cart_json["id"])
        assert cart.status == "paid"
        assert cart.invoice.status == "paid"

    def test_substitute_swaps_medication_and_price(self):
        other = Medication.objects.create(
            name="Ampicillin", category=self.medication.category,
            dosage_form="capsule", strength="500mg", price=Decimal("80.00"),
        )
        ActiveStoreInventory.objects.create(
            medication=other, active_store=self.dispensary.active_store,
            stock_quantity=30,
        )
        cart = self.create_cart()
        self.post(f"/pharmacy/api/carts/{cart['id']}/dispensary/",
                  {"dispensary": self.dispensary.id})
        item_id = cart["items"][0]["id"]

        alternatives = self.client.get(
            f"/pharmacy/api/cart-items/{item_id}/alternatives/", **self.auth
        ).json()
        assert [row["id"] for row in alternatives] == [other.id], alternatives

        response = self.post(
            f"/pharmacy/api/cart-items/{item_id}/substitute/",
            {"medication": other.id, "reason": "Out of stock"},
        )
        assert response.status_code == 200, response.content
        item = response.json()["cart"]["items"][0]
        assert item["medication"]["name"] == "Ampicillin"
        assert item["is_substituted"] is True
        assert Decimal(item["unit_price"]) == Decimal("80.00")

        response = self.post(
            f"/pharmacy/api/cart-items/{item_id}/remove-substitution/"
        )
        assert response.status_code == 200, response.content
        item = response.json()["cart"]["items"][0]
        assert item["medication"]["name"] == "Amoxicillin"
        assert Decimal(item["unit_price"]) == Decimal("50.00")

    def test_substitution_requires_reason(self):
        other = Medication.objects.create(
            name="Cloxacillin", category=self.medication.category,
            dosage_form="capsule", strength="250mg", price=Decimal("70.00"),
        )
        cart = self.create_cart()
        response = self.post(
            f"/pharmacy/api/cart-items/{cart['items'][0]['id']}/substitute/",
            {"medication": other.id},
        )
        assert response.status_code == 400
        assert "reason" in response.json()["error"].lower()

    def test_partial_dispense_leaves_cart_open(self):
        cart_json = self.create_cart()
        self.post(f"/pharmacy/api/carts/{cart_json['id']}/dispensary/",
                  {"dispensary": self.dispensary.id})

        self.post(f"/pharmacy/api/carts/{cart_json['id']}/invoice/")

        cart = PrescriptionCart.objects.get(id=cart_json["id"])
        self.pay(cart.invoice)
        cart.refresh_from_db()

        item_id = cart.items.first().id
        response = self.post(
            f"/pharmacy/api/carts/{cart.id}/dispense/",
            {"quantities": {str(item_id): 3}},
        )
        assert response.status_code == 200, response.content
        assert response.json()["completed"] is False

        cart.refresh_from_db()
        self.item.refresh_from_db()
        assert cart.status == "partially_dispensed"
        assert self.item.quantity_dispensed_so_far == 3
        total_stock = sum(
            row.stock_quantity
            for row in ActiveStoreInventory.objects.filter(medication=self.medication)
        )
        assert total_stock == 17, total_stock
