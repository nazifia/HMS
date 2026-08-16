"""Desk-office authorization shared by the HTML views and the mobile API.

Six modules ask the same question — consultations, referrals, prescriptions,
laboratory, radiology and theatre all carry `requires_authorization`,
`authorization_status` and an `authorization_code` FK — so issuing a code and
attaching it to the thing that was waiting is one operation here rather than
six copies.
"""
import random
import string
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from .models import AuthorizationCode

# What is waiting, by the name the API and the dashboard use for it.
# (model path, the code's service_type, a default amount when none is given)
AUTHORIZABLE = {
    "consultation": ("consultations.Consultation", "general", Decimal("5000.00")),
    "referral": ("consultations.Referral", "general", Decimal("10000.00")),
    "prescription": ("pharmacy.Prescription", "pharmacy", Decimal("0.00")),
    "laboratory": ("laboratory.TestRequest", "laboratory", Decimal("0.00")),
    "radiology": ("radiology.RadiologyOrder", "radiology", Decimal("0.00")),
    "surgery": ("theatre.Surgery", "theatre", Decimal("0.00")),
}

# Statuses that mean "the desk office has not dealt with this yet".
PENDING_STATUSES = ("required", "pending")


class AuthorizationError(Exception):
    """An authorization action that is not allowed right now."""


def model_for(kind):
    from django.apps import apps

    if kind not in AUTHORIZABLE:
        raise AuthorizationError(f"Unknown authorization type '{kind}'.")
    return apps.get_model(AUTHORIZABLE[kind][0])


def generate_code_string():
    """A code of the shape the desk office already reads out over the phone."""
    date_str = timezone.now().strftime("%Y%m%d")
    random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"AUTH-{date_str}-{random_str}"


def _unique_code():
    while True:
        code = generate_code_string()
        if not AuthorizationCode.objects.filter(code=code).exists():
            return code


def _as_amount(value, default=Decimal("0.00")):
    if value in (None, ""):
        return default
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise AuthorizationError("Invalid amount.")
    if amount < 0:
        raise AuthorizationError("Amount cannot be negative.")
    return amount


def issue_code(patient, amount, service_type="general", expiry_days=30,
               expiry_date=None, user=None, notes="", code=None):
    """Issue an authorization code for a patient.

    `code` supplies a manual code (the desk office sometimes reads one from a
    pre-printed book); leave it out and one is generated.
    """
    if not patient.is_nhia_patient():
        raise AuthorizationError(
            f"{patient.get_full_name()} is not an active NHIA patient."
        )

    amount = _as_amount(amount)
    if amount <= 0:
        # A code covering nothing is worse than no code: the module accepts it
        # and the money question is never asked.
        raise AuthorizationError(
            "Enter the amount this authorization covers."
        )

    if code:
        code = str(code).strip().upper()
        if AuthorizationCode.objects.filter(code=code).exists():
            raise AuthorizationError(
                f'Authorization code "{code}" already exists. Use a different one.'
            )
    else:
        code = _unique_code()

    if expiry_date is None:
        try:
            expiry_days = int(expiry_days)
        except (TypeError, ValueError):
            raise AuthorizationError("Invalid expiry period.")
        if expiry_days < 1:
            raise AuthorizationError("Expiry must be at least one day away.")
        expiry_date = timezone.now().date() + timezone.timedelta(days=expiry_days)

    return AuthorizationCode.objects.create(
        code=code,
        patient=patient,
        service_type=service_type,
        amount=amount,
        expiry_date=expiry_date,
        status="active",
        notes=notes,
        generated_by=user,
    )


def estimated_amount(kind, item):
    """What the code should cover, from the item itself where it knows."""
    default = AUTHORIZABLE[kind][2]
    if kind == "referral":
        return referral_estimated_cost(item)
    for method in ("get_total_prescribed_price", "get_total_price", "get_total_cost"):
        if hasattr(item, method):
            amount = _as_amount(getattr(item, method)(), default)
            if amount > 0:
                return amount
    return default


def authorize(kind, item, user, amount=None, expiry_days=30, notes="", code=None):
    """Issue a code for something that is waiting on one, and attach it.

    Attaching is the half that matters: a code that is never linked leaves the
    item sitting in the queue and the ward still blocked.
    """
    if not getattr(item, "requires_authorization", False):
        raise AuthorizationError(f"This {kind} does not require authorization.")
    if getattr(item, "authorization_code_id", None):
        raise AuthorizationError(f"This {kind} is already authorized.")

    service_type = AUTHORIZABLE[kind][1]
    amount = _as_amount(amount) if amount not in (None, "") else estimated_amount(kind, item)

    with transaction.atomic():
        auth_code = issue_code(
            item.patient,
            amount=amount,
            service_type=service_type,
            expiry_days=expiry_days,
            user=user,
            notes=f"Generated for {kind} #{item.pk}. {notes}".strip(),
            code=code,
        )
        item.authorization_code = auth_code
        item.authorization_status = "authorized"
        item.save()

    return auth_code


def pending_queryset(kind):
    """Items of one kind still waiting on the desk office."""
    model = model_for(kind)
    return model.objects.filter(
        requires_authorization=True,
        authorization_status__in=PENDING_STATUSES,
    ).select_related("patient")


def pending_counts():
    """How much is waiting, per kind, for the dashboard."""
    counts = {kind: pending_queryset(kind).count() for kind in AUTHORIZABLE}
    counts["total"] = sum(counts.values())
    return counts


def cancel_code(auth_code):
    """Cancel an active code. Used codes stay used — that is the audit trail."""
    if auth_code.status != "active":
        raise AuthorizationError(
            f"Only active codes can be cancelled; this one is "
            f"{auth_code.get_status_display().lower()}."
        )
    auth_code.status = "cancelled"
    auth_code.save(update_fields=["status"])
    return auth_code


def expire_stale_codes():
    """Move codes past their expiry date out of 'active'. Cheap, so callers
    run it before listing rather than relying on a scheduled job."""
    return AuthorizationCode.objects.filter(
        status="active", expiry_date__lt=timezone.now().date()
    ).update(status="expired")


def referral_estimated_cost(referral):
    """Estimated cost for a referral, by where it is going."""
    department_costs = {
        ("surgery", "theatre", "operating"): 25000.00,
        ("radiology", "imaging", "x-ray"): 15000.00,
        ("laboratory", "lab", "pathology"): 12000.00,
        ("physiotherapy", "rehabilitation"): 8000.00,
        ("ophthalmic", "ophthalmology", "eye"): 18000.00,
        ("dental", "oral"): 10000.00,
        ("neurology", "neurosurgery"): 20000.00,
        ("oncology", "cancer"): 30000.00,
        ("cardiology", "heart"): 22000.00,
        ("icu", "intensive", "critical"): 35000.00,
        ("nhia", "national health insurance"): 5000.00,
    }
    specialty_costs = {
        ("surgery", "surgical", "operative"): 25000.00,
        ("cardiology", "heart"): 22000.00,
        ("neurology", "neurosurgery", "brain"): 20000.00,
        ("oncology", "cancer", "tumor"): 30000.00,
    }

    if referral.referred_to_department:
        name = referral.referred_to_department.name.lower()
        for names, cost in department_costs.items():
            if name in names:
                return Decimal(str(cost))

    if referral.referred_to_specialty:
        specialty = referral.referred_to_specialty.lower()
        for words, cost in specialty_costs.items():
            if any(word in specialty for word in words):
                return Decimal(str(cost))

    return AUTHORIZABLE["referral"][2]
