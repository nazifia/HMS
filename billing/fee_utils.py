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
from django.db.models import F, Q, Sum
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
    "popd": ("POPD Consultation Fee", Decimal("1000.00")),
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


def create_service_invoice(patient, services, source_app, created_by=None, due_days=7):
    """
    Build a ``pending`` invoice for ``services`` billed to ``patient``.

    ``services`` is a single Service, or an iterable whose entries are either a
    Service (billed at its own price) or a ``(service, price, description)``
    tuple for a partial charge such as a clinic top-up.
    """
    if isinstance(services, Service):
        services = [services]
    lines = [
        (entry, entry.price, entry.name) if isinstance(entry, Service) else tuple(entry)
        for entry in services
    ]

    subtotal = Decimal("0")
    tax_amount = Decimal("0")
    for service, price, _description in lines:
        subtotal += price
        tax_amount += (price * (service.tax_percentage or Decimal("0"))) / 100

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
    for service, price, description in lines:
        item_tax = (price * (service.tax_percentage or Decimal("0"))) / 100
        InvoiceItem.objects.create(
            invoice=invoice,
            service=service,
            description=description,
            quantity=1,
            unit_price=price,
            tax_percentage=service.tax_percentage or Decimal("0"),
            tax_amount=item_tax,
            total_amount=price + item_tax,
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


def consultation_service_names():
    """Every service name that counts as a consultation fee."""
    return [CONSULTATION_FEE_SERVICE_NAME] + [
        name for name, _price in CLINIC_CONSULTATION_FEES.values()
    ]


def consultation_invoices(patient, since=None):
    """
    Invoices that bill this patient a consultation fee.

    Matches the standalone consultation/appointment invoices *and* the combined
    registration invoice (registration + consultation billed together), which
    carries source_app='registration' but holds a consultation-fee item.
    """
    qs = Invoice.objects.filter(patient=patient).filter(
        Q(source_app__in=["consultation", "appointment"])
        | Q(items__service__name__in=consultation_service_names())
    ).distinct()
    if since is not None:
        qs = qs.filter(invoice_date__gte=since)
    return qs


def consultation_amount_billed(patient, since=None):
    """
    Consultation fee (pre-tax) already billed to ``patient`` since ``since``.

    ``None`` when nothing was billed - which is how callers tell "no fee yet"
    apart from "fee billed at ₦0". Sums the standalone consultation invoices,
    the consultation item of a combined registration invoice, and any earlier
    clinic top-up, so a second top-up measures against the running total.
    """
    items = InvoiceItem.objects.filter(
        invoice__in=consultation_invoices(patient, since=since).exclude(
            status="cancelled"
        )
    ).filter(
        Q(service__name__in=consultation_service_names())
        | Q(invoice__source_app__in=["consultation", "appointment"])
    )
    total = items.aggregate(
        billed=Sum(F("unit_price") * F("quantity"))
    )["billed"]
    return None if total is None else Decimal(total)


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
def create_registration_fee(patient, user=None, clinic_type=None):
    """
    Apply the registration-fee policy for a freshly registered/converted patient.

    The invoice bills the registration fee *and* the first consultation fee
    together, so the patient settles both at one counter visit. ``clinic_type``
    ('mopd'/'sopd'/'popd') picks the matching consultation fee, else the generic
    one.

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

    services = [get_registration_fee_service()]
    # Same-visit consultation fee for the patient types that self-pay it.
    if patient.patient_type in ("regular", RETAINERSHIP_TYPE):
        services.append(get_consultation_fee_service(clinic_type))
    invoice = create_service_invoice(
        patient, services, source_app="registration", created_by=user
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
    the generic fee. Regular patients get a pending invoice; retainership
    patients get the invoice auto-paid from the (shared) wallet. NHIA goes
    through authorization instead.

    Same day, the fee is charged once: if a consultation fee was already billed
    (standalone or on the combined registration invoice) this returns None, or
    an invoice for the difference when the clinic seen costs more than what was
    billed. A cheaper clinic is not refunded.
    """
    if patient.patient_type not in ("regular", RETAINERSHIP_TYPE):
        return None

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    service = get_consultation_fee_service(clinic_type)
    # Paid invoices count as billed too, else a settled fee is charged twice.
    billed = consultation_amount_billed(patient, since=today_start)

    if billed is None:
        lines = [service]
    else:
        shortfall = service.price - billed
        if shortfall <= 0:
            return None
        # ponytail: bill only the gap; no refund when the clinic seen is cheaper
        lines = [(service, shortfall, f"{service.name} (clinic top-up)")]

    invoice = create_service_invoice(
        patient, lines, source_app="consultation", created_by=user
    )

    if patient.patient_type == RETAINERSHIP_TYPE:
        try:
            pay_invoice_from_wallet(invoice, user)
        except Exception as exc:  # pragma: no cover - safety net
            logger.error("Retainership consultation wallet payment failed: %s", exc)
        invoice.refresh_from_db()

    return invoice
