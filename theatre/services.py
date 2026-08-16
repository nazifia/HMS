"""Theatre workflow shared by the HTML views, the surgery form and the API.

Double-booking a theatre, the NHIA authorization rule and the surgery invoice
all have to hold whichever door a surgery is booked through, so they live here
rather than inside `SurgeryForm` and `SurgeryCreateView`.
"""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import (
    EquipmentUsage, PostOperativeNote, PreOperativeChecklist, Surgery,
    SurgicalTeam,
)


class TheatreActionError(Exception):
    """A theatre action that is not allowed right now."""


# Statuses that still hold a slot in a theatre.
LIVE_STATUSES = ("scheduled", "in_progress")

CHECKLIST_FIELDS = (
    "patient_identified", "site_marked", "anesthesia_safety_check_completed",
    "surgical_safety_checklist_completed", "consent_confirmed",
    "allergies_reviewed", "imaging_available", "blood_products_available",
    "antibiotics_administered",
)


def theatre_conflicts(theatre, scheduled_date, expected_duration,
                      exclude_surgery_id=None):
    """Surgeries already holding this theatre over the same window.

    Returns a list of human-readable clashes — empty means the slot is free.
    """
    if not (theatre and scheduled_date and expected_duration):
        return []

    end_time = scheduled_date + expected_duration
    overlapping = Surgery.objects.filter(
        theatre=theatre,
        status__in=LIVE_STATUSES,
        scheduled_date__lt=end_time,
    ).select_related("surgery_type", "patient")
    if exclude_surgery_id:
        overlapping = overlapping.exclude(pk=exclude_surgery_id)

    conflicts = []
    for surgery in overlapping:
        surgery_end = surgery.scheduled_date + surgery.expected_duration
        if surgery_end > scheduled_date:
            conflicts.append(
                f"{surgery.surgery_type.name} for {surgery.patient} "
                f"({surgery.scheduled_date.strftime('%Y-%m-%d %H:%M')} - "
                f"{surgery_end.strftime('%H:%M')})"
            )
    return conflicts


def assert_theatre_free(theatre, scheduled_date, expected_duration,
                        exclude_surgery_id=None):
    """Raise unless the theatre is free for that window."""
    conflicts = theatre_conflicts(
        theatre, scheduled_date, expected_duration, exclude_surgery_id
    )
    if conflicts:
        raise TheatreActionError(
            "Scheduling conflict: " + "; ".join(conflicts)
        )


def resolve_authorization_code(patient, code):
    """Validate an NHIA authorization code offered for a surgery."""
    if code is None:
        return None
    if not code.is_valid():
        raise TheatreActionError("The provided authorization code is not valid.")
    if code.patient_id != patient.id:
        raise TheatreActionError(
            "The provided authorization code is not for this patient."
        )
    return code


def finalize_scheduling(surgery, user, authorization_code=None,
                        source_referral=None, status=None):
    """Save a surgery, raise its invoice and settle its authorization.

    Takes an unsaved (or saved) Surgery so the HTML view can keep using its
    formsets. Returns (surgery, invoice).
    """
    from billing.models import Invoice, InvoiceItem, Service, ServiceCategory

    authorization_code = resolve_authorization_code(
        surgery.patient, authorization_code
    )

    is_nhia = surgery.patient.patient_type == "nhia"
    surgery_fee = Decimal(str(surgery.surgery_type.fee))
    # NHIA surgeries are covered by the authorization; the patient pays nothing.
    patient_payable_fee = Decimal("0.00") if is_nhia else surgery_fee
    description = (
        f"Theatre Procedure: {surgery.surgery_type.name}"
        f"{' (NHIA Covered)' if is_nhia else ''}"
    )

    with transaction.atomic():
        surgery.authorization_code = authorization_code
        # An NHIA surgery is 'pending' until a code is supplied; regular
        # patients never need one, so honour the status asked for.
        if is_nhia:
            surgery.status = "scheduled" if authorization_code else "pending"
        else:
            surgery.status = status or surgery.status or "scheduled"

        if source_referral is not None:
            surgery.source_referral = source_referral

        surgery.save()

        invoice = Invoice(
            patient=surgery.patient,
            invoice_date=surgery.scheduled_date,
            due_date=surgery.scheduled_date.date() + timedelta(days=7),
            status="pending",
            subtotal=patient_payable_fee,
            tax_amount=Decimal("0.00"),
            total_amount=patient_payable_fee,
            amount_paid=Decimal("0.00"),
            created_by=user,
            source_app="theatre",
        )
        if patient_payable_fee == Decimal("0.00"):
            invoice._auto_pay_zero_amount = True
        invoice.save()

        category, _ = ServiceCategory.objects.get_or_create(name="Theatre Services")
        service, _ = Service.objects.get_or_create(
            name=f"Theatre Procedure: {surgery.surgery_type.name}",
            category=category,
            defaults={
                "price": surgery_fee,
                "description": f"Theatre procedure: {surgery.surgery_type.name}",
            },
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            service=service,
            description=description,
            quantity=1,
            unit_price=patient_payable_fee,
            tax_percentage=service.tax_percentage,
            tax_amount=Decimal("0.00"),
            total_amount=patient_payable_fee,
        )

        surgery.invoice = invoice
        surgery.save(update_fields=["invoice", "updated_at"])

        if authorization_code:
            authorization_code.mark_as_used(f"Surgery #{surgery.id}")

    return surgery, invoice


