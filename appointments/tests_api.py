"""Appointments over the mobile API.

The booking rules are shared with the form via appointments.services, so the
API must refuse exactly what the web booking screen refuses: double-booking,
hours outside the doctor's shift, leave days, and past times.
"""
from datetime import time, timedelta

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import CustomUser, Role
from appointments.models import Appointment, DoctorLeave, DoctorSchedule
from patients.models import Patient


@override_settings(STRICT_ACCESS_CONTROL=True)
class AppointmentApiTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            phone_number="08014000001", username="reception", password="pw12345",
        )
        self.doctor = CustomUser.objects.create_user(
            phone_number="08014000002", username="drallen", password="pw12345",
            first_name="Ada", last_name="Allen",
        )
        role, _ = Role.objects.get_or_create(name="doctor")
        self.doctor.roles.add(role)
        self.auth = self.token_for("08014000001", "pw12345")

        self.patient = Patient.objects.create(
            first_name="Sade", last_name="Bello", date_of_birth="1993-03-03",
            gender="F", address="6 Ikeja Road", city="Lagos", state="Lagos",
        )

        # Tomorrow, so "in the past" checks never bite mid-test.
        self.date = (timezone.localtime() + timedelta(days=1)).date()
        DoctorSchedule.objects.create(
            doctor=self.doctor, weekday=self.date.weekday(),
            start_time=time(9, 0), end_time=time(12, 0), is_available=True,
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

    def at(self, hour, minute=0):
        """An aware datetime on the test date, in ISO form."""
        naive = timezone.datetime.combine(self.date, time(hour, minute))
        return timezone.make_aware(naive).isoformat()

    def book(self, hour=9, minute=0, **extra):
        payload = {
            "patient": self.patient.id,
            "doctor": self.doctor.id,
            "appointment_date": self.at(hour, minute),
            "reason": "Review",
            **extra,
        }
        return self.post("/appointments/api/appointments/", payload)

    # --- booking ----------------------------------------------------------

    def test_booking_records_reception_and_scheduled_status(self):
        response = self.book(hour=9)
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["status"] == "scheduled"
        assert body["doctor_name"] == "Ada Allen"
        assert body["patient_number"] == self.patient.patient_id
        assert Appointment.objects.get(id=body["id"]).created_by == self.user

    def test_double_booking_refused(self):
        assert self.book(hour=10).status_code == 201
        response = self.book(hour=10)
        assert response.status_code == 400, response.content
        assert "overlaps" in response.json()["error"]
        assert Appointment.objects.count() == 1

    def test_overlapping_a_longer_appointment_refused(self):
        assert self.book(hour=9, end_time="10:00").status_code == 201
        # Starts inside the first appointment's hour.
        response = self.book(hour=9, minute=30)
        assert response.status_code == 400, response.content
        assert "overlaps" in response.json()["error"]

    def test_outside_shift_refused(self):
        response = self.book(hour=15)
        assert response.status_code == 400, response.content
        assert "only available from" in response.json()["error"]

    def test_booking_on_leave_day_refused(self):
        DoctorLeave.objects.create(
            doctor=self.doctor,
            start_date=timezone.make_aware(
                timezone.datetime.combine(self.date, time(0, 0))
            ),
            end_date=timezone.make_aware(
                timezone.datetime.combine(self.date, time(23, 59))
            ),
            reason="Conference", is_approved=True,
        )
        response = self.book(hour=9)
        assert response.status_code == 400, response.content
        assert "on leave" in response.json()["error"]

    def test_past_booking_refused(self):
        yesterday = (timezone.localtime() - timedelta(days=1)).date()
        naive = timezone.datetime.combine(yesterday, time(9, 0))
        response = self.post("/appointments/api/appointments/", {
            "patient": self.patient.id,
            "doctor": self.doctor.id,
            "appointment_date": timezone.make_aware(naive).isoformat(),
            "reason": "Late",
        })
        assert response.status_code == 400, response.content
        assert "past" in response.json()["error"]

    def test_unapproved_leave_does_not_block(self):
        DoctorLeave.objects.create(
            doctor=self.doctor,
            start_date=timezone.make_aware(
                timezone.datetime.combine(self.date, time(0, 0))
            ),
            end_date=timezone.make_aware(
                timezone.datetime.combine(self.date, time(23, 59))
            ),
            reason="Requested", is_approved=False,
        )
        assert self.book(hour=9).status_code == 201

    # --- slots ------------------------------------------------------------

    def test_slots_exclude_booked_times(self):
        self.book(hour=9)
        body = self.get(
            f"/appointments/api/appointments/slots/"
            f"?doctor={self.doctor.id}&date={self.date}"
        ).json()
        starts = [slot["value"] for slot in body["slots"]]
        assert "09:00" not in starts, starts
        assert "09:30" in starts
        assert "12:00" not in starts, "a slot must finish inside the shift"

    def test_slots_report_why_none_are_offered(self):
        other_day = self.date + timedelta(days=1)
        while other_day.weekday() == self.date.weekday():
            other_day += timedelta(days=1)
        body = self.get(
            f"/appointments/api/appointments/slots/"
            f"?doctor={self.doctor.id}&date={other_day}"
        ).json()
        assert body["slots"] == []
        assert "does not work on" in body["message"]

    def test_rescheduling_does_not_clash_with_itself(self):
        appointment_id = self.book(hour=9).json()["id"]
        body = self.get(
            f"/appointments/api/appointments/slots/"
            f"?doctor={self.doctor.id}&date={self.date}"
            f"&appointment={appointment_id}"
        ).json()
        assert "09:00" in [slot["value"] for slot in body["slots"]]

    # --- status -----------------------------------------------------------

    def test_confirming_needs_the_consultation_fee_paid(self):
        appointment_id = self.book(hour=9).json()["id"]
        response = self.post(
            f"/appointments/api/appointments/{appointment_id}/set-status/",
            {"status": "confirmed"},
        )
        assert response.status_code == 400, response.content
        assert "Consultation fee" in response.json()["error"]

    def test_cancelled_appointments_are_terminal(self):
        appointment_id = self.book(hour=9).json()["id"]
        response = self.post(
            f"/appointments/api/appointments/{appointment_id}/set-status/",
            {"status": "cancelled"},
        )
        assert response.status_code == 200, response.content
        assert response.json()["status"] == "cancelled"

        response = self.post(
            f"/appointments/api/appointments/{appointment_id}/set-status/",
            {"status": "scheduled"},
        )
        assert response.status_code == 400
        assert "Cannot change a cancelled appointment" in response.json()["error"]

    def test_cancelling_frees_the_slot(self):
        appointment_id = self.book(hour=9).json()["id"]
        self.post(
            f"/appointments/api/appointments/{appointment_id}/set-status/",
            {"status": "cancelled"},
        )
        assert self.book(hour=9).status_code == 201

    # --- listing ----------------------------------------------------------

    def test_filters_by_day_and_doctor(self):
        self.book(hour=9)
        assert self.get(
            f"/appointments/api/appointments/?date={self.date}"
        ).json()["count"] == 1
        assert self.get(
            f"/appointments/api/appointments/?doctor={self.doctor.id}"
        ).json()["count"] == 1
        assert self.get(
            "/appointments/api/appointments/?today=true"
        ).json()["count"] == 0, "the booking is tomorrow"
        assert self.get(
            "/appointments/api/appointments/?search=bello"
        ).json()["count"] == 1

    # --- leave ------------------------------------------------------------

    def test_leave_approval_blocks_new_bookings(self):
        response = self.post("/appointments/api/leaves/", {
            "doctor": self.doctor.id,
            "start_date": self.at(0),
            "end_date": self.at(23),
            "reason": "Family",
        })
        assert response.status_code == 201, response.content
        leave_id = response.json()["id"]
        assert response.json()["is_approved"] is False
        assert self.book(hour=9).status_code == 201, "unapproved leave allows booking"

        Appointment.objects.all().delete()
        assert self.post(
            f"/appointments/api/leaves/{leave_id}/approve/"
        ).status_code == 200
        response = self.book(hour=9)
        assert response.status_code == 400
        assert "on leave" in response.json()["error"]
