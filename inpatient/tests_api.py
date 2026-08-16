"""Inpatient over the mobile API: wards, admitting, transferring, discharging.

The rules are shared with the HTML views via inpatient.services: an occupied
bed cannot take a second patient, a discharge frees the bed and stamps the
date, a transfer writes history on both sides, and the daily charge lands once
per day however many times the job runs.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import CustomUser, Role
from billing.models import Invoice, Service, ServiceCategory
from inpatient.models import Admission, Bed, BedTransfer, Ward, WardTransfer
from inpatient.services import admit_patient, charge_admission_for_date
from patients.models import Patient, PatientWallet, WalletTransaction


@override_settings(STRICT_ACCESS_CONTROL=True)
class InpatientApiTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            phone_number="08013000001", username="wardadmin", password="pw12345",
        )
        self.auth = self.token_for("08013000001", "pw12345")

        self.patient = Patient.objects.create(
            first_name="Ada", last_name="Nwosu", date_of_birth="1990-01-01",
            gender="F", address="1 Ward Road", city="Aba", state="Abia",
        )
        self.ward = Ward.objects.create(
            name="Male Medical", ward_type="general", floor="1", capacity=2,
            charge_per_day=Decimal("5000.00"),
        )
        self.bed = Bed.objects.create(ward=self.ward, bed_number="1")
        self.other_bed = Bed.objects.create(ward=self.ward, bed_number="2")

        category = ServiceCategory.objects.create(name="Inpatient")
        self.service = Service.objects.create(
            name="Admission Fee", category=category, price=Decimal("20000.00"),
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

    def admit(self, bed=None, patient=None, service=None):
        return self.post("/inpatient/api/admissions/", {
            "patient": (patient or self.patient).id,
            "bed": (bed or self.bed).id,
            "attending_doctor": self.user.id,
            "diagnosis": "Malaria",
            "reason_for_admission": "Fever for three days",
            "admission_service": (service or self.service).id,
        })

    def make_admission(self, bed=None, patient=None):
        """Admit without a service, so setup does not charge anything."""
        admission, _ = admit_patient(
            patient=patient or self.patient,
            bed=bed or self.bed,
            attending_doctor=self.user,
            diagnosis="Malaria",
            reason_for_admission="Fever",
            user=self.user,
        )
        return admission

    # --- ward board -------------------------------------------------------

    def test_ward_board_reports_live_bed_counts(self):
        self.make_admission()
        row = [
            w for w in self.get("/inpatient/api/wards/").json()["results"]
            if w["id"] == self.ward.id
        ][0]
        assert row["total_beds"] == 2
        assert row["occupied_beds"] == 1
        assert row["available_beds"] == 1

    def test_free_beds_filter_excludes_the_occupied_one(self):
        self.make_admission()
        rows = self.get(
            f"/inpatient/api/beds/?ward={self.ward.id}&free=true"
        ).json()["results"]
        assert [b["bed_number"] for b in rows] == ["2"]

        occupied = self.get(f"/inpatient/api/beds/?ward={self.ward.id}").json()
        by_number = {b["bed_number"]: b for b in occupied["results"]}
        assert by_number["1"]["patient_name"] == self.patient.get_full_name()

    # --- admitting --------------------------------------------------------

    def test_admitting_takes_the_bed_and_charges_the_wallet(self):
        response = self.admit()
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["ward_name"] == "Male Medical"
        assert body["is_active"] is True

        self.bed.refresh_from_db()
        assert self.bed.is_occupied

        # One invoice only: a post_save fallback used to raise a second one and
        # charge the wallet twice for the same admission.
        assert Invoice.objects.count() == 1
        invoice = Invoice.objects.get(id=body["invoice"])
        assert invoice.total_amount == Decimal("20000.00")
        assert invoice.status == "pending"

        wallet = PatientWallet.objects.get(patient=self.patient)
        assert wallet.balance == Decimal("-20000.00"), (
            wallet.balance,
            list(WalletTransaction.objects.values_list(
                "transaction_type", "amount", "balance_after")),
        )
        assert WalletTransaction.objects.filter(
            admission_id=body["id"], transaction_type="admission_fee",
        ).count() == 1

    def test_admitting_into_an_occupied_bed_refused(self):
        self.make_admission()
        other = Patient.objects.create(
            first_name="Bode", last_name="Ade", date_of_birth="1985-01-01",
            gender="M", address="2 Ward Road", city="Aba", state="Abia",
        )
        response = self.admit(patient=other)
        assert response.status_code == 400, response.content
        assert "already occupied" in response.json()["error"]
        assert Admission.objects.count() == 1
        assert not Invoice.objects.exists()

    def test_admitting_a_patient_who_is_already_admitted_refused(self):
        self.make_admission()
        response = self.admit(bed=self.other_bed)
        assert response.status_code == 400
        assert "already admitted" in response.json()["error"]
        self.other_bed.refresh_from_db()
        assert not self.other_bed.is_occupied

    def test_admitting_into_an_out_of_service_bed_refused(self):
        self.bed.is_active = False
        self.bed.save()
        response = self.admit()
        assert response.status_code == 400
        assert "out of service" in response.json()["error"]

    # --- transferring -----------------------------------------------------

    def test_transfer_moves_the_patient_and_writes_history(self):
        admission = self.make_admission()
        theatre_ward = Ward.objects.create(
            name="Female Medical", ward_type="general", floor="2", capacity=1,
            charge_per_day=Decimal("7000.00"),
        )
        target = Bed.objects.create(ward=theatre_ward, bed_number="A")

        response = self.post(
            f"/inpatient/api/admissions/{admission.id}/transfer/",
            {"bed": target.id, "notes": "Needs closer monitoring"},
        )
        assert response.status_code == 200, response.content
        assert response.json()["ward_name"] == "Female Medical"

        admission.refresh_from_db()
        self.bed.refresh_from_db()
        target.refresh_from_db()
        assert admission.bed_id == target.id
        assert not self.bed.is_occupied
        assert target.is_occupied

        assert BedTransfer.objects.filter(
            admission=admission, from_bed=self.bed, to_bed=target
        ).count() == 1
        assert WardTransfer.objects.filter(
            admission=admission, from_ward=self.ward, to_ward=theatre_ward
        ).count() == 1

    def test_transfer_within_a_ward_writes_no_ward_history(self):
        admission = self.make_admission()
        response = self.post(
            f"/inpatient/api/admissions/{admission.id}/transfer/",
            {"bed": self.other_bed.id},
        )
        assert response.status_code == 200, response.content
        assert BedTransfer.objects.count() == 1
        assert not WardTransfer.objects.exists()

    def test_transfer_into_an_occupied_bed_refused(self):
        admission = self.make_admission()
        other = Patient.objects.create(
            first_name="Chi", last_name="Eze", date_of_birth="1970-01-01",
            gender="F", address="3 Ward Road", city="Aba", state="Abia",
        )
        self.make_admission(bed=self.other_bed, patient=other)

        response = self.post(
            f"/inpatient/api/admissions/{admission.id}/transfer/",
            {"bed": self.other_bed.id},
        )
        assert response.status_code == 400
        assert "already occupied" in response.json()["error"]
        admission.refresh_from_db()
        assert admission.bed_id == self.bed.id
        assert not BedTransfer.objects.exists()

    # --- discharging ------------------------------------------------------

    def test_discharge_frees_the_bed_and_stamps_the_date(self):
        admission = self.make_admission()
        response = self.post(
            f"/inpatient/api/admissions/{admission.id}/discharge/",
            {"discharge_notes": "Recovered"},
        )
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["status"] == "discharged"
        assert body["discharge_date"]
        assert body["is_active"] is False

        self.bed.refresh_from_db()
        assert not self.bed.is_occupied

    def test_discharging_twice_refused(self):
        admission = self.make_admission()
        self.post(f"/inpatient/api/admissions/{admission.id}/discharge/")
        response = self.post(
            f"/inpatient/api/admissions/{admission.id}/discharge/"
        )
        assert response.status_code == 400
        assert "already discharged" in response.json()["error"]

    def test_discharge_needs_the_discharge_permission(self):
        admission = self.make_admission()
        nurse = CustomUser.objects.create_user(
            phone_number="08013000002", username="wardnurse", password="pw12345",
        )
        role, _ = Role.objects.get_or_create(name="nurse")
        nurse.roles.add(role)
        auth = self.token_for("08013000002", "pw12345")

        response = self.post(
            f"/inpatient/api/admissions/{admission.id}/discharge/", auth=auth
        )
        assert response.status_code == 403, response.content
        admission.refresh_from_db()
        assert admission.status == "admitted"

        nurse.user_permissions.add(
            Permission.objects.get(codename="discharge_patient")
        )
        auth = self.token_for("08013000002", "pw12345")
        response = self.post(
            f"/inpatient/api/admissions/{admission.id}/discharge/", auth=auth
        )
        assert response.status_code == 200, response.content

    # --- charges ----------------------------------------------------------

    def test_charges_endpoint_reports_what_is_outstanding(self):
        admission = self.make_admission()
        # Backdate without a save(): saving an admission accrues the extra days
        # itself (billing.signals), and this test is about reporting, not that.
        Admission.objects.filter(pk=admission.pk).update(
            admission_date=timezone.now() - timedelta(days=3)
        )
        admission.refresh_from_db()

        body = self.get(
            f"/inpatient/api/admissions/{admission.id}/charges/"
        ).json()
        assert body["duration_days"] == 3
        assert Decimal(body["billed"]) == Decimal("15000.00")
        assert Decimal(body["paid"]) == Decimal("0.00"), (
            body,
            list(WalletTransaction.objects.values_list(
                "transaction_type", "amount", "admission_id")),
        )
        assert Decimal(body["outstanding"]) == Decimal("15000.00")
        assert Decimal(body["daily_charge"]) == Decimal("5000.00")

    def test_daily_charge_lands_once_per_day(self):
        admission = self.make_admission()
        today = timezone.now().date()

        amount, _ = charge_admission_for_date(admission, today)
        assert amount == Decimal("5000.00")

        amount, reason = charge_admission_for_date(admission, today)
        assert amount is None
        assert reason == "Already charged for this date"

        assert WalletTransaction.objects.filter(
            admission=admission, transaction_type="daily_admission_charge",
        ).count() == 1
        wallet = PatientWallet.objects.get(patient=self.patient)
        assert wallet.balance == Decimal("-5000.00"), (
            wallet.balance,
            list(WalletTransaction.objects.values_list(
                "transaction_type", "amount", "balance_after")),
        )

    def test_no_daily_charge_after_discharge(self):
        admission = self.make_admission()
        self.post(f"/inpatient/api/admissions/{admission.id}/discharge/")
        admission.refresh_from_db()

        amount, reason = charge_admission_for_date(
            admission, timezone.now().date() + timedelta(days=1)
        )
        assert amount is None
        assert reason == "Charge date is after discharge"

    # --- ward round -------------------------------------------------------

    def test_round_and_nursing_note_record_their_author(self):
        admission = self.make_admission()
        response = self.post("/inpatient/api/rounds/", {
            "admission": admission.id,
            "notes": "Afebrile, chest clear",
            "treatment_instructions": "Continue IV fluids",
        })
        assert response.status_code == 201, response.content
        assert response.json()["doctor_name"] == self.user.get_full_name()

        response = self.post("/inpatient/api/nursing-notes/", {
            "admission": admission.id,
            "notes": "Slept well",
            "vital_signs": "BP 120/80",
        })
        assert response.status_code == 201, response.content
        assert response.json()["nurse_name"] == self.user.get_full_name()

        rows = self.get(
            f"/inpatient/api/rounds/?admission={admission.id}"
        ).json()
        assert rows["count"] == 1

    def test_admission_list_defaults_to_current_inpatients(self):
        admission = self.make_admission()
        self.post(f"/inpatient/api/admissions/{admission.id}/discharge/")

        assert self.get("/inpatient/api/admissions/").json()["count"] == 0
        assert self.get(
            "/inpatient/api/admissions/?status=all"
        ).json()["count"] == 1
