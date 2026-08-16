"""Radiology over the mobile API: orders, status, reporting, sign-off.

The guards are shared with the HTML views via radiology.services: a report
cannot be written before payment, editing a signed-off report is refused, and
verifying records who signed it — which the verification page never did.
"""
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import CustomUser, Role
from billing.models import Invoice, Payment, Service, ServiceCategory
from patients.models import Patient
from radiology.models import (
    RadiologyCategory, RadiologyOrder, RadiologyResult, RadiologyTest,
)


@override_settings(STRICT_ACCESS_CONTROL=True)
class RadiologyApiTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            phone_number="08015000001", username="radadmin", password="pw12345",
        )
        self.auth = self.token_for("08015000001", "pw12345")

        self.patient = Patient.objects.create(
            first_name="Ifeoma", last_name="Eze", date_of_birth="1992-02-02",
            gender="F", address="3 Imaging Road", city="Aba", state="Abia",
        )
        self.category = RadiologyCategory.objects.create(name="X-Ray")
        self.test = RadiologyTest.objects.create(
            name="Chest X-Ray", category=self.category, price=Decimal("8000.00"),
        )

    # --- helpers ----------------------------------------------------------

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

    def make_order(self, status_value="pending"):
        return RadiologyOrder.objects.create(
            patient=self.patient, test=self.test, referring_doctor=self.user,
            status=status_value,
        )

    def pay_for(self, order):
        """Settle the order's invoice the way the billing office would."""
        service_category = ServiceCategory.objects.create(name="Radiology")
        service = Service.objects.create(
            name="Imaging", category=service_category, price=Decimal("8000.00"),
        )
        invoice = Invoice.objects.create(
            patient=self.patient, invoice_date=timezone.now().date(),
            due_date=timezone.now().date(), subtotal=Decimal("8000.00"),
            tax_amount=Decimal("0.00"), discount_amount=Decimal("0.00"),
            total_amount=Decimal("8000.00"), status="pending",
            created_by=self.user, source_app="radiology",
        )
        invoice.items.create(
            service=service, description="Imaging", quantity=1,
            unit_price=Decimal("8000.00"),
        )
        Payment.objects.create(
            invoice=invoice, amount=invoice.total_amount, payment_method="cash",
            received_by=self.user,
        )
        invoice.refresh_from_db()
        order.invoice = invoice
        order.save()
        return invoice

    def report_payload(self, **extra):
        payload = {
            "findings": "Clear lung fields, no consolidation.",
            "impression": "Normal chest radiograph.",
            "image_quality": "good",
        }
        payload.update(extra)
        return payload

    def write_report(self, order):
        response = self.post(
            f"/radiology/api/orders/{order.id}/enter-result/", self.report_payload()
        )
        assert response.status_code == 201, response.content
        return response.json()["result"]["id"]

    # --- catalogue --------------------------------------------------------

    def test_catalogue_lists_tests_with_prices(self):
        rows = self.get("/radiology/api/tests/?search=Chest").json()
        match = [r for r in rows["results"] if r["id"] == self.test.id]
        assert match, rows["count"]
        assert match[0]["category_name"] == "X-Ray"
        assert Decimal(match[0]["price"]) == Decimal("8000.00")

    # --- orders -----------------------------------------------------------

    def test_create_order_records_referring_doctor(self):
        response = self.post("/radiology/api/orders/", {
            "patient": self.patient.id,
            "test": self.test.id,
            "priority": "urgent",
            "clinical_information": "Cough for two weeks",
        })
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["doctor_name"], "referring doctor should default to the caller"
        assert body["test_name"] == "Chest X-Ray"
        assert body["patient_number"] == self.patient.patient_id

    def test_unpaid_order_cannot_move_past_payment(self):
        order = self.make_order(status_value="awaiting_payment")
        response = self.post(
            f"/radiology/api/orders/{order.id}/set-status/", {"status": "scheduled"},
        )
        assert response.status_code == 400
        assert "Payment is still pending" in response.json()["error"]

        # Cancelling is the one move that stays open.
        response = self.post(
            f"/radiology/api/orders/{order.id}/set-status/", {"status": "cancelled"},
        )
        assert response.status_code == 200, response.content
        assert response.json()["status"] == "cancelled"

    def test_invalid_status_rejected(self):
        order = self.make_order()
        response = self.post(
            f"/radiology/api/orders/{order.id}/set-status/", {"status": "teleported"},
        )
        assert response.status_code == 400
        assert response.json()["error"] == "Invalid status."

    def test_scheduling_stamps_the_date(self):
        order = self.make_order(status_value="payment_confirmed")
        response = self.post(
            f"/radiology/api/orders/{order.id}/set-status/", {"status": "scheduled"},
        )
        assert response.status_code == 200, response.content
        assert response.json()["scheduled_date"]

    # --- reporting --------------------------------------------------------

    def test_report_blocked_until_payment(self):
        order = self.make_order(status_value="awaiting_payment")
        response = self.post(
            f"/radiology/api/orders/{order.id}/enter-result/", self.report_payload()
        )
        assert response.status_code == 400, response.content
        assert not RadiologyResult.objects.exists()

    def test_paid_invoice_unlocks_reporting(self):
        order = self.make_order(status_value="scheduled")
        self.pay_for(order)
        response = self.post(
            f"/radiology/api/orders/{order.id}/enter-result/", self.report_payload()
        )
        assert response.status_code == 201, response.content

    def test_report_requires_findings_and_impression(self):
        order = self.make_order(status_value="payment_confirmed")
        response = self.post(
            f"/radiology/api/orders/{order.id}/enter-result/",
            {"findings": "Clear.", "impression": ""},
        )
        assert response.status_code == 400
        assert "impression is required" in response.json()["error"]
        assert not RadiologyResult.objects.exists()

    def test_report_saved_and_order_answers_what_is_next(self):
        order = self.make_order(status_value="payment_confirmed")
        response = self.post(
            f"/radiology/api/orders/{order.id}/enter-result/",
            self.report_payload(is_abnormal=True, recommendations="CT if symptoms persist"),
        )
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["result"]["impression"] == "Normal chest radiograph."
        assert body["result"]["is_abnormal"] is True
        assert body["result"]["result_status"] == "submitted"
        assert body["result"]["is_verified"] is False
        assert body["order"]["can_add_result"] is True

    def test_second_report_updates_the_first(self):
        """One order has one report — a correction edits it, not a duplicate."""
        order = self.make_order(status_value="payment_confirmed")
        self.write_report(order)
        response = self.post(
            f"/radiology/api/orders/{order.id}/enter-result/",
            self.report_payload(impression="Right basal consolidation."),
        )
        assert response.status_code == 201, response.content
        assert RadiologyResult.objects.filter(order=order).count() == 1
        assert response.json()["result"]["impression"] == "Right basal consolidation."

    def test_report_accepts_an_uploaded_study(self):
        order = self.make_order(status_value="payment_confirmed")
        upload = SimpleUploadedFile(
            "chest.png", b"\x89PNG\r\n\x1a\nfake", content_type="image/png",
        )
        response = self.client.post(
            f"/radiology/api/orders/{order.id}/enter-result/",
            {**self.report_payload(), "images": upload},
            **self.auth,
        )
        assert response.status_code == 201, response.content
        assert response.json()["result"]["image_url"], "the app needs a URL to show"
        assert RadiologyResult.objects.get(order=order).images

    # --- sign-off ---------------------------------------------------------

    def test_verifying_records_who_and_when(self):
        order = self.make_order(status_value="payment_confirmed")
        result_id = self.write_report(order)

        response = self.post(
            f"/radiology/api/results/{result_id}/verify/", {"notes": "Agreed."}
        )
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["is_verified"] is True
        # verified_by was never set by the verification page, so who signed a
        # report off was lost.
        assert body["verified_by_name"], "verified_by must be persisted"
        assert body["verified_date"]
        assert "Agreed." in body["verification_notes"]

        order.refresh_from_db()
        assert order.status == "completed"

    def test_verifying_twice_refused(self):
        order = self.make_order(status_value="payment_confirmed")
        result_id = self.write_report(order)
        self.post(f"/radiology/api/results/{result_id}/verify/")

        response = self.post(f"/radiology/api/results/{result_id}/verify/")
        assert response.status_code == 400
        assert "already verified" in response.json()["error"]

    def test_signed_off_report_cannot_be_edited(self):
        order = self.make_order(status_value="payment_confirmed")
        result_id = self.write_report(order)
        self.post(f"/radiology/api/results/{result_id}/verify/")

        response = self.post(
            f"/radiology/api/orders/{order.id}/enter-result/",
            self.report_payload(impression="Actually abnormal."),
        )
        assert response.status_code == 400
        assert "cannot be edited" in response.json()["error"]
        assert RadiologyResult.objects.get(
            id=result_id
        ).impression == "Normal chest radiograph."

    def test_finalize_needs_verification_first(self):
        order = self.make_order(status_value="payment_confirmed")
        result_id = self.write_report(order)

        response = self.post(f"/radiology/api/results/{result_id}/finalize/")
        assert response.status_code == 400
        assert "Verify the report" in response.json()["error"]

        self.post(f"/radiology/api/results/{result_id}/verify/")
        response = self.post(f"/radiology/api/results/{result_id}/finalize/")
        assert response.status_code == 200, response.content
        assert response.json()["result_status"] == "finalized"

    def test_verification_needs_the_radiology_result_permission(self):
        order = self.make_order(status_value="payment_confirmed")
        result_id = self.write_report(order)

        viewer = CustomUser.objects.create_user(
            phone_number="08015000002", username="radviewer", password="pw12345",
        )
        role, _ = Role.objects.get_or_create(name="radiology_staff")
        viewer.roles.add(role)
        auth = self.token_for("08015000002", "pw12345")

        response = self.post(
            f"/radiology/api/results/{result_id}/verify/", auth=auth
        )
        assert response.status_code == 403, response.content

        viewer.user_permissions.add(
            Permission.objects.get(codename="change_radiologyresult")
        )
        auth = self.token_for("08015000002", "pw12345")
        response = self.post(
            f"/radiology/api/results/{result_id}/verify/", auth=auth
        )
        assert response.status_code == 200, response.content

    def test_unverified_filter_finds_reports_waiting_for_sign_off(self):
        order = self.make_order(status_value="payment_confirmed")
        self.write_report(order)
        rows = self.get("/radiology/api/results/?unverified=true").json()
        assert rows["count"] == 1
