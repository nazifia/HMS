from decimal import Decimal, InvalidOperation
from django.utils import timezone
from billing.models import Invoice, InvoiceItem, Service
from django.contrib import messages
from nhia.models import NHIAPatient # Import NHIAPatient

def create_pharmacy_invoice(request, prescription, subtotal_value):
    messages.info(request, f"[create_pharmacy_invoice] Called for Prescription ID: {prescription.id}, Subtotal: {subtotal_value}")
    try:
        pharmacy_service = Service.objects.get(name__iexact="Medication Dispensing")
        messages.info(request, f"[create_pharmacy_invoice] Found 'Medication Dispensing' service. ID: {pharmacy_service.id}, Tax: {pharmacy_service.tax_percentage}%")
    except Service.DoesNotExist:
        messages.error(request, "Billing service 'Medication Dispensing' not found. Invoice cannot be created. Please configure this service in the billing module.")
        return None
    except Exception as e:
        messages.error(request, f"[create_pharmacy_invoice] Error fetching 'Medication Dispensing' service: {str(e)}. Invoice cannot be created.")
        return None

    subtotal_value = Decimal(str(subtotal_value)).quantize(Decimal('0.01'))
    
    # Check if the patient is an NHIA patient
    is_nhia_patient = (prescription.patient.patient_type == 'nhia')

    if is_nhia_patient:
        # NHIA patients pay 10% of the medication cost
        subtotal_value = subtotal_value * Decimal('0.10')
        messages.info(request, f"[create_pharmacy_invoice] NHIA patient detected. Medication cost adjusted to 10%: {subtotal_value}")

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
        messages.info(request, f"[create_pharmacy_invoice] Attempting to create Invoice object for Prescription ID: {prescription.id} with subtotal: {subtotal_value}, tax: {tax_amount_calculated}.")
        invoice = Invoice.objects.create(
            patient=prescription.patient,
            prescription=prescription,
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=7),
            created_by=request.user,
            subtotal=subtotal_value,
            tax_amount=tax_amount_calculated,
            discount_amount=Decimal('0.00'),
            status='pending',
            source_app='pharmacy'
        )
        messages.info(request, f"[create_pharmacy_invoice] Invoice object CREATED. ID: {invoice.id}, Number: {invoice.invoice_number}")
    except Exception as e:
        messages.error(request, f"[create_pharmacy_invoice] CRITICAL ERROR creating Invoice object: {str(e)}")
        return None

    try:
        messages.info(request, f"[create_pharmacy_invoice] Attempting to create InvoiceItem for Invoice ID: {invoice.id}, Service ID: {pharmacy_service.id}, Unit Price: {subtotal_value}, Tax %: {tax_percentage}")
        InvoiceItem.objects.create(
            invoice=invoice,
            service=pharmacy_service,
            description=f"Medications for Prescription #{prescription.id} (Total Prescribed Value)",
            quantity=1,
            unit_price=subtotal_value,
            tax_percentage=tax_percentage, 
        )
        messages.info(request, f"[create_pharmacy_invoice] InvoiceItem object CREATED for Invoice ID: {invoice.id}")
    except Exception as e:
        messages.error(request, f"[create_pharmacy_invoice] CRITICAL ERROR creating InvoiceItem object: {str(e)}. Data: invoice_id={invoice.id}, service_id={pharmacy_service.id}, unit_price={subtotal_value}")
        if invoice and invoice.pk:
            try:
                invoice.delete()
                messages.warning(request, f"[create_pharmacy_invoice] Orphaned Invoice ID: {invoice.id} deleted due to InvoiceItem creation failure.")
            except Exception as del_e:
                messages.error(request, f"[create_pharmacy_invoice] Failed to delete orphaned Invoice ID: {invoice.id}. Error: {del_e}")
        return None

    try:
        invoice.save()
        messages.info(request, f"[create_pharmacy_invoice] Final Invoice SAVE successful. ID: {invoice.id}, Total: {invoice.total_amount}")
    except Exception as e:
        messages.error(request, f"[create_pharmacy_invoice] CRITICAL ERROR saving Invoice after InvoiceItem: {str(e)}")
        return None
    return invoice
