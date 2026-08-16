"""Booking rules shared by the appointment form, the slot endpoint and the API.

Double-booking, doctor leave, shift hours and the NHIA authorization rule all
have to hold whichever door a booking comes through, so they live here rather
than inside the form.
"""
from datetime import datetime, timedelta

from django.utils import timezone

from .models import Appointment, DoctorLeave, DoctorSchedule, SLOT_MINUTES


class BookingError(Exception):
    """A booking that the schedule will not allow."""


def _busy_ranges(doctor, date, exclude_appointment_id=None):
    """Live bookings for a doctor on a date, as (start, end) naive datetimes."""
    existing = Appointment.objects.filter(
        doctor=doctor,
        appointment_date__date=date,
        status__in=["scheduled", "confirmed"],
    ).only("appointment_date", "end_time")
    if exclude_appointment_id:
        existing = existing.exclude(id=exclude_appointment_id)

    ranges = []
    for appointment in existing:
        start = datetime.combine(date, appointment.appointment_time)
        end = (
            datetime.combine(date, appointment.end_time)
            if appointment.end_time
            else start + timedelta(minutes=SLOT_MINUTES)
        )
        ranges.append((start, end))
    return ranges


def doctor_shift(doctor, date):
    """The doctor's working hours for that weekday, or (None, reason)."""
    on_leave = DoctorLeave.objects.filter(
        doctor=doctor,
        start_date__date__lte=date,
        end_date__date__gte=date,
        is_approved=True,
    ).exists()
    if on_leave:
        return None, f"{doctor.get_full_name()} is on leave on this date."

    schedule = DoctorSchedule.objects.filter(
        doctor=doctor, weekday=date.weekday(), is_available=True
    ).first()
    if schedule:
        return schedule, ""

    # No schedule at all is a setup problem, not a busy day — say which.
    if DoctorSchedule.objects.filter(doctor=doctor).exists():
        return None, (
            f"{doctor.get_full_name()} does not work on "
            f"{date.strftime('%A')}s."
        )
    return None, (
        f"{doctor.get_full_name()} has no working hours set up yet. "
        f"Add a schedule under Appointments > Doctor Schedules first."
    )


def available_slots(doctor, date, exclude_appointment_id=None):
    """Bookable slots for a doctor on a date. Returns (slots, message)."""
    schedule, message = doctor_shift(doctor, date)
    if schedule is None:
        return [], message

    busy = _busy_ranges(doctor, date, exclude_appointment_id)

    # Don't offer slots that have already started today.
    now = timezone.localtime()
    earliest = now.replace(tzinfo=None) if date == now.date() else None

    slots = []
    shift_end = datetime.combine(date, schedule.end_time)
    slot_start = datetime.combine(date, schedule.start_time)
    while slot_start < shift_end:
        slot_end = slot_start + timedelta(minutes=SLOT_MINUTES)
        taken = any(
            slot_start < busy_end and slot_end > busy_start
            for busy_start, busy_end in busy
        )
        if slot_end <= shift_end and not taken and (
            earliest is None or slot_start >= earliest
        ):
            slots.append({
                "value": slot_start.strftime("%H:%M"),
                "text": slot_start.strftime("%I:%M %p"),
            })
        slot_start = slot_end
    return slots, ""


def check_doctor_availability(
    doctor, date, start_time, end_time=None, exclude_appointment_id=None
):
    """Raise BookingError unless the doctor is free for that slot.

    Covers leave, the day's shift hours, and overlap with live bookings.
    """
    schedule, message = doctor_shift(doctor, date)
    if schedule is None:
        raise BookingError(message)

    slot_end = end_time or (
        datetime.combine(date, start_time) + timedelta(minutes=SLOT_MINUTES)
    ).time()

    if (
        start_time < schedule.start_time
        or start_time >= schedule.end_time
        or slot_end > schedule.end_time
    ):
        raise BookingError(
            f"{doctor.get_full_name()} is only available from "
            f"{schedule.start_time.strftime('%I:%M %p')} to "
            f"{schedule.end_time.strftime('%I:%M %p')} on this day."
        )

    start = datetime.combine(date, start_time)
    end = datetime.combine(date, slot_end)
    for busy_start, busy_end in _busy_ranges(doctor, date, exclude_appointment_id):
        # A overlaps B if A.start < B.end and A.end > B.start.
        if start < busy_end and end > busy_start:
            raise BookingError(
                f"This appointment overlaps with an existing appointment for "
                f"{doctor.get_full_name()} at "
                f"{busy_start.strftime('%I:%M %p')}."
            )


def update_status(appointment, new_status):
    """Move an appointment's status, refusing the transitions that are wrong."""
    if new_status not in dict(Appointment.STATUS_CHOICES):
        raise BookingError("Invalid status")

    # Completed/cancelled are terminal: reopening one would silently free the slot.
    if appointment.status in ("completed", "cancelled") and (
        new_status != appointment.status
    ):
        raise BookingError(
            f"Cannot change a {appointment.get_status_display().lower()} "
            f"appointment."
        )

    # Confirming or completing requires the consultation fee settled first.
    if new_status in ("confirmed", "completed") and (
        not appointment.consultation_payment_verified()
    ):
        raise BookingError(
            "Consultation fee has not been paid. The patient must pay before "
            "the appointment can be confirmed or completed."
        )

    appointment.status = new_status
    appointment.save()
    return appointment


def resolve_authorization_code(patient, code_text, existing=None):
    """NHIA patients must present a valid desk-office code to book.

    Returns the AuthorizationCode to attach (None for non-NHIA patients).
    """
    nhia_info = getattr(patient, "nhia_info", None)
    if not (nhia_info and nhia_info.is_active):
        return None

    code_text = (code_text or "").strip()
    if not code_text:
        if existing:
            # Editing without retyping keeps the code already attached.
            return existing
        raise BookingError(
            "This is an NHIA patient. An authorization code from the desk "
            "office is required to book an appointment."
        )

    from nhia.models import AuthorizationCode

    code = AuthorizationCode.objects.filter(code=code_text, patient=patient).first()
    if code is None:
        raise BookingError("Invalid authorization code for this patient.")
    if not code.is_valid() and code != existing:
        raise BookingError(
            f"This authorization code is "
            f"{code.get_status_display().lower()} and can no longer be used."
        )
    if code.service_type not in ("appointment", "general"):
        raise BookingError(
            f"This code is for {code.get_service_type_display()} services, "
            f"not appointments."
        )
    return code
