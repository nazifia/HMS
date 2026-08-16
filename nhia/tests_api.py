"""NHIA / desk office over the mobile API: issuing, verifying and cancelling
authorization codes, and clearing the queue of work waiting on one.

The rule that matters is that authorizing something *attaches* the code: a code
issued and left unlinked leaves the ward blocked and the item in the queue,
which is what the bulk-authorize pages used to do.
"""
from datetime import timedelta
from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import CustomUser, Department, Role
from consultations.models import Consultation, ConsultingRoom, Referral
from laboratory.models import Test, TestRequest
from nhia.api.serializers import KIND_LABELS
from nhia.models import AuthorizationCode, NHIAPatient
from nhia.services import AUTHORIZABLE
from patients.models import Patient


@override_settings(STRICT_ACCESS_CONTROL=True)
class NhiaApiTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            phone_number="08014000001", username="deskoffice", password="pw12345",
        )
        self.auth = self.token_for("08014000001", "pw12345")

        self.patient = Patient.objects.create(
            first_name="Ngozi", last_name="Obi", date_of_birth="1988-03-03",
            gender="F", address="7 Scheme Road", city="Aba", state="Abia",
            patient_type="nhia",
        )
        NHIAPatient.objects.create(
            patient=self.patient, nhia_reg_number="NHIA-0001",
        )
        self.self_pay = Patient.objects.create(
            first_name="Emeka", last_name="Udo", date_of_birth="1975-05-05",
            gender="M", address="9 Cash Road", city="Aba", state="Abia",
        )

        # A consulting room outside NHIA is what makes a consultation need a code.
        # Departments are seeded by migrations, so take the row rather than a
        # second one with the same name.
        self.department, _ = Department.objects.get_or_create(
            name="General Medicine"
        )
        self.room = ConsultingRoom.objects.create(
            room_number="C1", floor="1", department=self.department,
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

    def make_consultation(self, patient=None):
        return Consultation.objects.create(
            patient=patient or self.patient,
            doctor=self.user,
            consulting_room=self.room,
            chief_complaint="Headache for two days",
        )

    def make_referral(self):
        return Referral.objects.create(
            patient=self.patient,
            referring_doctor=self.user,
            referred_to_department=self.department,
            reason="Second opinion",
            requires_authorization=True,
            authorization_status="required",
        )

    def issue(self, amount="7500.00", **extra):
        payload = {
            "patient": self.patient.id,
            "amount": amount,
            "service_type": "laboratory",
        }
        payload.update(extra)
        return self.post("/nhia/api/authorization-codes/", payload)

    # --- issuing ----------------------------------------------------------

    def test_issuing_a_code_records_who_and_what_it_covers(self):
        response = self.issue()
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["code"].startswith("AUTH-")
        assert body["patient_name"] == self.patient.get_full_name()
        assert body["nhia_number"] == "NHIA-0001"
        assert Decimal(body["amount"]) == Decimal("7500.00")
        assert body["status"] == "active"
        assert body["is_usable"] is True
        assert body["generated_by_name"]

        code = AuthorizationCode.objects.get(id=body["id"])
        assert code.expiry_date == timezone.now().date() + timedelta(days=30)

    def test_manual_code_accepted_and_must_be_unique(self):
        response = self.issue(code="ward-book-14")
        assert response.status_code == 201, response.content
        assert response.json()["code"] == "WARD-BOOK-14"

        response = self.issue(code="WARD-BOOK-14")
        assert response.status_code == 400
        assert "already exists" in response.json()["error"]
        assert AuthorizationCode.objects.count() == 1

    def test_non_nhia_patient_cannot_be_given_a_code(self):
        response = self.post("/nhia/api/authorization-codes/", {
            "patient": self.self_pay.id, "amount": "5000.00",
        })
        assert response.status_code == 400
        assert "not an active NHIA patient" in response.json()["error"]
        assert not AuthorizationCode.objects.exists()

    def test_zero_amount_refused(self):
        response = self.issue(amount="0")
        assert response.status_code == 400
        assert "amount this authorization covers" in response.json()["error"]
        assert not AuthorizationCode.objects.exists()

    # --- verifying --------------------------------------------------------

    def test_verify_reports_why_a_code_cannot_be_used(self):
        code = self.issue().json()["code"]

        body = self.get(f"/nhia/api/authorization-codes/verify/?code={code}").json()
        assert body["valid"] is True
        assert body["code"]["code"] == code

        # A laboratory code is not a theatre code.
        body = self.get(
            f"/nhia/api/authorization-codes/verify/?code={code}&service_type=theatre"
        ).json()
        assert body["valid"] is False
        assert "Laboratory" in body["message"]

    def test_verify_unknown_code_is_a_404_not_a_crash(self):
        response = self.get("/nhia/api/authorization-codes/verify/?code=NOPE")
        assert response.status_code == 404
        assert response.json()["valid"] is False

    def test_expired_code_is_not_usable(self):
        code = AuthorizationCode.objects.create(
            code="AUTH-OLD", patient=self.patient, service_type="general",
            amount=Decimal("1000.00"),
            expiry_date=timezone.now().date() - timedelta(days=1),
            status="active",
        )
        body = self.get(
            f"/nhia/api/authorization-codes/verify/?code={code.code}"
        ).json()
        assert body["valid"] is False
        code.refresh_from_db()
        assert code.status == "expired", "listing should retire stale codes"

    # --- cancelling -------------------------------------------------------

    def test_cancelling_an_active_code_and_not_a_used_one(self):
        code_id = self.issue().json()["id"]
        response = self.post(f"/nhia/api/authorization-codes/{code_id}/cancel/")
        assert response.status_code == 200, response.content
        assert response.json()["status"] == "cancelled"

        response = self.post(f"/nhia/api/authorization-codes/{code_id}/cancel/")
        assert response.status_code == 400
        assert "Only active codes" in response.json()["error"]

    # --- the queue --------------------------------------------------------

    def test_pending_queue_merges_every_module(self):
        consultation = self.make_consultation()
        assert consultation.requires_authorization, "setup should need a code"
        self.make_referral()

        body = self.get("/nhia/api/pending/").json()
        assert body["counts"]["consultation"] == 1
        assert body["counts"]["referral"] == 1
        assert body["counts"]["total"] == 2

        kinds = {row["kind"] for row in body["results"]}
        assert kinds == {"consultation", "referral"}
        row = [r for r in body["results"] if r["kind"] == "referral"][0]
        assert row["patient_name"] == self.patient.get_full_name()
        assert Decimal(row["estimated_amount"]) > 0

    def test_pending_queue_filters_by_kind(self):
        self.make_consultation()
        self.make_referral()
        body = self.get("/nhia/api/pending/?kind=referral").json()
        assert [row["kind"] for row in body["results"]] == ["referral"]

    def test_authorizing_attaches_the_code_and_clears_the_queue(self):
        consultation = self.make_consultation()
        response = self.post(
            f"/nhia/api/pending/consultation/{consultation.id}/authorize/",
            {"amount": "5000.00"},
        )
        assert response.status_code == 201, response.content
        code = response.json()

        consultation.refresh_from_db()
        assert consultation.authorization_code_id == code["id"], (
            "a code that is not attached leaves the consultation blocked"
        )
        assert consultation.authorization_status == "authorized"
        assert self.get("/nhia/api/pending/").json()["counts"]["consultation"] == 0

    def test_authorizing_twice_refused(self):
        consultation = self.make_consultation()
        path = f"/nhia/api/pending/consultation/{consultation.id}/authorize/"
        assert self.post(path, {"amount": "5000.00"}).status_code == 201

        response = self.post(path, {"amount": "5000.00"})
        assert response.status_code == 400
        assert "already authorized" in response.json()["error"]
        assert AuthorizationCode.objects.count() == 1

    def test_authorizing_something_that_does_not_need_it_refused(self):
        consultation = self.make_consultation(patient=self.self_pay)
        assert not consultation.requires_authorization

        response = self.post(
            f"/nhia/api/pending/consultation/{consultation.id}/authorize/",
            {"amount": "5000.00"},
        )
        assert response.status_code == 400
        assert "does not require authorization" in response.json()["error"]

    def test_referral_amount_defaults_to_the_estimate(self):
        referral = self.make_referral()
        response = self.post(
            f"/nhia/api/pending/referral/{referral.id}/authorize/"
        )
        assert response.status_code == 201, response.content
        # General Medicine has no special rate, so the base referral cost.
        assert Decimal(response.json()["amount"]) == Decimal("10000.00")

    def test_lab_request_amount_defaults_to_the_tests_ordered(self):
        test = Test.objects.create(
            name="Full Blood Count", price=Decimal("3500.00"), sample_type="blood",
        )
        request = TestRequest.objects.create(
            patient=self.patient, doctor=self.user,
            requires_authorization=True, authorization_status="required",
        )
        request.tests.add(test)

        response = self.post(
            f"/nhia/api/pending/laboratory/{request.id}/authorize/"
        )
        assert response.status_code == 201, response.content
        assert Decimal(response.json()["amount"]) == Decimal("3500.00")

        request.refresh_from_db()
        assert request.authorization_status == "authorized"

    def test_unknown_kind_refused(self):
        response = self.post("/nhia/api/pending/teleport/1/authorize/")
        assert response.status_code == 400
        assert "Unknown authorization type" in response.json()["error"]

    def test_issuing_needs_the_authorization_permission(self):
        consultation = self.make_consultation()
        clerk = CustomUser.objects.create_user(
            phone_number="08014000002", username="clerk", password="pw12345",
        )
        role, _ = Role.objects.get_or_create(name="receptionist")
        clerk.roles.add(role)
        auth = self.token_for("08014000002", "pw12345")

        response = self.post(
            f"/nhia/api/pending/consultation/{consultation.id}/authorize/",
            {"amount": "5000.00"}, auth=auth,
        )
        assert response.status_code == 403, response.content
        consultation.refresh_from_db()
        assert consultation.authorization_code_id is None

    # --- registrations ----------------------------------------------------

    def test_nhia_patient_lookup_by_scheme_number(self):
        rows = self.get("/nhia/api/nhia-patients/?search=NHIA-0001").json()
        assert rows["count"] == 1
        assert rows["results"][0]["patient_name"] == self.patient.get_full_name()

    def test_every_authorizable_kind_has_a_label(self):
        assert set(KIND_LABELS) == set(AUTHORIZABLE)
