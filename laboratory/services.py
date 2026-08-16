"""Laboratory workflow shared by the HTML views and the mobile REST API.

The rules themselves live on TestRequest (`can_be_processed`,
`is_payment_verified`); this is where the surrounding workflow lives — which
status changes are legal, when a result may be entered, and what verifying one
does to the request.
"""
from django.db import transaction
from django.utils import timezone

from .models import TestRequest, TestResult, TestResultParameter


class LabActionError(Exception):
    """A laboratory action that is not allowed right now."""


def assert_can_enter_results(test_request):
    """Raise unless results may be entered against this request."""
    can_process, message = test_request.can_be_processed()
    if not can_process:
        raise LabActionError(message)

    if not test_request.is_payment_verified():
        raise LabActionError(
            "Cannot add results. Payment is pending for this test request."
        )


def update_status(test_request, new_status):
    """Move a request along, refusing the transitions that are not allowed."""
    if new_status not in dict(TestRequest.STATUS_CHOICES):
        raise LabActionError("Invalid status.")

    # Sample handling and processing need authorization settled first.
    if new_status in ("sample_collected", "processing"):
        can_process, message = test_request.can_be_processed()
        if not can_process:
            raise LabActionError(message)

    # An unpaid request may only be cancelled.
    if test_request.status == "awaiting_payment" and new_status != "cancelled":
        raise LabActionError(
            "Cannot proceed. Payment is still pending for this test request."
        )

    test_request.status = new_status
    test_request.save()
    return test_request


def create_result(test_request, test, user, notes="", parameters=None,
                  sample_collection_date=None):
    """Record one test's result, with its parameter values.

    `parameters` maps TestParameter id -> {"value", "is_normal", "notes"}.
    """
    assert_can_enter_results(test_request)

    if not test_request.tests.filter(id=test.id).exists():
        raise LabActionError(f"{test.name} is not part of this test request.")

    if TestResult.objects.filter(test_request=test_request, test=test).exists():
        raise LabActionError(f"{test.name} already has a result.")

    with transaction.atomic():
        result = TestResult.objects.create(
            test_request=test_request,
            test=test,
            performed_by=user,
            notes=notes,
            sample_collection_date=sample_collection_date,
        )
        _save_parameters(result, parameters or {})
        sync_request_completion(test_request)

    return result


def _save_parameters(result, parameters):
    """Write parameter values, ignoring any that are not part of this test."""
    valid = {p.id: p for p in result.test.parameters.all()}
    for parameter_id, data in parameters.items():
        parameter = valid.get(int(parameter_id))
        if parameter is None:
            continue
        value = str(data.get("value", "")).strip()
        if not value:
            continue
        TestResultParameter.objects.update_or_create(
            test_result=result,
            parameter=parameter,
            defaults={
                "value": value,
                "is_normal": bool(data.get("is_normal", True)),
                "notes": data.get("notes", ""),
            },
        )


def sync_request_completion(test_request):
    """Set the request's status from the state of its results.

    A request is complete when every test on it has a *verified* result —
    entering results is not the same as signing them off. While results are
    still coming in (or awaiting verification) the request sits in processing.
    """
    if test_request.status in ("cancelled", "awaiting_payment"):
        return test_request

    ordered = set(test_request.tests.values_list("id", flat=True))
    results = TestResult.objects.filter(test_request=test_request)
    verified = set(results.filter(verified_by__isnull=False).values_list(
        "test_id", flat=True
    ))

    if ordered and ordered <= verified:
        new_status = "completed"
    elif results.exists():
        new_status = "processing"
    elif test_request.status == "completed":
        # Results were removed; the request is open again.
        new_status = "processing"
    else:
        return test_request

    if test_request.status != new_status:
        test_request.status = new_status
        test_request.save(update_fields=["status"])
    return test_request


def verify_result(result, user):
    """Sign off a result; completes the request once every test is signed off."""
    if result.verified_by:
        raise LabActionError(
            f"This result was already verified by "
            f"{result.verified_by.get_full_name()}."
        )
    if not result.parameters.exclude(value="").exists() and not result.result_file:
        raise LabActionError(
            "Nothing to verify: record parameter values or attach a result file first."
        )

    with transaction.atomic():
        result.verified_by = user
        result.verified_date = timezone.now()
        result.save(update_fields=["verified_by", "verified_date"])
        sync_request_completion(result.test_request)

    return result
