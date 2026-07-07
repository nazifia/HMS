"""
Helpers for automatic registration and consultation fee invoicing.

Centralizes the logic that:
  * creates the registration-fee invoice when a patient is registered, with
    type-specific behaviour (regular = pay-then-activate, NHIA = free,
    retainership = auto-paid from wallet);
  * creates the consultation-fee invoice when a regular outpatient is sent to a
    physician (added to the waiting list).

Fee amounts are stored as editable ``billing.Service`` rows so they can be
changed from the admin without code edits. The two services are seeded by a
data migration but ``get_or_create`` here keeps things self-healing.
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Invoice, InvoiceItem, Payment, Service, ServiceCategory

logger = logging.getLogger(__name__)

# Canonical service names (also referenced by the seed data migration).
REGISTRATION_FEE_SERVICE_NAME = "Registration Fee"
CONSULTATION_FEE_SERVICE_NAME = "Consultation Fee"

DEFAULT_REGISTRATION_FEE = Decimal("500.00")
DEFAULT_CONSULTATION_FEE = Decimal("1000.00")

# Per-clinic consultation fees. Falls back to the generic fee when the clinic
# type is unset or its service is missing. Prices are seeded here via
# get_or_create and stay editable from the billing admin afterwards.
CLINIC_CONSULTATION_FEES = {
    "mopd": ("MOPD Consultation Fee", Decimal("1000.00")),
    "sopd": ("SOPD Consultation Fee", Decimal("1500.00")),
}

# Patient types that are exempt from a self-pay registration fee.
NHIA_TYPE = "nhia"
RETAINERSHIP_TYPE = "retainership"


def _get_or_create_service(name, category_name, default_price):
    """Fetch (or create) the fee Service under the given category."""
    category, _ = ServiceCategory.objects.get_or_create(name=category_name)
    service, created = Service.objects.get_or_create(
        name=name,
        defaults={
            "category": category,
            "price": default_price,
            "is_active": True,
        },
    )
    return service


def get_registration_fee_service():
    return _get_or_create_service(
        REGISTRATION_FEE_SERVICE_NAME, "Registration", DEFAULT_REGISTRATION_FEE
    )


def get_consultation_fee_service(clinic_type=None):
    """Consultation fee service, clinic-specific (MOPD/SOPD) when given."""
    clinic = CLINIC_CONSULTATION_FEES.get((clinic_type or "").lower())
    if clinic:
        name, default_price = clinic
        return _get_or_create_service(name, "Consultation", default_price)
    return _get_or_create_service(
        CONSULTATION_FEE_SERVICE_NAME, "Consultation", DEFAULT_CONSULTATION_FEE
    )


def create_service_invoice(patient, service, source_app, created_by=None, due_days=7):
    """
    Build a single-item, ``pending`` invoice for ``service`` billed to ``patient``.

    Reuses ``InvoiceItem.save()`` to compute tax/total, then re-saves the invoice
    so its subtotal/tax/total reflect the item.
    """
    tax_percentage = service.tax_percentage or Decimal("0")
    subtotal = service.price
    tax_amount = (subtotal * tax_percentage) / 100

    invoice = Invoice.objects.create(
        patient=patient,
        invoice_date=timezone.now(),
        due_date=timezone.now().date() + timedelta(days=due_days),
        status="pending",
        source_app=source_app,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=subtotal + tax_amount,
        created_by=created_by,
    )
    InvoiceItem.objects.create(
        invoice=invoice,
        service=service,
        description=service.name,
        quantity=1,
        unit_price=service.price,
        tax_percentage=tax_percentage,
        tax_amount=tax_amount,
        total_amount=subtotal + tax_amount,
    )
    return invoice


def pay_invoice_from_wallet(invoice, user=None):
    """
    Settle the outstanding balance of ``invoice`` from the patient's wallet.

    Creating a wallet ``Payment`` triggers the existing billing signals which
    debit the (effective/shared) wallet and mark the invoice paid.
    """
    balance = invoice.get_balance()
    if balance <= 0:
        return None
    return Payment.objects.create(
        invoice=invoice,
        amount=balance,
        payment_method="wallet",
        payment_date=timezone.now(),
        received_by=user,
        notes=f"Auto-payment from wallet for {invoice.get_source_app_display()} fee",
    )


def _has_open_invoice(patient, source_app, since=None):
    """True if patient already has a non-cancelled, unpaid invoice of this type."""
    qs = Invoice.objects.filter(
        patient=patient,
        source_app=source_app,
        status__in=["draft", "pending", "partially_paid"],
    )
    if since is not None:
        qs = qs.filter(invoice_date__gte=since)
    return qs.exists()


@transaction.atomic
def create_registration_fee(patient, user=None):
    """
    Apply the registration-fee policy for a freshly registered/converted patient.

    Returns the invoice (or None for NHIA). Side effect: sets ``patient.is_active``
    according to type and payment.
    """
    # NHIA: registration is free -> active immediately, no invoice.
    if patient.patient_type == NHIA_TYPE:
        if not patient.is_active:
            patient.is_active = True
            patient.save(update_fields=["is_active"])
        return None

    # Idempotency: don't stack registration invoices.
    if _has_open_invoice(patient, "registration"):
        return None

    service = get_registration_fee_service()
    invoice = create_service_invoice(
        patient, service, source_app="registration", created_by=user
    )

    if patient.patient_type == RETAINERSHIP_TYPE:
        # Pay from the (shared retainership) wallet -> activation handled by signal.
        try:
            pay_invoice_from_wallet(invoice, user)
        except Exception as exc:  # pragma: no cover - safety net
            logger.error("Retainership registration wallet payment failed: %s", exc)
        if not patient.is_active:
            patient.is_active = True
            patient.save(update_fields=["is_active"])
        return invoice

    # Self-pay (regular/private/etc.): inactive until the fee is paid.
    if patient.is_active:
        patient.is_active = False
        patient.save(update_fields=["is_active"])
    return invoice


@transaction.atomic
def create_consultation_fee(patient, user=None, service_point=None, clinic_type=None):
    """
    Create the consultation-fee invoice for a regular outpatient.

    ``clinic_type`` ('mopd'/'sopd') selects the matching consultation fee, else
    the generic fee. Only regular patients are billed here (NHIA goes through
    authorization; retainership/others are out of scope per spec). Idempotent
    for the same day.
    """
    if patient.patient_type != "regular":
        return None

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if _has_open_invoice(patient, "consultation", since=today_start):
        return None

    service = get_consultation_fee_service(clinic_type)
    return create_service_invoice(
        patient, service, source_app="consultation", created_by=user
    )
