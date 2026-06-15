from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db.models import Sum
from billing.models import Service
from .models import Invoice as PharmacyInvoice
from django.contrib import messages
from nhia.models import NHIAPatient  # Import NHIAPatient


def create_pharmacy_invoice(request, prescription, subtotal_value, force_new=False):
    messages.info(
        request,
        f"[create_pharmacy_invoice] Called for Prescription ID: {prescription.id}, Subtotal: {subtotal_value}, Force New: {force_new}",
    )

    # Check if an invoice already exists for this prescription
    # Only reuse UNPAID invoices - don't reuse paid invoices (for partial dispensing support)
    if not force_new:
        try:
            existing_invoice = PharmacyInvoice.objects.filter(
                prescription=prescription, status__in=["pending", "unpaid"]
            ).first()
            if existing_invoice:
                messages.info(
                    request,
                    f"[create_pharmacy_invoice] Found unpaid invoice for Prescription ID: {prescription.id}, Invoice ID: {existing_invoice.id}. Reusing.",
                )
                return existing_invoice
        except Exception as e:
            messages.error(
                request,
                f"[create_pharmacy_invoice] Error checking for existing invoice: {str(e)}",
            )

    # Guard against duplicate full charges:
    # If existing PAID invoices already cover the prescription's full patient
    # portion, do NOT create another invoice. This stops double-billing when a
    # cart is paid then cancelled and a fresh cart re-bills the full amount.
    # Genuine partial dispensing still works because the already-paid total is
    # less than the full payable, so a new invoice is allowed for the remainder.
    if not force_new:
        try:
            paid_total = PharmacyInvoice.objects.filter(
                prescription=prescription, status="paid"
            ).aggregate(t=Sum("total_amount"))["t"] or Decimal("0.00")
            breakdown = prescription.get_pricing_breakdown()
            full_payable = Decimal(
                str(breakdown.get("patient_portion", 0))
            ).quantize(Decimal("0.01"))
            if full_payable > 0 and paid_total >= full_payable:
                existing_paid = (
                    PharmacyInvoice.objects.filter(
                        prescription=prescription, status="paid"
                    )
                    .order_by("invoice_date", "id")
                    .last()
                )
                messages.warning(
                    request,
                    f"[create_pharmacy_invoice] Prescription ID {prescription.id} is already "
                    f"fully paid (₦{paid_total} >= ₦{full_payable}). Reusing existing paid "
                    f"invoice #{existing_paid.id} instead of creating a duplicate.",
                )
                return existing_paid
        except Exception as e:
            messages.error(
                request,
                f"[create_pharmacy_invoice] Error checking full-payment guard: {str(e)}",
            )

    # Check if there's a PAID invoice - for partial dispensing we need a new invoice
    try:
        paid_invoice = PharmacyInvoice.objects.filter(
            prescription=prescription, status="paid"
        ).first()
        if paid_invoice:
            messages.info(
                request,
                f"[create_pharmacy_invoice] Found PAID invoice for Prescription ID: {prescription.id}, Invoice ID: {paid_invoice.id}. Creating NEW invoice for remaining items.",
            )
    except Exception as e:
        messages.info(request, f"[create_pharmacy_invoice] Note: {str(e)}")

    try:
        pharmacy_service = Service.objects.filter(name__iexact="Medication Dispensing").first()
        if pharmacy_service is None:
            pharmacy_service = Service.objects.create(
                name="Medication Dispensing",
                description="Dispensing of prescribed medications",
                price=Decimal("0.00"),
                category=None,
                is_active=True,
            )
            messages.info(
                request,
                f"[create_pharmacy_invoice] Auto-created 'Medication Dispensing' service. ID: {pharmacy_service.id}",
            )
        else:
            messages.info(
                request,
                f"[create_pharmacy_invoice] Found 'Medication Dispensing' service. ID: {pharmacy_service.id}, Tax: {pharmacy_service.tax_percentage}%",
            )
    except Exception as e:
        messages.error(
            request,
            f"[create_pharmacy_invoice] Error fetching 'Medication Dispensing' service: {str(e)}. Invoice cannot be created.",
        )
        return None

    # Use the provided subtotal_value (based on actual dispensed quantities)
    # Convert to Decimal and quantize for precision
    subtotal_value = Decimal(str(subtotal_value)).quantize(Decimal("0.01"))

    # Get pricing breakdown for logging
    pricing_breakdown = prescription.get_pricing_breakdown()

    if pricing_breakdown["is_nhia_patient"]:
        messages.info(
            request,
            f"[create_pharmacy_invoice] NHIA patient detected. Patient pays (based on dispensed): ₦{subtotal_value}",
        )
    else:
        messages.info(
            request,
            f"[create_pharmacy_invoice] Non-NHIA patient. Patient pays full cost (based on dispensed): ₦{subtotal_value}",
        )

    tax_percentage = (
        pharmacy_service.tax_percentage
        if pharmacy_service and pharmacy_service.tax_percentage is not None
        else Decimal("0.00")
    )
    tax_amount_calculated = Decimal("0.00")
    if tax_percentage > 0:
        try:
            tax_amount_calculated = (subtotal_value * tax_percentage) / Decimal(
                "100.00"
            )
            tax_amount_calculated = tax_amount_calculated.quantize(Decimal("0.01"))
            messages.info(
                request,
                f"[create_pharmacy_invoice] Calculated tax: {tax_amount_calculated} at {tax_percentage}%",
            )
        except InvalidOperation:
            messages.error(
                request,
                f"[create_pharmacy_invoice] Invalid operation during tax calculation for subtotal: {subtotal_value}",
            )
            tax_amount_calculated = Decimal("0.00")

    invoice = None
    try:
        messages.info(
            request,
            f"[create_pharmacy_invoice] Attempting to create PharmacyInvoice object for Prescription ID: {prescription.id} with subtotal: {subtotal_value}, tax: {tax_amount_calculated}.",
        )
        invoice = PharmacyInvoice.objects.create(
            patient=prescription.patient,
            prescription=prescription,
            invoice_date=timezone.now(),
            due_date=timezone.now().date() + timezone.timedelta(days=7),
            subtotal=subtotal_value,
            tax_amount=tax_amount_calculated,
            discount_amount=Decimal("0.00"),
            status="pending",
        )
        messages.info(
            request,
            f"[create_pharmacy_invoice] PharmacyInvoice object CREATED. ID: {invoice.id}",
        )
        messages.info(
            request,
            f"[create_pharmacy_invoice] Final Invoice SAVE successful. ID: {invoice.id}, Total: {invoice.total_amount}",
        )
    except Exception as e:
        messages.error(
            request,
            f"[create_pharmacy_invoice] CRITICAL ERROR creating PharmacyInvoice object: {str(e)}",
        )
        return None

    return invoice
