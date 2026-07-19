from django.db import models
from saas.models import TenantModel
from django.utils import timezone
from patients.models import Patient
from django.conf import settings

# ponytail: fixed slot length, shared by the slot generator and the booking
# validator so they can't drift. Move to DoctorSchedule if per-doctor slots are needed.
SLOT_MINUTES = 30


class Appointment(TenantModel):
    STATUS_CHOICES = (
        ("scheduled", "Scheduled"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("no_show", "No Show"),
    )

    PRIORITY_CHOICES = (
        ("normal", "Normal"),
        ("urgent", "Urgent"),
        ("emergency", "Emergency"),
    )

    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="appointments"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_appointments",
    )
    # Full start datetime. The old separate appointment_time column was folded in
    # here (migration 0007); `appointment_time` below is now a read-only view of it.
    appointment_date = models.DateTimeField()
    end_time = models.TimeField(null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="scheduled"
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="normal"
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_appointments",
    )

    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.doctor.get_full_name()} - {self.appointment_date}"

    @property
    def appointment_time(self):
        """Local start time. Kept as a property so templates reading
        `appointment.appointment_time` still work after the column was dropped.
        Not queryable — order and filter on `appointment_date` instead."""
        return timezone.localtime(self.appointment_date).time()

    def is_past_due(self):
        return timezone.now().date() > self.appointment_date.date()

    def is_upcoming(self):
        """Check if appointment is today or in the future"""
        today = timezone.now().date()
        return self.appointment_date.date() >= today

    def is_today(self):
        """Check if appointment is today"""
        return self.appointment_date.date() == timezone.now().date()

    class Meta:
        ordering = ["appointment_date"]
        indexes = [
            models.Index(fields=["appointment_date"], name="idx_appt_date"),
            models.Index(fields=["patient"], name="idx_appt_patient"),
            models.Index(fields=["doctor"], name="idx_appt_doctor"),
            models.Index(fields=["status"], name="idx_appt_status"),
            models.Index(
                fields=["appointment_date", "status"], name="idx_appt_date_status"
            ),
        ]


class AppointmentFollowUp(TenantModel):
    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name="follow_ups"
    )
    follow_up_date = models.DateField()
    notes = models.TextField()
    # Set once the follow-up is turned into a real booking; keeps the
    # "Book Appointment" button from showing twice for the same follow-up.
    booked_appointment = models.OneToOneField(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booked_from_follow_up",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )

    def __str__(self):
        return f"Follow-up for {self.appointment} on {self.follow_up_date}"

    class Meta:
        ordering = ["follow_up_date"]


class DoctorSchedule(TenantModel):
    WEEKDAY_CHOICES = (
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    )

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_schedules",
    )
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.doctor.get_full_name()} - {self.get_weekday_display()} ({self.start_time} - {self.end_time})"

    class Meta:
        unique_together = ("doctor", "weekday")
        ordering = ["weekday", "start_time"]


class DoctorLeave(TenantModel):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_leaves"
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    reason = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.doctor.get_full_name()} - {self.start_date} to {self.end_date}"

    @property
    def duration(self):
        delta = self.end_date - self.start_date
        return delta.days + 1

    class Meta:
        ordering = ["-start_date"]
