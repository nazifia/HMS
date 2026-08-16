"""Theatre over the mobile API: the day's list, booking, team, checklist, notes.

The guards are shared with the surgery form and its view via theatre.services:
a theatre cannot be double-booked, an NHIA surgery cannot start without an
authorization code, and a post-operative note cannot be written for a surgery
that has not happened.
"""
from datetime import timedelta
from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import CustomUser
from nhia.models import AuthorizationCode, NHIAPatient
from patients.models import Patient
from theatre.models import (
    OperationTheatre, PostOperativeNote, Surgery, SurgeryType,
    SurgicalEquipment, SurgicalTeam,
)


@override_settings(STRICT_ACCESS_CONTROL=True)
class TheatreApiTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            phone_number="08016000001", username="theatreadmin", password="pw12345",
        )
        self.auth = self.token_for("08016000001", "pw12345")

        self.patient = Patient.objects.create(
            first_name="Uche", last_name="Okafor", date_of_birth="1979-09-09",
            gender="M", address="5 Theatre Road", city="Aba", state="Abia",
        )
        self.theatre = OperationTheatre.objects.create(
            name="Main Theatre", theatre_number="T1", floor="2",
        )
        self.other_theatre = OperationTheatre.objects.create(
            name="Day Theatre", theatre_number="T2", floor="2",
        )
        self.surgery_type = SurgeryType.objects.create(
            name="Appendectomy",
            average_duration=timedelta(hours=2),
            preparation_time=timedelta(minutes=30),
            recovery_time=timedelta(hours=4),
            fee=Decimal("150000.00"),
        )
        self.equipment = SurgicalEquipment.objects.create(
            name="Laparoscope", equipment_type="instrument", quantity_available=2,
        )
        self.slot = timezone.now() + timedelta(days=1)

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

    def book(self, when=None, theatre=None, patient=None, duration="02:00:00"):
        return self.post("/theatre/api/surgeries/", {
            "patient": (patient or self.patient).id,
            "surgery_type": self.surgery_type.id,
            "theatre": (theatre or self.theatre).id,
            "scheduled_date": (when or self.slot).isoformat(),
            "expected_duration": duration,
        })

    def nhia_patient(self):
        number = NHIAPatient.objects.count() + 1
        patient = Patient.objects.create(
            first_name="Amaka", last_name=f"Nnaji{number}",
            date_of_birth="1990-10-10", gender="F", address="6 Scheme Road",
            city="Aba", state="Abia", patient_type="nhia",
        )
        NHIAPatient.objects.create(
            patient=patient, nhia_reg_number=f"NHIA-700{number}",
        )
        return patient

    # --- catalogue and board ---------------------------------------------

    def test_surgery_type_carries_its_fee_and_duration(self):
        rows = self.get("/theatre/api/surgery-types/").json()["results"]
        row = [r for r in rows if r["id"] == self.surgery_type.id][0]
        assert Decimal(row["fee"]) == Decimal("150000.00")
        assert row["average_duration"] == "02:00:00"
        assert row["risk_level_display"] == "Medium Risk"

    def test_theatre_day_lists_what_is_booked(self):
        assert self.book().status_code == 201
        date = self.slot.astimezone(timezone.get_current_timezone()).date()
        body = self.get(f"/theatre/api/theatres/today/?date={date}").json()
        assert body["count"] == 1
        assert body["results"][0]["theatre_name"] == "Main Theatre"

    # --- booking ----------------------------------------------------------

    def test_booking_raises_the_invoice_and_records_the_surgeon(self):
        response = self.book()
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["surgeon_name"], "surgeon should default to the caller"
        assert body["status"] == "scheduled"
        assert body["invoice"]

        from billing.models import Invoice

        invoice = Invoice.objects.get(id=body["invoice"])
        assert invoice.total_amount == Decimal("150000.00")
        assert invoice.source_app == "theatre"

    def test_double_booking_a_theatre_refused(self):
        assert self.book().status_code == 201
        response = self.book(when=self.slot + timedelta(minutes=30))
        assert response.status_code == 400, response.content
        assert "Scheduling conflict" in response.json()["error"]
        assert Surgery.objects.count() == 1

    def test_same_slot_in_another_theatre_is_fine(self):
        assert self.book().status_code == 201
        response = self.book(theatre=self.other_theatre)
        assert response.status_code == 201, response.content
        assert Surgery.objects.count() == 2

    def test_check_slot_answers_before_the_form_is_submitted(self):
        from urllib.parse import quote

        assert self.book().status_code == 201
        when = quote((self.slot + timedelta(minutes=30)).isoformat())
        body = self.get(
            f"/theatre/api/surgeries/check-slot/?theatre={self.theatre.id}"
            f"&scheduled_date={when}&expected_duration=01:00:00"
        ).json()
        assert body["free"] is False, body
        assert body["conflicts"]

        body = self.get(
            f"/theatre/api/surgeries/check-slot/?theatre={self.other_theatre.id}"
            f"&scheduled_date={quote(self.slot.isoformat())}"
            f"&expected_duration=01:00:00"
        ).json()
        assert body["free"] is True, body

    def test_nhia_surgery_waits_for_authorization(self):
        patient = self.nhia_patient()
        response = self.book(patient=patient)
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["status"] == "pending"
        assert body["requires_authorization"] is True
        assert body["can_perform"] is False
        assert "authorization" in body["blocked_reason"].lower()

        # NHIA surgery is covered: the patient is billed nothing.
        from billing.models import Invoice

        assert Invoice.objects.get(id=body["invoice"]).total_amount == Decimal("0.00")

    def test_nhia_surgery_with_a_code_is_scheduled(self):
        patient = self.nhia_patient()
        code = AuthorizationCode.objects.create(
            code="AUTH-THEATRE-1", patient=patient, service_type="theatre",
            amount=Decimal("150000.00"),
            expiry_date=timezone.now().date() + timedelta(days=30),
            status="active",
        )
        response = self.post("/theatre/api/surgeries/", {
            "patient": patient.id,
            "surgery_type": self.surgery_type.id,
            "theatre": self.theatre.id,
            "scheduled_date": self.slot.isoformat(),
            "expected_duration": "02:00:00",
            "authorization_code": code.id,
        })
        assert response.status_code == 201, response.content
        assert response.json()["status"] == "scheduled"
        code.refresh_from_db()
        assert code.status == "used"

    def test_code_for_another_patient_refused(self):
        patient = self.nhia_patient()
        other = self.nhia_patient()
        code = AuthorizationCode.objects.create(
            code="AUTH-THEATRE-2", patient=other, service_type="theatre",
            amount=Decimal("1000.00"),
            expiry_date=timezone.now().date() + timedelta(days=30),
            status="active",
        )
        response = self.post("/theatre/api/surgeries/", {
            "patient": patient.id,
            "surgery_type": self.surgery_type.id,
            "theatre": self.theatre.id,
            "scheduled_date": self.slot.isoformat(),
            "expected_duration": "02:00:00",
            "authorization_code": code.id,
        })
        assert response.status_code == 400
        assert "not for this patient" in response.json()["error"]
        assert not Surgery.objects.exists()

    # --- status -----------------------------------------------------------

    def test_unauthorized_nhia_surgery_cannot_start(self):
        patient = self.nhia_patient()
        surgery_id = self.book(patient=patient).json()["id"]
        response = self.post(
            f"/theatre/api/surgeries/{surgery_id}/set-status/",
            {"status": "in_progress"},
        )
        assert response.status_code == 400
        assert "authorization" in response.json()["error"].lower()

    def test_completed_surgery_cannot_be_reopened(self):
        surgery_id = self.book().json()["id"]
        path = f"/theatre/api/surgeries/{surgery_id}/set-status/"
        assert self.post(path, {"status": "in_progress"}).status_code == 200
        assert self.post(path, {"status": "completed"}).status_code == 200

        response = self.post(path, {"status": "in_progress"})
        assert response.status_code == 400
        assert "already completed" in response.json()["error"]

    # --- team -------------------------------------------------------------

    def test_team_member_added_once_per_role(self):
        surgery_id = self.book().json()["id"]
        nurse = CustomUser.objects.create_user(
            phone_number="08016000002", username="scrubnurse", password="pw12345",
        )
        response = self.post(f"/theatre/api/surgeries/{surgery_id}/team/", {
            "staff": nurse.id, "role": "nurse",
        })
        assert response.status_code == 201, response.content
        assert response.json()["role_display"] == "Nurse"

        response = self.post(f"/theatre/api/surgeries/{surgery_id}/team/", {
            "staff": nurse.id, "role": "nurse",
        })
        assert response.status_code == 400
        assert "already on this team" in response.json()["error"]
        assert SurgicalTeam.objects.filter(surgery_id=surgery_id).count() == 1

    def test_invalid_team_role_refused(self):
        surgery_id = self.book().json()["id"]
        response = self.post(f"/theatre/api/surgeries/{surgery_id}/team/", {
            "staff": self.user.id, "role": "chef",
        })
        assert response.status_code == 400
        assert response.json()["error"] == "Invalid team role."

    # --- checklist --------------------------------------------------------

    def test_checklist_says_what_is_still_outstanding(self):
        surgery_id = self.book().json()["id"]
        response = self.post(f"/theatre/api/surgeries/{surgery_id}/checklist/", {
            "patient_identified": True,
            "site_marked": True,
            "consent_confirmed": True,
            "notes": "Awaiting blood products",
        })
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["is_complete"] is False
        assert "blood_products_available" in body["outstanding"]
        assert body["completed_by_name"]

        # Ticking the rest completes it, and the surgery says so.
        response = self.post(f"/theatre/api/surgeries/{surgery_id}/checklist/", {
            name: True for name in body["outstanding"]
        })
        assert response.json()["is_complete"] is True
        surgery = self.get(f"/theatre/api/surgeries/{surgery_id}/").json()
        assert surgery["checklist_complete"] is True

    def test_checklist_closed_once_the_surgery_is_done(self):
        surgery_id = self.book().json()["id"]
        path = f"/theatre/api/surgeries/{surgery_id}/set-status/"
        self.post(path, {"status": "in_progress"})
        self.post(path, {"status": "completed"})

        response = self.post(
            f"/theatre/api/surgeries/{surgery_id}/checklist/",
            {"patient_identified": True},
        )
        assert response.status_code == 400
        assert "checklist is closed" in response.json()["error"]

    # --- post-op ----------------------------------------------------------

    def test_post_op_note_refused_before_the_surgery_happens(self):
        surgery_id = self.book().json()["id"]
        response = self.post(
            f"/theatre/api/surgeries/{surgery_id}/post-op-note/",
            {"notes": "Uneventful."},
        )
        assert response.status_code == 400
        assert "has not started" in response.json()["error"]
        assert not PostOperativeNote.objects.exists()

    def test_post_op_note_recorded_after_the_surgery(self):
        surgery_id = self.book().json()["id"]
        self.post(
            f"/theatre/api/surgeries/{surgery_id}/set-status/",
            {"status": "in_progress"},
        )
        response = self.post(
            f"/theatre/api/surgeries/{surgery_id}/post-op-note/",
            {
                "notes": "Appendix removed, no spillage.",
                "complications": "None",
                "follow_up_instructions": "Review in one week",
            },
        )
        assert response.status_code == 201, response.content
        assert response.json()["created_by_name"]

        rows = self.get(
            f"/theatre/api/surgeries/{surgery_id}/post-op-notes/"
        ).json()
        assert len(rows) == 1

    # --- equipment --------------------------------------------------------

    def test_equipment_usage_capped_by_what_the_theatre_holds(self):
        surgery_id = self.book().json()["id"]
        response = self.post(f"/theatre/api/surgeries/{surgery_id}/equipment/", {
            "equipment": self.equipment.id, "quantity_used": 5,
        })
        assert response.status_code == 400
        assert "Only 2 of Laparoscope available" in response.json()["error"]

        response = self.post(f"/theatre/api/surgeries/{surgery_id}/equipment/", {
            "equipment": self.equipment.id, "quantity_used": 2,
            "notes": "Both scopes used",
        })
        assert response.status_code == 201, response.content
        assert response.json()["equipment_name"] == "Laparoscope"

    def test_surgery_detail_carries_its_pack_orders(self):
        """Packs are already native under pharmacy; theatre links, not copies."""
        from pharmacy.models import MedicalPack, PackOrder

        surgery = Surgery.objects.get(id=self.book().json()["id"])
        pack = MedicalPack.objects.create(
            name="Appendectomy Pack", pack_type="surgery",
            surgery_type="appendectomy",
        )
        PackOrder.objects.create(
            pack=pack, patient=self.patient, surgery=surgery,
            ordered_by=self.user,
        )

        body = self.get(f"/theatre/api/surgeries/{surgery.id}/").json()
        assert [p["pack_name"] for p in body["pack_orders"]] == ["Appendectomy Pack"]
