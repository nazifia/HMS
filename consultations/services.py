"""Consultation and referral workflow shared by the views and the mobile API.

Referral routing (who may accept what) and the NHIA authorization gate are the
rules worth having in one place: accepting a referral moves a patient between
clinical areas, and an unauthorized NHIA referral must not be accepted from any
door.
"""
from accounts.permissions import is_tenant_admin
from django.utils import timezone

from core.audit_utils import log_audit_action

from .models import Consultation, Referral, WaitingList


class ConsultationActionError(Exception):
    """An action the current user is not allowed to take."""


def can_update_consultation(user, consultation):
    return (
        user == consultation.doctor
        or user.is_staff
        or is_tenant_admin(user)
    )


def update_consultation_status(consultation, user, new_status):
    if not can_update_consultation(user, consultation):
        raise ConsultationActionError(
            "You don't have permission to update this consultation."
        )
    if new_status not in dict(Consultation.STATUS_CHOICES):
        raise ConsultationActionError("Invalid status provided.")

    old_status = consultation.status
    consultation.status = new_status
    consultation.save()

    log_audit_action(
        user,
        "update",
        consultation,
        f"Updated consultation status from {old_status} to {new_status}",
    )
    return consultation


def can_update_referral(user, referral):
    return (
        is_tenant_admin(user)
        or referral.can_be_accepted_by(user)
        or referral.referring_doctor == user
        or referral.assigned_doctor == user
    )


def update_referral_status(referral, user, new_status, notes=""):
    """Move a referral along, enforcing routing and the NHIA gate."""
    if not can_update_referral(user, referral):
        raise ConsultationActionError(
            "You don't have permission to update this referral."
        )
    if new_status not in dict(Referral.STATUS_CHOICES):
        raise ConsultationActionError("Invalid status.")

    # An NHIA referral needing desk-office authorization cannot be accepted
    # until that authorization is in hand.
    if new_status == "accepted" and referral.requires_authorization:
        if referral.authorization_status not in ("authorized", "not_required"):
            raise ConsultationActionError(
                f"Cannot accept this referral. Authorization status is "
                f"'{referral.get_authorization_status_display()}'. This NHIA "
                f"patient referral requires desk office authorization before "
                f"it can be accepted."
            )

    old_status = referral.status
    referral.status = new_status

    if notes:
        stamp = (
            f"[{timezone.now().strftime('%Y-%m-%d %H:%M')} - "
            f"{user.get_full_name()}] Status changed from {old_status} to "
            f"{new_status}: {notes}"
        )
        referral.notes = f"{referral.notes}\n\n{stamp}" if referral.notes else stamp

    # Accepting a routed referral makes the accepting doctor responsible for it.
    if new_status == "accepted" and referral.referral_type in (
        "department", "specialty", "unit", "theatre", "ward"
    ):
        referral.assigned_doctor = user

    referral.save()
    _notify_referring_doctor(referral, user, new_status)
    return referral


def _notify_referring_doctor(referral, user, new_status):
    """Tell the sender what happened, unless they are the one who did it."""
    if referral.referring_doctor == user:
        return
    if not referral.can_be_accepted_by(user) and referral.assigned_doctor != user:
        return

    from core.models import InternalNotification

    InternalNotification.objects.create(
        user=referral.referring_doctor,
        message=(
            f"Referral for {referral.patient.get_full_name()} to "
            f"{referral.get_referral_destination()} has been {new_status} by "
            f"Dr. {user.get_full_name()}"
        ),
    )


def call_in_patient(entry, user):
    """Take the next patient from the waiting list into a consultation."""
    if entry.status != "waiting":
        raise ConsultationActionError(
            f"This patient is already {entry.get_status_display().lower()}."
        )

    entry.status = "in_progress"
    if user and not entry.doctor:
        entry.doctor = user
    entry.save()

    consultation = Consultation.objects.create(
        patient=entry.patient,
        doctor=user,
        consulting_room=entry.consulting_room,
        waiting_list_entry=entry,
        appointment=entry.appointment,
        chief_complaint="",
        symptoms="",
        status="in_progress",
    )
    log_audit_action(
        user, "create", consultation, "Started consultation from waiting list"
    )
    return consultation


def complete_waiting_entry(entry):
    if entry.status in ("completed", "cancelled"):
        raise ConsultationActionError(
            f"This entry is already {entry.get_status_display().lower()}."
        )
    entry.status = "completed"
    entry.save(update_fields=["status"])
    return entry


def waiting_queue(consulting_room=None, doctor=None, today_only=True):
    """The live queue, urgent first, then by check-in time."""
    queryset = (
        WaitingList.objects
        .select_related("patient", "consulting_room", "doctor")
        .filter(status__in=["waiting", "in_progress"])
    )
    if consulting_room:
        queryset = queryset.filter(consulting_room=consulting_room)
    if doctor:
        queryset = queryset.filter(doctor=doctor)
    if today_only:
        queryset = queryset.filter(check_in_time__date=timezone.localdate())
    return queryset
