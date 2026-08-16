"""Patients over the mobile API: register, search, vitals, history, wallet."""
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import Client, TestCase, override_settings

from accounts.models import CustomUser, Role
from patients.models import Patient, PatientWallet, Vitals


@override_settings(STRICT_ACCESS_CONTROL=True)
class PatientApiTest(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            phone_number="08011000001", username="recadmin", password="pw12345",
        )
        self.auth = self.token_for("08011000001", "pw12345")
        self.patient = Patient.objects.create(
            first_name="Chidi", last_name="Okafor", date_of_birth="1988-03-03",
            gender="M", phone_number="08021000002", address="1 Ring Road",
            city="Enugu", state="Enugu",
        )

    def token_for(self, phone, password):
        response = Client().post(
            "/api/accounts/login/",
            {"phone_number": phone, "password": password},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        return {"HTTP_AUTHORIZATION": f"Token {response.json()['token']}"}

    def staff_user(self, phone, username, *codenames):
        """Clinical staff holding only `codenames` (the role gets them past
        StrictAccessControlMiddleware's patients.view)."""
        user = CustomUser.objects.create_user(
            phone_number=phone, username=username, password="pw12345",
        )
        role, _ = Role.objects.get_or_create(name="nurse")
        user.roles.add(role)
        if codenames:
            user.user_permissions.add(
                *Permission.objects.filter(codename__in=codenames)
            )
        return user, self.token_for(phone, "pw12345")

    def get(self, path, auth=None):
        return self.client.get(path, **(auth or self.auth))

    def post(self, path, payload=None, auth=None):
        return self.client.post(
            path, payload or {}, content_type="application/json",
            **(auth or self.auth),
        )

    # --- register / search ----------------------------------------------

    def test_register_generates_patient_id(self):
        response = self.post("/patients/api/patients/", {
            "first_name": "Amina", "last_name": "Bello",
            "date_of_birth": "1995-07-07", "gender": "F",
            "address": "2 Kano Road", "city": "Kano", "state": "Kano",
        })
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["patient_id"], "patient_id should be generated on save"
        assert body["full_name"] == "Amina Bello"
        assert body["age"] is not None

    def test_search_matches_name_id_and_phone(self):
        for term in ("okafor", self.patient.patient_id, "08021000002"):
            rows = self.get(f"/patients/api/patients/?search={term}").json()
            assert rows["count"] == 1, (term, rows["count"])

        assert self.get(
            "/patients/api/patients/?search=nosuchperson"
        ).json()["count"] == 0

    def test_inactive_patients_hidden_by_default(self):
        self.patient.is_active = False
        self.patient.save()
        assert self.get("/patients/api/patients/").json()["count"] == 0
        assert self.get("/patients/api/patients/?active=all").json()["count"] == 1

    # --- permissions ------------------------------------------------------

    def test_read_only_staff_cannot_register(self):
        _, auth = self.staff_user("08011000003", "readnurse", "view_patient")
        assert self.get("/patients/api/patients/", auth=auth).status_code == 200

        response = self.post("/patients/api/patients/", {
            "first_name": "Nope", "last_name": "Nope",
            "date_of_birth": "1990-01-01", "gender": "F",
            "address": "x", "city": "y", "state": "z",
        }, auth=auth)
        assert response.status_code == 403, response.content
        assert Patient.objects.count() == 1

    # --- vitals -----------------------------------------------------------

    def test_vitals_compute_bmi_and_default_recorder(self):
        response = self.post("/patients/api/vitals/", {
            "patient": self.patient.id,
            "temperature": "36.8",
            "blood_pressure_systolic": 120,
            "blood_pressure_diastolic": 80,
            "pulse_rate": 72,
            "height": "170.00",
            "weight": "70.00",
        })
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["blood_pressure"] == "120/80"
        assert Decimal(body["bmi"]) == Decimal("24.22"), body["bmi"]
        assert body["recorded_by"], "recorded_by should default to the user"

    def test_vitals_filtered_by_patient(self):
        other = Patient.objects.create(
            first_name="Zara", last_name="Musa", date_of_birth="1999-09-09",
            gender="F", address="3 Yola Road", city="Yola", state="Adamawa",
        )
        Vitals.objects.create(patient=self.patient, pulse_rate=70, recorded_by="n")
        Vitals.objects.create(patient=other, pulse_rate=80, recorded_by="n")

        rows = self.get(f"/patients/api/vitals/?patient={self.patient.id}").json()
        assert rows["count"] == 1
        assert rows["results"][0]["pulse_rate"] == 70

    # --- medical history --------------------------------------------------

    def test_medical_history_defaults_doctor_name(self):
        response = self.post("/patients/api/medical-history/", {
            "patient": self.patient.id,
            "diagnosis": "Malaria",
            "treatment": "ACT course",
            "date": "2026-08-15T09:00:00Z",
        })
        assert response.status_code == 201, response.content
        assert response.json()["doctor_name"]

    # --- wallet -----------------------------------------------------------

    def test_wallet_reports_balance_and_outstanding(self):
        body = self.get(f"/patients/api/patients/{self.patient.id}/wallet/").json()
        assert Decimal(body["wallet"]["balance"]) == Decimal("0.00")
        assert Decimal(body["outstanding"]["total"]) == Decimal("0.00")

    def test_funding_credits_wallet_and_records_transaction(self):
        response = self.post(
            f"/patients/api/patients/{self.patient.id}/fund/",
            {"amount": "5000.00", "payment_method": "cash"},
        )
        assert response.status_code == 200, response.content
        body = response.json()
        assert Decimal(body["wallet"]["balance"]) == Decimal("5000.00")
        assert body["transaction"]["transaction_type"] == "deposit"
        assert "cash" in body["transaction"]["description"]

        wallet = PatientWallet.objects.get(patient=self.patient)
        assert wallet.balance == Decimal("5000.00")

        rows = self.get(
            f"/patients/api/patients/{self.patient.id}/transactions/"
        ).json()
        assert rows["count"] == 1
        assert Decimal(rows["results"][0]["balance_after"]) == Decimal("5000.00")

    def test_funding_rejects_bad_amounts(self):
        for amount in ("0", "-100", "abc", None):
            response = self.post(
                f"/patients/api/patients/{self.patient.id}/fund/",
                {"amount": amount},
            )
            assert response.status_code == 400, (amount, response.content)
        assert not PatientWallet.objects.filter(
            patient=self.patient, balance__gt=0
        ).exists()

    def test_funding_needs_its_own_permission(self):
        # change_patient is not enough: moving money is a separate right.
        _, auth = self.staff_user(
            "08011000004", "editnurse", "view_patient", "change_patient",
        )
        response = self.post(
            f"/patients/api/patients/{self.patient.id}/fund/",
            {"amount": "100.00"}, auth=auth,
        )
        assert response.status_code == 403, response.content

        _, auth = self.staff_user(
            "08011000005", "cashier", "view_patient", "add_wallettransaction",
        )
        response = self.post(
            f"/patients/api/patients/{self.patient.id}/fund/",
            {"amount": "100.00"}, auth=auth,
        )
        assert response.status_code == 200, response.content
