"""Pharmacy invoicing on the unified billing.Invoice model.

Replaces the old pharmacy_billing app. Pharmacy invoices are ordinary
billing.Invoice rows with source_app="pharmacy", so there is a single
invoice ledger per prescription (prescription.invoices) instead of three
parallel link paths. This removes the structural cause of duplicate
prescription invoices.
"""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone

from billing.models import Invoice, Service


def pharmacy_invoices(prescription):
    """All pharmacy invoices for a prescription (the single canonical query)."""
    return Invoice.objects.filter(prescription=prescription, source_app="pharmacy")


def create_pharmacy_invoice(request, prescription, subtotal_value, force_new=False):
    """Create (or reuse) the pharmacy billing.Invoice for a prescription.

    Reuses an existing unpaid invoice unless force_new. Refuses to create a
    duplicate when the prescription's full patient portion is already paid
    (defence in depth; the single-ledger design is the real fix).
    """
    qs = pharmacy_invoices(prescription)

    # Reuse an existing unpaid invoice.
    if not force_new:
        existing = qs.filter(status__in=["pending", "partially_paid"]).first()
        if existing:
            return existing

        # Don't re-bill a fully-paid prescription (cart paid then cancelled,
        # fresh cart re-billing the full amount). Partial dispensing still works
        # because paid_total stays below full_payable until complete.
        paid_total = qs.filter(status="paid").aggregate(t=Sum("total_amount"))[
            "t"
        ] or Decimal("0.00")
        breakdown = prescription.get_pricing_breakdown()
        full_payable = Decimal(str(breakdown.get("patient_portion", 0))).quantize(
            Decimal("0.01")
        )
        if full_payable > 0 and paid_total >= full_payable:
            existing_paid = qs.filter(status="paid").order_by(
                "invoice_date", "id"
            ).last()
            messages.warning(
                request,
                f"Prescription {prescription.id} already fully paid "
                f"(₦{paid_total} ≥ ₦{full_payable}); reusing invoice "
                f"#{existing_paid.id} instead of duplicating.",
            )
            return existing_paid

    # Pharmacy service (for tax rate); create once if missing.
    pharmacy_service = Service.objects.filter(
        name__iexact="Medication Dispensing"
    ).first()
    if pharmacy_service is None:
        pharmacy_service = Service.objects.create(
            name="Medication Dispensing",
            description="Dispensing of prescribed medications",
            price=Decimal("0.00"),
            category=None,
            is_active=True,
        )

    subtotal_value = Decimal(str(subtotal_value)).quantize(Decimal("0.01"))

    tax_percentage = pharmacy_service.tax_percentage or Decimal("0.00")
    tax_amount = Decimal("0.00")
    if tax_percentage > 0:
        try:
            tax_amount = (
                (subtotal_value * tax_percentage) / Decimal("100.00")
            ).quantize(Decimal("0.01"))
        except InvalidOperation:
            tax_amount = Decimal("0.00")

    try:
        invoice = Invoice.objects.create(
            patient=prescription.patient,
            prescription=prescription,
            source_app="pharmacy",
            invoice_date=timezone.now(),
            due_date=timezone.now().date() + timezone.timedelta(days=7),
            subtotal=subtotal_value,
            tax_amount=tax_amount,
            discount_amount=Decimal("0.00"),
            status="pending",
        )
    except Exception as e:
        messages.error(request, f"Error creating pharmacy invoice: {e}")
        return None

    return invoice
