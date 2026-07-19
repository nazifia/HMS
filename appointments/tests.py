from datetime import date, datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from patients.models import Patient

from .forms import AppointmentForm, DoctorLeaveForm, DoctorScheduleForm
from .models import Appointment, AppointmentFollowUp, DoctorLeave, DoctorSchedule


class AppointmentBookingTests(TestCase):
    """Covers the booking rules in AppointmentForm.clean()."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = CustomUser.objects.create_user(
            phone_number="08000000001", username="doc", password="x",
            first_name="Ada", last_name="Doc",
        )
        profile = cls.doctor.profile
        profile.role = "doctor"
        profile.specialization = "General"
        profile.save()
        cls.patient = Patient.objects.create(
            first_name="Test", last_name="Patient", date_of_birth=date(1990, 1, 1),
            gender="F", address="1 Test St", city="Lagos", state="Lagos",
        )
        # Next Monday, so the test never lands on "today" (past-time rule).
        today = timezone.localdate()
        cls.day = today + timedelta(days=(7 - today.weekday()) or 7)
        DoctorSchedule.objects.create(
            doctor=cls.doctor,
            weekday=cls.day.weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

    def form(self, start, end=None):
        return AppointmentForm(data={
            "patient": self.patient.pk,
            "doctor": self.doctor.pk,
            "appointment_date": self.day.isoformat(),
            "appointment_time": start,
            "end_time": end or "",
            "reason": "checkup",
            "status": "scheduled",
            "priority": "normal",
        })

    def test_valid_slot_is_accepted(self):
        self.assertTrue(self.form("10:00").is_valid())

    def test_past_date_rejected(self):
        form = self.form("10:00")
        form.data = form.data.copy()
        form.data["appointment_date"] = (timezone.localdate() - timedelta(days=1)).isoformat()
        self.assertFalse(form.is_valid())

    def test_slot_must_finish_within_shift(self):
        # Starts inside the shift but runs past 17:00.
        self.assertFalse(self.form("16:45").is_valid())
        self.assertFalse(self.form("17:00").is_valid())

    def test_overlapping_appointment_rejected(self):
        self.assertTrue(self.form("10:00").is_valid())
        self.form("10:00").save()
        self.assertFalse(self.form("10:15").is_valid())  # overlaps the 10:00-10:30 slot
        self.assertTrue(self.form("10:30").is_valid())   # starts exactly when it ends

    def test_mid_day_leave_blocks_whole_day(self):
        DoctorLeave.objects.create(
            doctor=self.doctor,
            start_date=timezone.make_aware(
                datetime.combine(self.day, time(13, 0))
            ),
            end_date=timezone.make_aware(
                datetime.combine(self.day, time(17, 0))
            ),
            reason="conference",
            is_approved=True,
        )
        self.assertFalse(self.form("10:00").is_valid())

    def test_save_combines_date_and_time(self):
        appt = self.form("10:00").save()
        local = timezone.localtime(appt.appointment_date)
        self.assertEqual(local.date(), self.day)
        self.assertEqual(local.hour, 10)
        self.assertEqual(appt.appointment_time, time(10, 0))

    def test_edit_form_prefills_date_and_time_from_datetime(self):
        appt = self.form("10:00").save()
        initial = AppointmentForm(instance=appt).initial
        self.assertEqual(initial["appointment_date"], self.day)
        self.assertEqual(initial["appointment_time"], time(10, 0))

    def test_appointment_time_property_tracks_the_datetime(self):
        appt = self.form("10:00").save()
        self.assertEqual(appt.appointment_time, time(10, 0))
        appt.refresh_from_db()
        self.assertEqual(appt.appointment_time, time(10, 0))
        # Property is derived, so it follows a change to the stored datetime.
        appt.appointment_date = timezone.make_aware(datetime.combine(self.day, time(14, 30)))
        self.assertEqual(appt.appointment_time, time(14, 30))

    def test_pages_render_the_time_from_the_property(self):
        """Templates still read appointment.appointment_time after the column drop."""
        appt = self.form("10:00").save()
        admin = CustomUser.objects.create_superuser(
            phone_number="08000000002", username="root", password="pw",
        )
        self.client.force_login(admin)
        for url in (
            reverse("appointments:detail", args=[appt.pk]),
            reverse("appointments:list"),
            f"{reverse('appointments:calendar')}?month={self.day.month}&year={self.day.year}",
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "10:00 AM")

    def test_patient_labels_include_patient_id(self):
        form = AppointmentForm()
        label = form.fields["patient"].label_from_instance(self.patient)
        self.assertIn(self.patient.patient_id, label)

    def slots(self, **extra):
        admin = CustomUser.objects.filter(username="root2").first() or (
            CustomUser.objects.create_superuser(
                phone_number="08000000003", username="root2", password="pw",
            )
        )
        self.client.force_login(admin)
        params = {"doctor_id": self.doctor.pk, "date": self.day.isoformat(), **extra}
        response = self.client.get(reverse("appointments:get_available_slots"), params)
        return [s["value"] for s in response.json()["available_slots"]]

    def test_booked_slot_is_not_offered_but_is_on_reschedule(self):
        appt = self.form("10:00").save()
        self.assertNotIn("10:00", self.slots())
        self.assertIn("09:30", self.slots())  # neighbouring slot stays free
        # Rescheduling that same appointment must not see itself as a conflict.
        self.assertIn("10:00", self.slots(appointment_id=appt.pk))

    def test_doctor_pickers_only_list_doctors(self):
        for form in (DoctorScheduleForm(), DoctorLeaveForm()):
            with self.subTest(form=type(form).__name__):
                self.assertEqual(
                    list(form.fields["doctor"].queryset), [self.doctor]
                )

    def test_booking_a_follow_up_prefills_and_links_the_new_appointment(self):
        original = self.form("10:00").save()
        original.status = "completed"
        original.save()
        follow_up = AppointmentFollowUp.objects.create(
            appointment=original, follow_up_date=self.day, notes="review results",
        )
        admin = CustomUser.objects.create_superuser(
            phone_number="08000000004", username="root3", password="pw",
        )
        self.client.force_login(admin)
        url = f"{reverse('appointments:create')}?follow_up_id={follow_up.pk}"

        # GET prefills patient, doctor and date from the original appointment.
        response = self.client.get(url)
        form = response.context["form"]
        self.assertEqual(form.initial["doctor"], self.doctor)
        self.assertEqual(form.initial["appointment_date"], self.day)

        # POST books it and links the follow-up to the new appointment.
        response = self.client.post(url, {
            "patient": self.patient.pk,
            "doctor": self.doctor.pk,
            "appointment_date": self.day.isoformat(),
            "appointment_time": "11:00",
            "reason": "Follow-up: checkup",
            "status": "scheduled",
            "priority": "normal",
        })
        follow_up.refresh_from_db()
        self.assertIsNotNone(follow_up.booked_appointment)
        self.assertEqual(follow_up.booked_appointment.appointment_time, time(11, 0))

        # Already-booked follow-up can't be booked again.
        response = self.client.get(url)
        self.assertNotIn("appointment_date", response.context["form"].initial)

    def test_leave_dates_are_stored_as_aware_full_day_datetimes(self):
        form = DoctorLeaveForm(data={
            "doctor": self.doctor.pk,
            "start_date": self.day.isoformat(),
            "end_date": self.day.isoformat(),
            "reason": "conference",
            "is_approved": True,
        })
        self.assertTrue(form.is_valid(), form.errors)
        leave = form.save()
        self.assertTrue(timezone.is_aware(leave.start_date))
        self.assertEqual(timezone.localtime(leave.start_date).date(), self.day)
        self.assertEqual(timezone.localtime(leave.end_date).date(), self.day)
        self.assertEqual(timezone.localtime(leave.start_date).time(), time.min)
        # The whole day must be covered, so a booking on that day is blocked.
        self.assertFalse(self.form("10:00").is_valid())
