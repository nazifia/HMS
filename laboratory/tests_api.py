"""Laboratory over the mobile API: requests, status, result entry, sign-off.

The guards that matter are shared with the HTML views via laboratory.services:
results cannot be entered before payment, and a request is complete only once
every test has a *verified* result — entering a result is not sign-off.
"""
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import CustomUser, Role
from billing.models import Invoice, Payment, Service, ServiceCategory
from laboratory.models import (
    Test, TestCategory, TestParameter, TestRequest, TestResult,
)
from patients.models import Patient


@override_settings(STRICT_ACCESS_CONTROL=True)
class LaboratoryApiTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            phone_number="08012000001", username="labadmin", password="pw12345",
        )
        self.auth = self.token_for("08012000001", "pw12345")

        self.patient = Patient.objects.create(
            first_name="Tunde", last_name="Alabi", date_of_birth="1980-06-06",
            gender="M", address="4 Aba Road", city="Aba", state="Abia",
        )
        category = TestCategory.objects.create(name="Haematology")
        self.test = Test.objects.create(
            name="Full Blood Count", category=category, price=Decimal("3500.00"),
            sample_type="blood",
        )
        self.haemoglobin = TestParameter.objects.create(
            test=self.test, name="Haemoglobin", unit="g/dL",
            normal_range="12-16", order=1,
        )
        self.wbc = TestParameter.objects.create(
            test=self.test, name="WBC", unit="10^9/L", normal_range="4-11", order=2,
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

    def make_request(self, status_value="pending"):
        test_request = TestRequest.objects.create(
            patient=self.patient, doctor=self.user, status=status_value,
        )
        test_request.tests.add(self.test)
        return test_request

    def pay_for(self, test_request):
        """Settle the request's invoice the way the billing office would."""
        service_category = ServiceCategory.objects.create(name="Laboratory")
        service = Service.objects.create(
            name="Lab Test", category=service_category, price=Decimal("3500.00"),
        )
        invoice = Invoice.objects.create(
            patient=self.patient, invoice_date=timezone.now().date(),
            due_date=timezone.now().date(), subtotal=Decimal("3500.00"),
            tax_amount=Decimal("0.00"), discount_amount=Decimal("0.00"),
            total_amount=Decimal("3500.00"), status="pending",
            created_by=self.user, source_app="laboratory",
        )
        invoice.items.create(
            service=service, description="Lab", quantity=1,
            unit_price=Decimal("3500.00"),
        )
        Payment.objects.create(
            invoice=invoice, amount=invoice.total_amount, payment_method="cash",
            received_by=self.user,
        )
        invoice.refresh_from_db()
        test_request.invoice = invoice
        test_request.save()
        return invoice

    # --- catalogue --------------------------------------------------------

    def test_catalogue_lists_parameters(self):
        rows = self.get(f"/laboratory/api/tests/?search=Full Blood Count").json()
        match = [r for r in rows["results"] if r["id"] == self.test.id]
        assert match, rows["count"]
        assert [p["name"] for p in match[0]["parameters"]] == [
            "Haemoglobin", "WBC",
        ]

    # --- requests ---------------------------------------------------------

    def test_create_request_records_ordering_doctor(self):
        response = self.post("/laboratory/api/requests/", {
            "patient": self.patient.id,
            "tests": [self.test.id],
            "priority": "urgent",
        })
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["doctor_name"], "ordering doctor should default to the caller"
        assert Decimal(body["total_price"]) == Decimal("3500.00")
        assert body["patient_number"] == self.patient.patient_id

    def test_unpaid_request_cannot_move_past_payment(self):
        test_request = self.make_request(status_value="awaiting_payment")
        response = self.post(
            f"/laboratory/api/requests/{test_request.id}/set_status/",
            {"status": "sample_collected"},
        )
        assert response.status_code == 400
        assert "Payment is still pending" in response.json()["error"]

        # Cancelling is the one move that stays open.
        response = self.post(
            f"/laboratory/api/requests/{test_request.id}/set_status/",
            {"status": "cancelled"},
        )
        assert response.status_code == 200, response.content
        assert response.json()["status"] == "cancelled"

    def test_invalid_status_rejected(self):
        test_request = self.make_request()
        response = self.post(
            f"/laboratory/api/requests/{test_request.id}/set_status/",
            {"status": "teleported"},
        )
        assert response.status_code == 400
        assert response.json()["error"] == "Invalid status."

    # --- results ----------------------------------------------------------

    def test_results_blocked_until_payment(self):
        test_request = self.make_request(status_value="awaiting_payment")
        response = self.post(
            f"/laboratory/api/requests/{test_request.id}/enter-result/",
            {"test": self.test.id, "parameters": {str(self.haemoglobin.id): {"value": "13"}}},
        )
        assert response.status_code == 400, response.content
        assert "Payment is pending" in response.json()["error"]
        assert not TestResult.objects.exists()

    def test_enter_result_saves_parameters_and_advances_status(self):
        test_request = self.make_request(status_value="payment_confirmed")
        response = self.post(
            f"/laboratory/api/requests/{test_request.id}/enter-result/",
            {
                "test": self.test.id,
                "notes": "Sample slightly haemolysed",
                "parameters": {
                    str(self.haemoglobin.id): {"value": "9.1", "is_normal": False},
                    str(self.wbc.id): {"value": "7.4", "is_normal": True},
                },
            },
        )
        assert response.status_code == 201, response.content
        body = response.json()
        values = {p["name"]: p for p in body["result"]["parameters"]}
        assert values["Haemoglobin"]["value"] == "9.1"
        assert values["Haemoglobin"]["is_normal"] is False
        assert values["Haemoglobin"]["unit"] == "g/dL"
        assert body["test_request"]["status"] == "processing"

    def test_paid_invoice_unlocks_result_entry(self):
        test_request = self.make_request(status_value="pending")
        self.pay_for(test_request)
        response = self.post(
            f"/laboratory/api/requests/{test_request.id}/enter-result/",
            {"test": self.test.id,
             "parameters": {str(self.haemoglobin.id): {"value": "14"}}},
        )
        assert response.status_code == 201, response.content

    def test_duplicate_result_refused(self):
        test_request = self.make_request(status_value="payment_confirmed")
        payload = {
            "test": self.test.id,
            "parameters": {str(self.haemoglobin.id): {"value": "12"}},
        }
        assert self.post(
            f"/laboratory/api/requests/{test_request.id}/enter-result/", payload
        ).status_code == 201
        response = self.post(
            f"/laboratory/api/requests/{test_request.id}/enter-result/", payload
        )
        assert response.status_code == 400, response.content
        assert "already has a result" in response.json()["error"]
        assert TestResult.objects.filter(
            test_request=test_request, test=self.test
        ).count() == 1

    def test_result_for_test_not_on_request_refused(self):
        other = Test.objects.create(
            name="Urinalysis", price=Decimal("1500.00"), sample_type="urine",
        )
        test_request = self.make_request(status_value="payment_confirmed")
        response = self.post(
            f"/laboratory/api/requests/{test_request.id}/enter-result/",
            {"test": other.id},
        )
        assert response.status_code == 400
        assert "not part of this test request" in response.json()["error"]

    # --- verification -----------------------------------------------------

    def enter_result(self, test_request):
        response = self.post(
            f"/laboratory/api/requests/{test_request.id}/enter-result/",
            {"test": self.test.id,
             "parameters": {str(self.haemoglobin.id): {"value": "13.2"}}},
        )
        assert response.status_code == 201, response.content
        return response.json()["result"]["id"]

    def test_verifying_records_who_and_when(self):
        test_request = self.make_request(status_value="payment_confirmed")
        result_id = self.enter_result(test_request)

        response = self.post(f"/laboratory/api/results/{result_id}/verify/")
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["is_verified"] is True
        assert body["verified_by_name"]
        # verified_date used to be assigned to a non-existent field, so it was
        # silently dropped and blew up when read back.
        assert body["verified_date"], "verified_date must be persisted"

        test_request.refresh_from_db()
        assert test_request.status == "completed"

    def test_second_test_keeps_request_open_until_both_verified(self):
        second = Test.objects.create(
            name="ESR", price=Decimal("1200.00"), sample_type="blood",
        )
        test_request = self.make_request(status_value="payment_confirmed")
        test_request.tests.add(second)

        result_id = self.enter_result(test_request)
        self.post(f"/laboratory/api/results/{result_id}/verify/")
        test_request.refresh_from_db()
        assert test_request.status == "processing", test_request.status

    def test_verifying_twice_refused(self):
        test_request = self.make_request(status_value="payment_confirmed")
        result_id = self.enter_result(test_request)
        self.post(f"/laboratory/api/results/{result_id}/verify/")

        response = self.post(f"/laboratory/api/results/{result_id}/verify/")
        assert response.status_code == 400
        assert "already verified" in response.json()["error"]

    def test_empty_result_cannot_be_verified(self):
        test_request = self.make_request(status_value="payment_confirmed")
        result = TestResult.objects.create(
            test_request=test_request, test=self.test, performed_by=self.user,
        )
        response = self.post(f"/laboratory/api/results/{result.id}/verify/")
        assert response.status_code == 400
        assert "Nothing to verify" in response.json()["error"]

    def test_verification_needs_the_lab_result_permission(self):
        test_request = self.make_request(status_value="payment_confirmed")
        result_id = self.enter_result(test_request)

        viewer = CustomUser.objects.create_user(
            phone_number="08012000002", username="labviewer", password="pw12345",
        )
        role, _ = Role.objects.get_or_create(name="lab_technician")
        viewer.roles.add(role)
        auth = self.token_for("08012000002", "pw12345")

        response = self.post(
            f"/laboratory/api/results/{result_id}/verify/", auth=auth
        )
        assert response.status_code == 403, response.content

        viewer.user_permissions.add(
            Permission.objects.get(codename="enter_testresults")
        )
        auth = self.token_for("08012000002", "pw12345")
        response = self.post(
            f"/laboratory/api/results/{result_id}/verify/", auth=auth
        )
        assert response.status_code == 200, response.content

    def test_entering_a_result_does_not_complete_the_request(self):
        """Completion means sign-off: an unverified result leaves it open."""
        test_request = self.make_request(status_value="payment_confirmed")
        self.enter_result(test_request)
        test_request.refresh_from_db()
        assert test_request.status == "processing", test_request.status

    def test_deleting_the_only_result_reopens_a_completed_request(self):
        test_request = self.make_request(status_value="payment_confirmed")
        result_id = self.enter_result(test_request)
        self.post(f"/laboratory/api/results/{result_id}/verify/")
        test_request.refresh_from_db()
        assert test_request.status == "completed"

        TestResult.objects.get(id=result_id).delete()
        test_request.refresh_from_db()
        assert test_request.status == "processing", test_request.status

    def test_resync_command_reopens_requests_closed_under_the_old_rule(self):
        from io import StringIO

        from django.core.management import call_command

        test_request = self.make_request(status_value="payment_confirmed")
        self.enter_result(test_request)
        # Simulate a request closed by the old "results exist" rule.
        TestRequest.objects.filter(id=test_request.id).update(status="completed")

        out = StringIO()
        call_command("resync_test_request_status", "--dry-run", stdout=out)
        assert "completed -> processing" in out.getvalue()
        test_request.refresh_from_db()
        assert test_request.status == "completed", "dry run must not save"

        call_command("resync_test_request_status", stdout=StringIO())
        test_request.refresh_from_db()
        assert test_request.status == "processing"
