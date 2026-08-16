"""Packs, expenses, dispensary admin and supplier writes over the mobile API.

The permission tests matter most: these endpoints are writable, and holding
`pharmacy.view` must not be enough to create records.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import Client, TestCase, override_settings

from accounts.models import CustomUser, Role
from pharmacy.models import (
    ActiveStoreInventory, Dispensary, MedicalPack, MedicalPackItem, Medication,
    MedicationCategory, PackOrder, PharmacyExpense,
)



@override_settings(
    STRICT_ACCESS_CONTROL=True,
    # These tests sign several users in. The default DatabaseCache backs
    # cached_db sessions, and concurrent writes to SQLite's cache_table raise
    # "database table is locked", which Django surfaces as SessionInterrupted.
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class PharmacyAdminApiTest(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            phone_number="08010000008", username="pharmadmin", password="pw12345",
        )
        category = MedicationCategory.objects.create(name="Anaesthetic")
        self.medication = Medication.objects.create(
            name="Lidocaine", category=category, dosage_form="ampoule",
            strength="2%", price=Decimal("200.00"),
        )
        self.dispensary = Dispensary.objects.create(name="Theatre Dispensary")
        ActiveStoreInventory.objects.create(
            medication=self.medication, active_store=self.dispensary.active_store,
            stock_quantity=100, reorder_level=10,
        )
        self.auth = self.token_for("08010000008", "pw12345")

    def pharmacy_user(self, phone, username, *codenames):
        """A non-superuser pharmacy staffer holding only `codenames`.

        Two separate gates run before DRF sees the request: the pharmacist role
        satisfies StrictAccessControlMiddleware's `pharmacy.view`, and
        change_dispensary is what PharmacyAccessMiddleware reads as "pharmacy
        admin" (a pharmacist without a dispensary assignment is redirected).
        Neither implies write access — that is what these tests check.
        """
        user = CustomUser.objects.create_user(
            phone_number=phone, username=username, password="pw12345",
        )
        role, _ = Role.objects.get_or_create(name="pharmacist")
        user.roles.add(role)
        user.user_permissions.add(
            *Permission.objects.filter(
                codename__in=("change_dispensary",) + codenames
            )
        )
        return user, self.token_for(phone, "pw12345")

    def token_for(self, phone, password):
        # A fresh client per user: the login endpoint opens a Django session
        # too, and reusing one client makes the activity tracker log a second
        # login against the first session.
        response = Client().post(
            "/api/accounts/login/",
            {"phone_number": phone, "password": password},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        return {"HTTP_AUTHORIZATION": f"Token {response.json()['token']}"}

    def post(self, path, payload=None, auth=None):
        return self.client.post(
            path, payload or {}, content_type="application/json",
            **(auth or self.auth),
        )

    def get(self, path, auth=None):
        return self.client.get(path, **(auth or self.auth))

    # --- permissions -----------------------------------------------------

    def test_read_only_user_cannot_write(self):
        _, auth = self.pharmacy_user(
            "08010000009", "reader", "view_pharmacyexpense",
        )

        assert self.get("/pharmacy/api/expenses/", auth=auth).status_code == 200

        response = self.post("/pharmacy/api/expenses/", {
            "expense_type": "utility",
            "description": "Electricity",
            "amount": "5000.00",
            "expense_date": str(date.today()),
        }, auth=auth)
        assert response.status_code == 403, response.content
        assert not PharmacyExpense.objects.exists()

    def test_permission_grant_allows_write(self):
        writer, auth = self.pharmacy_user(
            "08010000010", "writer", "add_pharmacyexpense", "view_pharmacyexpense",
        )

        response = self.post("/pharmacy/api/expenses/", {
            "expense_type": "utility",
            "description": "Electricity",
            "amount": "5000.00",
            "expense_date": str(date.today()),
        }, auth=auth)
        assert response.status_code == 201, response.content
        assert PharmacyExpense.objects.get().created_by == writer

    def test_supplier_write_needs_permission(self):
        _, auth = self.pharmacy_user("08010000011", "supreader", "view_supplier")

        assert self.get("/pharmacy/api/suppliers/", auth=auth).status_code == 200
        response = self.post(
            "/pharmacy/api/suppliers/", {"name": "Rogue Supplies"}, auth=auth
        )
        assert response.status_code == 403, response.content

        response = self.post("/pharmacy/api/suppliers/", {
            "name": "Zenith Pharma",
            "phone_number": "08031234567",
            "address": "12 Marina Road",
            "city": "Lagos",
            "state": "Lagos",
        })
        assert response.status_code == 201, response.content

    # --- expenses --------------------------------------------------------

    def test_expense_summary_totals(self):
        for amount, status_value in [("5000.00", "paid"), ("2500.00", "pending")]:
            self.post("/pharmacy/api/expenses/", {
                "expense_type": "operational",
                "description": f"Cost {amount}",
                "amount": amount,
                "expense_date": str(date.today()),
                "payment_status": status_value,
            })
        summary = self.get("/pharmacy/api/expenses/summary/").json()
        assert summary["entries"] == 2
        assert Decimal(summary["total"]) == Decimal("7500.00")
        assert Decimal(summary["pending"]) == Decimal("2500.00")

    # --- packs -----------------------------------------------------------

    def make_pack(self, quantity=5):
        pack = MedicalPack.objects.create(name="Minor Surgery Pack", pack_type="surgery")
        MedicalPackItem.objects.create(
            pack=pack, medication=self.medication, quantity=quantity,
        )
        return pack

    def test_pack_lists_items_and_value(self):
        pack = self.make_pack(quantity=5)
        row = self.get(f"/pharmacy/api/packs/{pack.id}/").json()
        assert row["item_count"] == 1
        assert Decimal(row["total_value"]) == Decimal("1000.00")

    def test_pack_availability_reflects_stock(self):
        pack = self.make_pack(quantity=5)
        assert self.get(
            f"/pharmacy/api/packs/{pack.id}/availability/"
        ).json()["can_order"] is True

        ActiveStoreInventory.objects.update(stock_quantity=1)
        body = self.get(f"/pharmacy/api/packs/{pack.id}/availability/").json()
        assert body["can_order"] is False
        assert "Insufficient stock" in body["message"]

    def test_pack_order_workflow(self):
        from patients.models import Patient

        pack = self.make_pack(quantity=5)
        patient = Patient.objects.create(
            first_name="Ngozi", last_name="Eze", date_of_birth="1992-02-02",
            gender="female", phone_number="08020000012",
        )
        response = self.post("/pharmacy/api/pack-orders/", {
            "pack": pack.id, "patient": patient.id, "order_notes": "For theatre 2",
        })
        assert response.status_code == 201, response.content
        order_id = response.json()["id"]
        assert PackOrder.objects.get(id=order_id).ordered_by == self.admin

        response = self.post(f"/pharmacy/api/pack-orders/{order_id}/dispense/")
        assert response.status_code == 400, response.content

        order = self.post(f"/pharmacy/api/pack-orders/{order_id}/process/").json()
        assert order["status"] in ("in_progress", "ready"), order["status"]

    # --- dispensary admin ------------------------------------------------

    def test_create_dispensary_and_assign_pharmacist(self):
        response = self.post("/pharmacy/api/manage-dispensaries/", {
            "name": "Night Dispensary", "location": "Block C",
        })
        assert response.status_code == 201, response.content
        dispensary_id = response.json()["id"]

        pharmacist = CustomUser.objects.create_user(
            phone_number="08010000013", username="nightpharm", password="pw12345",
        )
        response = self.post("/pharmacy/api/pharmacist-assignments/", {
            "pharmacist": pharmacist.id,
            "dispensary": dispensary_id,
            "start_date": "2026-08-15T08:00:00Z",
        })
        assert response.status_code == 201, response.content

        rows = self.get(
            f"/pharmacy/api/manage-dispensaries/{dispensary_id}/pharmacists/"
        ).json()
        assert [row["pharmacist"] for row in rows] == [pharmacist.id]
        assert self.get(
            f"/pharmacy/api/manage-dispensaries/{dispensary_id}/"
        ).json()["pharmacist_count"] == 1
