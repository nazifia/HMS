from datetime import date, datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import CustomUser
from patients.models import Patient

from .forms import AppointmentForm
from .models import Appointment, DoctorLeave, DoctorSchedule


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

    def test_edit_form_prefills_date_from_datetime(self):
        appt = self.form("10:00").save()
        self.assertEqual(AppointmentForm(instance=appt).initial["appointment_date"], self.day)

    def test_patient_labels_include_patient_id(self):
        form = AppointmentForm()
        label = form.fields["patient"].label_from_instance(self.patient)
        self.assertIn(self.patient.patient_id, label)
