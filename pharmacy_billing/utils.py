from decimal import Decimal, InvalidOperation
from django.utils import timezone
from billing.models import Service
from .models import Invoice as PharmacyInvoice
from django.contrib import messages
from nhia.models import NHIAPatient # Import NHIAPatient

def create_pharmacy_invoice(request, prescription, subtotal_value):
    messages.info(request, f"[create_pharmacy_invoice] Called for Prescription ID: {prescription.id}, Subtotal: {subtotal_value}")
    
    # Check if an invoice already exists for this prescription
    try:
        existing_invoice = PharmacyInvoice.objects.get(prescription=prescription)
        messages.info(request, f"[create_pharmacy_invoice] Invoice already exists for Prescription ID: {prescription.id}, Invoice ID: {existing_invoice.id}")
        return existing_invoice
    except PharmacyInvoice.DoesNotExist:
        # No existing invoice, proceed with creation
        pass
    except Exception as e:
        messages.error(request, f"[create_pharmacy_invoice] Error checking for existing invoice: {str(e)}")
        return None

    try:
        pharmacy_service = Service.objects.get(name__iexact="Medication Dispensing")
        messages.info(request, f"[create_pharmacy_invoice] Found 'Medication Dispensing' service. ID: {pharmacy_service.id}, Tax: {pharmacy_service.tax_percentage}%")
    except Service.DoesNotExist:
        messages.error(request, "Billing service 'Medication Dispensing' not found. Invoice cannot be created. Please configure this service in the billing module.")
        return None
    except Exception as e:
        messages.error(request, f"[create_pharmacy_invoice] Error fetching 'Medication Dispensing' service: {str(e)}. Invoice cannot be created.")
        return None

    # Use the provided subtotal_value (based on actual dispensed quantities)
    # Convert to Decimal and quantize for precision
    subtotal_value = Decimal(str(subtotal_value)).quantize(Decimal('0.01'))

    # Get pricing breakdown for logging
    pricing_breakdown = prescription.get_pricing_breakdown()

    if pricing_breakdown['is_nhia_patient']:
        messages.info(request, f"[create_pharmacy_invoice] NHIA patient detected. Patient pays (based on dispensed): ₦{subtotal_value}")
    else:
        messages.info(request, f"[create_pharmacy_invoice] Non-NHIA patient. Patient pays full cost (based on dispensed): ₦{subtotal_value}")

    tax_percentage = pharmacy_service.tax_percentage if pharmacy_service and pharmacy_service.tax_percentage is not None else Decimal('0.00')
    tax_amount_calculated = Decimal('0.00')
    if tax_percentage > 0:
        try:
            tax_amount_calculated = (subtotal_value * tax_percentage) / Decimal('100.00')
            tax_amount_calculated = tax_amount_calculated.quantize(Decimal('0.01')) 
            messages.info(request, f"[create_pharmacy_invoice] Calculated tax: {tax_amount_calculated} at {tax_percentage}%")
        except InvalidOperation:
            messages.error(request, f"[create_pharmacy_invoice] Invalid operation during tax calculation for subtotal: {subtotal_value}")
            tax_amount_calculated = Decimal('0.00')

    invoice = None
    try:
        messages.info(request, f"[create_pharmacy_invoice] Attempting to create PharmacyInvoice object for Prescription ID: {prescription.id} with subtotal: {subtotal_value}, tax: {tax_amount_calculated}.")
        invoice = PharmacyInvoice.objects.create(
            patient=prescription.patient,
            prescription=prescription,
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=7),
            subtotal=subtotal_value,
            tax_amount=tax_amount_calculated,
            discount_amount=Decimal('0.00'),
            status='pending'
        )
        messages.info(request, f"[create_pharmacy_invoice] PharmacyInvoice object CREATED. ID: {invoice.id}")
        messages.info(request, f"[create_pharmacy_invoice] Final Invoice SAVE successful. ID: {invoice.id}, Total: {invoice.total_amount}")
    except Exception as e:
        messages.error(request, f"[create_pharmacy_invoice] CRITICAL ERROR creating PharmacyInvoice object: {str(e)}")
        return None

    return invoice