def schedule_surgery(patient, surgery_type, theatre, scheduled_date,
                     expected_duration, user, primary_surgeon=None,
                     anesthetist=None, pre_surgery_notes="",
                     authorization_code=None, source_referral=None,
                     status="scheduled"):
    """Book a theatre slot: refuses a double-booking, then raises the invoice."""
    assert_theatre_free(theatre, scheduled_date, expected_duration)

    surgery = Surgery(
        patient=patient,
        surgery_type=surgery_type,
        theatre=theatre,
        scheduled_date=scheduled_date,
        expected_duration=expected_duration,
        primary_surgeon=primary_surgeon,
        anesthetist=anesthetist,
        pre_surgery_notes=pre_surgery_notes,
        status=status,
    )
    return finalize_scheduling(
        surgery, user,
        authorization_code=authorization_code,
        source_referral=source_referral,
        status=status,
    )


def update_status(surgery, new_status):
    """Move a surgery along, refusing what the theatre would not allow."""
    if new_status not in dict(Surgery.STATUS_CHOICES):
        raise TheatreActionError("Invalid status.")

    # Starting or completing needs authorization settled first.
    if new_status in ("in_progress", "completed"):
        can_perform, message = surgery.can_be_performed()
        if not can_perform:
            raise TheatreActionError(message)

    if surgery.status in ("completed", "cancelled") and new_status != surgery.status:
        raise TheatreActionError(
            f"This surgery is already {surgery.status} and cannot be changed."
        )

    surgery.status = new_status
    surgery.save()
    return surgery


def assign_team_member(surgery, staff, role, usage_notes=""):
    """Put one person on a surgery's team, once per role."""
    if role not in dict(SurgicalTeam.ROLE_CHOICES):
        raise TheatreActionError("Invalid team role.")
    if SurgicalTeam.objects.filter(surgery=surgery, staff=staff, role=role).exists():
        raise TheatreActionError(
            f"{staff.get_full_name()} is already on this team as "
            f"{dict(SurgicalTeam.ROLE_CHOICES)[role].lower()}."
        )
    return SurgicalTeam.objects.create(
        surgery=surgery, staff=staff, role=role, usage_notes=usage_notes,
    )


def save_checklist(surgery, user, fields):
    """Record the pre-operative checklist. One per surgery, editable until done."""
    if surgery.status in ("completed", "cancelled"):
        raise TheatreActionError(
            f"This surgery is already {surgery.status}; its checklist is closed."
        )

    checklist, _ = PreOperativeChecklist.objects.get_or_create(
        surgery=surgery, defaults={"completed_by": user},
    )
    for name in CHECKLIST_FIELDS:
        if name in fields:
            setattr(checklist, name, bool(fields[name]))
    if "notes" in fields:
        checklist.notes = fields["notes"]
    checklist.completed_by = user
    checklist.save()
    return checklist


def checklist_is_complete(checklist):
    """Every safety item ticked. What the theatre asks before starting."""
    if checklist is None:
        return False
    return all(getattr(checklist, name) for name in CHECKLIST_FIELDS)


def add_post_op_note(surgery, user, notes, complications="",
                     follow_up_instructions=""):
    """Record what happened. Only meaningful once the surgery has started."""
    if not str(notes or "").strip():
        raise TheatreActionError("Post-operative notes are required.")
    if surgery.status in ("scheduled", "pending"):
        raise TheatreActionError(
            "This surgery has not started yet; there is nothing to report."
        )

    return PostOperativeNote.objects.create(
        surgery=surgery,
        notes=notes,
        complications=complications,
        follow_up_instructions=follow_up_instructions,
        created_by=user,
    )


def record_equipment_usage(surgery, equipment, quantity_used=1, notes=""):
    """Note equipment against a surgery, refusing more than the theatre holds."""
    if quantity_used < 1:
        raise TheatreActionError("Quantity must be at least one.")
    if quantity_used > equipment.quantity_available:
        raise TheatreActionError(
            f"Only {equipment.quantity_available} of {equipment.name} available."
        )
    if not equipment.is_available:
        raise TheatreActionError(f"{equipment.name} is out of service.")

    usage, created = EquipmentUsage.objects.get_or_create(
        surgery=surgery, equipment=equipment,
        defaults={"quantity_used": quantity_used, "notes": notes},
    )
    if not created:
        usage.quantity_used = quantity_used
        usage.notes = notes or usage.notes
        usage.save()
    return usage


def theatre_day(theatre=None, date=None):
    """The list a theatre works through on one day."""
    date = date or timezone.localdate()
    queryset = (
        Surgery.objects
        .filter(scheduled_date__date=date)
        .select_related("patient", "surgery_type", "theatre", "primary_surgeon")
        .order_by("scheduled_date")
    )
    if theatre is not None:
        queryset = queryset.filter(theatre=theatre)
    return queryset
