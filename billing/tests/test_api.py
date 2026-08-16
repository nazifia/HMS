"""Billing over the mobile API: invoices, service lines, payments.

Payment goes through the same BillingOfficePaymentProcessor as the billing
office pages, so the balance and wallet rules are the shared ones.
"""
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import CustomUser, Role
from billing.models import Invoice, Payment, Service, ServiceCategory
from patients.models import Patient, PatientWallet


@override_settings(STRICT_ACCESS_CONTROL=True)
class BillingApiTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            phone_number="08013000001", username="cashier", password="pw12345",
        )
        self.auth = self.token_for("08013000001", "pw12345")
        self.patient = Patient.objects.create(
            first_name="Grace", last_name="Eze", date_of_birth="1991-04-04",
            gender="F", address="5 Owerri Road", city="Owerri", state="Imo",
        )
        category = ServiceCategory.objects.create(name="Consultation")
        self.service = Service.objects.create(
            name="General Consultation", category=category,
            price=Decimal("2000.00"), tax_percentage=Decimal("0.00"),
        )

    def token_for(self, phone, password):
        response = Client().post(
            "/api/accounts/login/",
            {"phone_number": phone, "password": password},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        return {"HTTP_AUTHORIZATION": f"Token {response.json()['token']}"}

    def get(self, path, auth=None):
        return self.client.get(path, **(auth or self.auth))

    def post(self, path, payload=None, auth=None):
        return self.client.post(
            path, payload or {}, content_type="application/json",
            **(auth or self.auth),
        )

    def make_invoice(self, quantity=1):
        response = self.post("/billing/api/invoices/", {
            "patient": self.patient.id,
            "due_date": str(timezone.now().date()),
            "source_app": "billing",
        })
        assert response.status_code == 201, response.content
        invoice_id = response.json()["id"]

        response = self.post("/billing/api/invoice-items/", {
            "invoice": invoice_id,
            "service": self.service.id,
            "description": "Consultation",
            "quantity": quantity,
            "unit_price": "2000.00",
        })
        assert response.status_code == 201, response.content
        return invoice_id

    # --- invoices ---------------------------------------------------------

    def test_adding_items_recomputes_invoice_total(self):
        invoice_id = self.make_invoice(quantity=2)
        invoice = self.get(f"/billing/api/invoices/{invoice_id}/").json()
        assert Decimal(invoice["total_amount"]) == Decimal("4000.00")
        assert Decimal(invoice["balance"]) == Decimal("4000.00")
        assert invoice["invoice_number"], "invoice number is generated"
        assert invoice["service_details"] == "General Consultation"

    def test_search_and_unpaid_filter(self):
        self.make_invoice()
        assert self.get("/billing/api/invoices/?search=grace").json()["count"] == 1
        assert self.get("/billing/api/invoices/?unpaid=true").json()["count"] == 1
        assert self.get(
            "/billing/api/invoices/?search=nobody"
        ).json()["count"] == 0

    # --- payments ---------------------------------------------------------

    def test_payment_settles_invoice(self):
        invoice_id = self.make_invoice()
        response = self.post(f"/billing/api/invoices/{invoice_id}/pay/", {
            "amount": "2000.00", "payment_method": "cash",
        })
        assert response.status_code == 200, response.content
        invoice = response.json()["invoice"]
        assert invoice["status"] == "paid"
        assert Decimal(invoice["balance"]) == Decimal("0.00")
        assert len(invoice["payments"]) == 1

    def test_part_payment_leaves_balance(self):
        invoice_id = self.make_invoice()
        invoice = self.post(f"/billing/api/invoices/{invoice_id}/pay/", {
            "amount": "500.00", "payment_method": "cash",
        }).json()["invoice"]
        assert invoice["status"] == "partially_paid"
        assert Decimal(invoice["balance"]) == Decimal("1500.00")

    def test_overpayment_refused(self):
        invoice_id = self.make_invoice()
        response = self.post(f"/billing/api/invoices/{invoice_id}/pay/", {
            "amount": "9999.00", "payment_method": "cash",
        })
        assert response.status_code == 400
        assert "exceeds remaining balance" in response.json()["error"]
        assert not Payment.objects.exists()

    def test_invalid_amount_refused(self):
        invoice_id = self.make_invoice()
        for amount in ("0", "-5", "abc", None):
            response = self.post(
                f"/billing/api/invoices/{invoice_id}/pay/",
                {"amount": amount, "payment_method": "cash"},
            )
            assert response.status_code == 400, (amount, response.content)
        assert not Payment.objects.exists()

    def test_wallet_payment_debits_the_wallet_once(self):
        PatientWallet.objects.update_or_create(
            patient=self.patient, defaults={"balance": Decimal("5000.00")},
        )
        invoice_id = self.make_invoice()
        response = self.post(f"/billing/api/invoices/{invoice_id}/pay/", {
            "amount": "2000.00", "payment_source": "patient_wallet",
        })
        assert response.status_code == 200, response.content
        assert response.json()["invoice"]["status"] == "paid"

        wallet = PatientWallet.objects.get(patient=self.patient)
        assert wallet.balance == Decimal("3000.00"), wallet.balance

    def test_payment_needs_the_process_payment_permission(self):
        invoice_id = self.make_invoice()
        clerk = CustomUser.objects.create_user(
            phone_number="08013000002", username="clerk", password="pw12345",
        )
        role, _ = Role.objects.get_or_create(name="accountant")
        clerk.roles.add(role)
        auth = self.token_for("08013000002", "pw12345")

        response = self.post(
            f"/billing/api/invoices/{invoice_id}/pay/",
            {"amount": "100.00", "payment_method": "cash"}, auth=auth,
        )
        assert response.status_code == 403, response.content

        clerk.user_permissions.add(
            Permission.objects.get(codename="process_payment")
        )
        auth = self.token_for("08013000002", "pw12345")
        response = self.post(
            f"/billing/api/invoices/{invoice_id}/pay/",
            {"amount": "100.00", "payment_method": "cash"}, auth=auth,
        )
        assert response.status_code == 200, response.content

    # --- items lock -------------------------------------------------------

    def test_items_locked_once_paid_against(self):
        invoice_id = self.make_invoice()
        self.post(f"/billing/api/invoices/{invoice_id}/pay/", {
            "amount": "500.00", "payment_method": "cash",
        })
        response = self.post("/billing/api/invoice-items/", {
            "invoice": invoice_id,
            "service": self.service.id,
            "quantity": 1,
            "unit_price": "2000.00",
        })
        assert response.status_code == 400
        assert "paid against" in response.json()["error"]

    # --- cashier summary --------------------------------------------------

    def test_summary_reports_outstanding_and_todays_collections(self):
        invoice_id = self.make_invoice()
        self.post(f"/billing/api/invoices/{invoice_id}/pay/", {
            "amount": "500.00", "payment_method": "cash",
        })
        summary = self.get("/billing/api/invoices/summary/").json()
        assert summary["invoices"] == 1
        assert Decimal(summary["outstanding"]) == Decimal("1500.00")
        assert Decimal(summary["collected_today"]) == Decimal("500.00")

    def test_payment_history_filters(self):
        invoice_id = self.make_invoice()
        self.post(f"/billing/api/invoices/{invoice_id}/pay/", {
            "amount": "500.00", "payment_method": "cash",
        })
        assert self.get("/billing/api/payments/?mine=true").json()["count"] == 1
        assert self.get(
            f"/billing/api/payments/?patient={self.patient.id}"
        ).json()["count"] == 1

    # --- catalogue --------------------------------------------------------

    def test_service_catalogue_search(self):
        # Other services may already be seeded, so match on the one we made.
        rows = self.get("/billing/api/services/?search=consultation").json()
        mine = [r for r in rows["results"] if r["id"] == self.service.id]
        assert mine, rows["count"]
        assert Decimal(mine[0]["price"]) == Decimal("2000.00")
        assert mine[0]["category_name"] == "Consultation"
