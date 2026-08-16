"""Consultations, the clinic queue and referrals over the mobile API.

The rules worth pinning: only the treating doctor (or staff) may move a
consultation, referrals may only be accepted by the area they were routed to,
and an NHIA referral awaiting desk-office authorization cannot be accepted.
"""
from django.test import Client, TestCase, override_settings

from accounts.models import CustomUser, Department, Role
from consultations.models import (
    Consultation, ConsultingRoom, Referral, SOAPNote, WaitingList,
)
from patients.models import Patient


@override_settings(STRICT_ACCESS_CONTROL=True)
class ConsultationApiTest(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            phone_number="08016000001", username="clinicadmin", password="pw12345",
        )
        self.auth = self.token_for("08016000001")

        # These departments ship with the app, so take whatever is there.
        self.medicine, _ = Department.objects.get_or_create(name="Medicine")
        self.surgery, _ = Department.objects.get_or_create(name="Surgery")
        self.room = ConsultingRoom.objects.create(
            room_number="C1", floor="1", department=self.medicine,
        )
        self.patient = Patient.objects.create(
            first_name="Femi", last_name="Ojo", date_of_birth="1987-07-07",
            gender="M", address="7 Ibadan Road", city="Ibadan", state="Oyo",
        )

    def token_for(self, phone):
        response = Client().post(
            "/api/accounts/login/",
            {"phone_number": phone, "password": "pw12345"},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        return {"HTTP_AUTHORIZATION": f"Token {response.json()['token']}"}

    def doctor(self, phone, username, department=None):
        user = CustomUser.objects.create_user(
            phone_number=phone, username=username, password="pw12345",
            first_name=username.title(), last_name="Doe",
        )
        role, _ = Role.objects.get_or_create(name="doctor")
        user.roles.add(role)
        if department:
            profile = user.profile
            profile.department = department
            profile.save()
        return user, self.token_for(phone)

    def get(self, path, auth=None):
        return self.client.get(path, **(auth or self.auth))

    def post(self, path, payload=None, auth=None):
        return self.client.post(
            path, payload or {}, content_type="application/json",
            **(auth or self.auth),
        )

    def queue_entry(self, priority="normal"):
        return WaitingList.objects.create(
            patient=self.patient, consulting_room=self.room, priority=priority,
        )

    # --- waiting list -----------------------------------------------------

    def test_queue_puts_urgent_patients_first(self):
        second = Patient.objects.create(
            first_name="Ngo", last_name="Uche", date_of_birth="1990-01-01",
            gender="F", address="8 Road", city="Enugu", state="Enugu",
        )
        self.queue_entry(priority="normal")
        WaitingList.objects.create(
            patient=second, consulting_room=self.room, priority="emergency",
        )
        rows = self.get("/consultations/api/waiting-list/").json()["results"]
        assert rows[0]["patient_name"] == "Ngo Uche", [r["priority"] for r in rows]

    def test_calling_in_starts_a_consultation(self):
        entry = self.queue_entry()
        response = self.post(f"/consultations/api/waiting-list/{entry.id}/call-in/")
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["waiting_entry"]["status"] == "in_progress"
        assert body["consultation"]["status"] == "in_progress"
        assert body["consultation"]["room_number"] == "C1"

        consultation = Consultation.objects.get(id=body["consultation"]["id"])
        assert consultation.waiting_list_entry_id == entry.id
        assert consultation.doctor == self.admin

    def test_calling_in_twice_refused(self):
        entry = self.queue_entry()
        assert self.post(
            f"/consultations/api/waiting-list/{entry.id}/call-in/"
        ).status_code == 201
        response = self.post(
            f"/consultations/api/waiting-list/{entry.id}/call-in/"
        )
        assert response.status_code == 400
        assert "already in progress" in response.json()["error"].lower()
        assert Consultation.objects.count() == 1

    # --- consultations ----------------------------------------------------

    def test_other_doctors_cannot_move_someone_elses_consultation(self):
        doctor, doctor_auth = self.doctor("08016000002", "drone", self.medicine)
        consultation = Consultation.objects.create(
            patient=self.patient, doctor=doctor, consulting_room=self.room,
            chief_complaint="Headache", symptoms="Since Monday",
        )
        stranger, stranger_auth = self.doctor(
            "08016000003", "drtwo", self.medicine
        )

        response = self.post(
            f"/consultations/api/consultations/{consultation.id}/set-status/",
            {"status": "completed"}, auth=stranger_auth,
        )
        assert response.status_code == 403, response.content
        consultation.refresh_from_db()
        assert consultation.status == "pending"

        response = self.post(
            f"/consultations/api/consultations/{consultation.id}/set-status/",
            {"status": "completed"}, auth=doctor_auth,
        )
        assert response.status_code == 200, response.content
        consultation.refresh_from_db()
        assert consultation.status == "completed"

    def test_invalid_consultation_status_refused(self):
        consultation = Consultation.objects.create(
            patient=self.patient, doctor=self.admin, chief_complaint="x",
            symptoms="y",
        )
        response = self.post(
            f"/consultations/api/consultations/{consultation.id}/set-status/",
            {"status": "teleported"},
        )
        assert response.status_code == 400
        assert "Invalid status" in response.json()["error"]

    def test_notes_are_attributed_and_listed(self):
        consultation = Consultation.objects.create(
            patient=self.patient, doctor=self.admin, chief_complaint="x",
            symptoms="y",
        )
        assert self.post(
            f"/consultations/api/consultations/{consultation.id}/notes/",
            {"note": "Patient tolerated the review well"},
        ).status_code == 201
        assert self.post(
            f"/consultations/api/consultations/{consultation.id}/notes/",
            {"note": "   "},
        ).status_code == 400

        body = self.get(
            f"/consultations/api/consultations/{consultation.id}/"
        ).json()
        assert len(body["notes_log"]) == 1
        assert body["notes_log"][0]["created_by_name"]

    # --- referrals --------------------------------------------------------

    def make_referral(self, department=None, **extra):
        return Referral.objects.create(
            patient=self.patient,
            referring_doctor=self.admin,
            referral_type="department",
            referred_to_department=department or self.surgery,
            reason="Second opinion",
            **extra,
        )

    def test_only_the_target_department_can_accept(self):
        referral = self.make_referral(department=self.surgery)
        _, outsider_auth = self.doctor("08016000004", "drmed", self.medicine)
        _, surgeon_auth = self.doctor("08016000005", "drsurg", self.surgery)

        response = self.post(
            f"/consultations/api/referrals/{referral.id}/set-status/",
            {"status": "accepted"}, auth=outsider_auth,
        )
        assert response.status_code == 403, response.content
        referral.refresh_from_db()
        assert referral.status == "pending"

        response = self.post(
            f"/consultations/api/referrals/{referral.id}/set-status/",
            {"status": "accepted", "notes": "Booking theatre"}, auth=surgeon_auth,
        )
        assert response.status_code == 200, response.content
        referral.refresh_from_db()
        assert referral.status == "accepted"
        assert referral.assigned_doctor.username == "drsurg"
        assert "Booking theatre" in referral.notes

    def test_unauthorized_nhia_referral_cannot_be_accepted(self):
        referral = self.make_referral()
        Referral.objects.filter(id=referral.id).update(
            requires_authorization=True, authorization_status="required",
        )
        _, surgeon_auth = self.doctor("08016000006", "drsurg2", self.surgery)

        response = self.post(
            f"/consultations/api/referrals/{referral.id}/set-status/",
            {"status": "accepted"}, auth=surgeon_auth,
        )
        assert response.status_code == 400, response.content
        assert "desk office authorization" in response.json()["error"]
        referral.refresh_from_db()
        assert referral.status == "pending"

    def test_referring_doctor_sees_it_as_outgoing(self):
        self.make_referral()
        assert self.get(
            "/consultations/api/referrals/?outgoing=true"
        ).json()["count"] == 1

        _, surgeon_auth = self.doctor("08016000007", "drsurg3", self.surgery)
        incoming = self.get(
            "/consultations/api/referrals/?incoming=true", auth=surgeon_auth
        ).json()
        assert incoming["count"] == 1
        assert incoming["results"][0]["can_accept"] is True

    def test_creating_a_referral_records_the_sender(self):
        response = self.post("/consultations/api/referrals/", {
            "patient": self.patient.id,
            "referral_type": "department",
            "referred_to_department": self.surgery.id,
            "reason": "Surgical review",
        })
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["status"] == "pending"
        assert body["referring_doctor_name"]
        assert body["destination"]

    # --- clerking notes ---------------------------------------------------

    def test_clerking_schema_lists_the_proforma_sections(self):
        rows = self.get("/consultations/api/clerking-notes/schema/").json()
        names = [row["name"] for row in rows]
        assert names[0] == "presenting_complaint"
        assert names[-1] == "management_plan"
        assert len(names) == 13, names
        assert all(row["label"] and row["placeholder"] for row in rows)

    def test_clerking_note_saves_partially_and_lists_filled_sections(self):
        consultation = Consultation.objects.create(
            patient=self.patient, doctor=self.admin, chief_complaint="x",
            symptoms="y",
        )
        # A review visit may only fill in part of the proforma.
        response = self.post("/consultations/api/clerking-notes/", {
            "consultation": consultation.id,
            "presenting_complaint": "Cough for 3 days",
            "management_plan": "Amoxicillin 500mg tds",
        })
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["created_by_name"]
        assert body["patient_name"] == "Femi Ojo"

        labels = [section["label"] for section in body["sections"]]
        assert labels == [
            "Presenting Complaint (PC)", "Management / Treatment Plan",
        ], labels
        assert body["review_of_systems"] == ""

    def test_clerking_note_can_be_extended_later(self):
        consultation = Consultation.objects.create(
            patient=self.patient, doctor=self.admin, chief_complaint="x",
            symptoms="y",
        )
        note_id = self.post("/consultations/api/clerking-notes/", {
            "consultation": consultation.id,
            "presenting_complaint": "Cough",
        }).json()["id"]

        response = self.client.patch(
            f"/consultations/api/clerking-notes/{note_id}/",
            {"provisional_diagnosis": "Community acquired pneumonia"},
            content_type="application/json", **self.auth,
        )
        assert response.status_code == 200, response.content
        note = SOAPNote.objects.get(id=note_id)
        assert note.presenting_complaint == "Cough", "earlier section kept"
        assert note.provisional_diagnosis == "Community acquired pneumonia"

    def test_notes_filtered_by_consultation_and_patient(self):
        first = Consultation.objects.create(
            patient=self.patient, doctor=self.admin, chief_complaint="x",
            symptoms="y",
        )
        other_patient = Patient.objects.create(
            first_name="Ada", last_name="Nwo", date_of_birth="1995-05-05",
            gender="F", address="9 Road", city="Jos", state="Plateau",
        )
        second = Consultation.objects.create(
            patient=other_patient, doctor=self.admin, chief_complaint="x",
            symptoms="y",
        )
        for consultation in (first, second):
            self.post("/consultations/api/clerking-notes/", {
                "consultation": consultation.id, "summary": "Seen",
            })

        assert self.get(
            f"/consultations/api/clerking-notes/?consultation={first.id}"
        ).json()["count"] == 1
        assert self.get(
            f"/consultations/api/clerking-notes/?patient={other_patient.id}"
        ).json()["count"] == 1
