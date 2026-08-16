"""The home screen's one call.

What matters is that a tile reports the real figure and that it disappears for
a user who may not see the module behind it — the dashboard must not advertise
a screen the server would refuse.
"""
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import CustomUser
from billing.models import Invoice
from inpatient.models import Bed, Ward
from patients.models import Patient


@override_settings(STRICT_ACCESS_CONTROL=True)
class DashboardApiTest(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            phone_number="08019000001", username="boss", password="pw12345",
        )
        self.auth = self.token_for("08019000001", "pw12345")

        self.patient = Patient.objects.create(
            first_name="Ngozi", last_name="Eze", date_of_birth="1980-02-02",
            gender="F", address="2 Clinic Road", city="Aba", state="Abia",
        )
        ward = Ward.objects.create(
            name="Male Medical", ward_type="general", floor="1", capacity=2,
            charge_per_day=Decimal("5000.00"),
        )
        Bed.objects.create(ward=ward, bed_number="1")
        Bed.objects.create(ward=ward, bed_number="2", is_occupied=True)
        Invoice.objects.create(
            patient=self.patient, invoice_number="INVDASH1",
            invoice_date=timezone.now(), due_date=timezone.now().date(),
            status="pending", subtotal=Decimal("300.00"),
            tax_amount=Decimal("0.00"), discount_amount=Decimal("0.00"),
        )

    def token_for(self, phone, password):
        response = Client().post(
            "/api/accounts/login/",
            {"phone_number": phone, "password": password},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        return {"HTTP_AUTHORIZATION": f"Token {response.json()['token']}"}

    def tiles_for(self, auth):
        response = self.client.get("/api/dashboard/", **auth)
        assert response.status_code == 200, response.content
        return {tile["key"]: tile for tile in response.json()["tiles"]}

    def test_tiles_report_the_real_figures(self):
        tiles = self.tiles_for(self.auth)

        assert set(tiles) == {
            "clinic_queue", "unpaid_invoices", "lab_verification",
            "low_stock", "free_beds",
        }, tiles
        assert tiles["free_beds"]["count"] == 1, tiles["free_beds"]
        assert tiles["unpaid_invoices"]["count"] == 1
        assert "300.00" in tiles["unpaid_invoices"]["note"]
        assert tiles["clinic_queue"]["count"] == 0

    def test_a_tile_the_user_may_not_see_is_not_served(self):
        CustomUser.objects.create_user(
            phone_number="08019000002", username="cashier", password="pw12345",
        ).user_permissions.add(
            Permission.objects.get(
                codename="view_invoice", content_type__app_label="billing",
            )
        )
        tiles = self.tiles_for(self.token_for("08019000002", "pw12345"))

        assert set(tiles) == {"unpaid_invoices"}, tiles
