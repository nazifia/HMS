"""Radiology workflow shared by the HTML views and the mobile REST API.

The rules themselves live on RadiologyOrder (`can_be_processed`,
`can_add_result`, `is_payment_verified`); this is the workflow around them —
which status moves are legal, when a report may be written, and what verifying
one records.
"""
from django.db import transaction
from django.utils import timezone

from .models import RadiologyOrder, RadiologyResult


class RadiologyActionError(Exception):
    """A radiology action that is not allowed right now."""


# Fields a report carries. Everything else on the model is set by the workflow.
RESULT_FIELDS = (
    "findings", "impression", "technique", "contrast_used", "contrast_amount",
    "recommendations", "image_quality", "study_status", "notes",
    "is_abnormal", "study_date",
)

FILE_FIELDS = ("image_file", "images", "report_file")


def assert_can_add_result(order):
    """Raise unless a report may be written against this order."""
    can_add, message = order.can_add_result()
    if not can_add:
        raise RadiologyActionError(message)

    if not order.is_payment_verified():
        raise RadiologyActionError(
            "Cannot add results. Payment is pending for this radiology order."
        )


def update_status(order, new_status):
    """Move an order along, refusing the transitions that are not allowed."""
    if new_status not in dict(RadiologyOrder.STATUS_CHOICES):
        raise RadiologyActionError("Invalid status.")

    # Scheduling and completing need authorization settled first.
    if new_status in ("scheduled", "completed"):
        can_process, message = order.can_be_processed()
        if not can_process:
            raise RadiologyActionError(message)

    # An unpaid order may only be cancelled.
    if order.status == "awaiting_payment" and new_status != "cancelled":
        raise RadiologyActionError(
            "Cannot proceed. Payment is still pending for this radiology order."
        )

    order.status = new_status
    if new_status == "scheduled" and not order.scheduled_date:
        order.scheduled_date = timezone.now()
    if new_status == "completed":
        order.completed_date = timezone.now()
    order.save()
    return order


def save_result(order, user, fields=None, files=None):
    """Write (or update) the report for an order.

    One order has one report — `RadiologyResult.order` is a OneToOne — so this
    updates the existing row rather than refusing, which is what a radiologist
    correcting a typo expects.
    """
    assert_can_add_result(order)

    fields = fields or {}
    files = files or {}

    if not str(fields.get("findings", "")).strip():
        raise RadiologyActionError("Findings are required.")
    if not str(fields.get("impression", "")).strip():
        raise RadiologyActionError("An impression is required.")

    with transaction.atomic():
        result = RadiologyResult.objects.filter(order=order).first()
        if result is None:
            result = RadiologyResult(order=order, performed_by=user)
        elif result.result_status in ("verified", "finalized"):
            raise RadiologyActionError(
                f"This report is already {result.get_result_status_display().lower()} "
                f"and cannot be edited."
            )

        for name in RESULT_FIELDS:
            # Blank means "not recorded": leave what is already there alone.
            if name in fields and fields[name] not in (None, ""):
                setattr(result, name, fields[name])
        for name in FILE_FIELDS:
            if files.get(name) is not None:
                setattr(result, name, files[name])

        result.result_status = "submitted"
        if not result.study_date:
            result.study_date = timezone.now()
        result.save()

    return result


def verify_result(result, user, notes=""):
    """Sign off a report: records who, when, and any verification note."""
    if result.result_status in ("verified", "finalized"):
        signed_by = (
            result.verified_by.get_full_name() if result.verified_by else "someone else"
        )
        raise RadiologyActionError(f"This report was already verified by {signed_by}.")
    if not (result.findings or "").strip():
        raise RadiologyActionError("Nothing to verify: the report has no findings.")

    with transaction.atomic():
        result.result_status = "verified"
        # verified_by was never set by the verification page, so the record of
        # who signed a report off was lost.
        result.verified_by = user
        result.verified_date = timezone.now()
        if notes:
            stamp = timezone.now().strftime("%Y-%m-%d %H:%M")
            result.verification_notes = (
                f"{result.verification_notes}\n\n--- Verification on {stamp} ---\n{notes}"
                if result.verification_notes else notes
            )
        result.save()

        # A signed-off report means the study is done.
        if result.order.status not in ("completed", "cancelled"):
            result.order.status = "completed"
            result.order.completed_date = timezone.now()
            result.order.save()

    return result


def finalize_result(result, user):
    """Close a report for good. Only a verified one can be finalized."""
    if result.result_status == "finalized":
        raise RadiologyActionError("This report is already finalized.")
    if result.result_status != "verified":
        raise RadiologyActionError("Verify the report before finalizing it.")

    result.result_status = "finalized"
    result.save(update_fields=["result_status", "updated_at"])
    return result
