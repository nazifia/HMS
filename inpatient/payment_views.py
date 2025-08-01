from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from .models import Admission, InpatientMedication
from .payment_forms import InpatientMedicationPaymentForm
from pharmacy.models import Prescription
from billing.models import Invoice, InvoiceItem, Payment, Service
from patients.models import PatientWallet
from core.audit_utils import log_audit_action
from core.models import InternalNotification


@login_required
def inpatient_medication_payment(request, admission_id, prescription_id):
    """Process payment for inpatient medication from billing office or patient wallet"""
    admission = get_object_or_404(Admission, id=admission_id)
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Get or create inpatient medication record
    inpatient_medication, created = InpatientMedication.objects.get_or_create(
        admission=admission,
        prescription=prescription,
        defaults={
            'ordered_by': request.user,
            'order_date': timezone.now()
        }
    )

    # Get or create invoice for this prescription
    invoice = None
    if hasattr(prescription, 'invoice') and prescription.invoice:
        invoice = prescription.invoice
    else:
        # Create invoice if it doesn't exist
        try:
            medication_service = Service.objects.get(name__iexact="Medication Dispensing")
        except Service.DoesNotExist:
            # Create the service if it doesn't exist
            medication_service = Service.objects.create(
                name="Medication Dispensing",
                description="Dispensing of prescribed medications for inpatients",
                price=0.00,  # Price will be calculated based on medications
                category=None
            )

        total_cost = prescription.get_total_prescribed_price()
        invoice = Invoice.objects.create(
            patient=admission.patient,
            status='pending',
            total_amount=total_cost,
            subtotal=total_cost,
            tax_amount=0,
            discount_amount=0,
            created_by=request.user,
            source_app='inpatient',
            prescription=prescription
        )

        InvoiceItem.objects.create(
            invoice=invoice,
            service=medication_service,
            description=f"Inpatient Medication for {admission.patient.get_full_name()}",
            quantity=1,
            unit_price=total_cost,
            tax_percentage=0,
            tax_amount=0,
            discount_amount=0,
            total_amount=total_cost
        )

    # Get patient wallet
    patient_wallet = None
    try:
        patient_wallet = PatientWallet.objects.get(patient=admission.patient)
    except PatientWallet.DoesNotExist:
        # Create wallet if it doesn't exist
        patient_wallet = PatientWallet.objects.create(
            patient=admission.patient,
            balance=0
        )

    remaining_amount = invoice.get_balance()

    if remaining_amount <= 0:
        messages.info(request, 'This medication has already been fully paid.')
        return redirect('inpatient:admission_detail', pk=admission.id)

    if request.method == 'POST':
        form = InpatientMedicationPaymentForm(
            request.POST,
            invoice=invoice,
            patient_wallet=patient_wallet
        )
        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.invoice = invoice
                    payment.received_by = request.user

                    payment_source = form.cleaned_data['payment_source']

                    if payment_source == 'patient_wallet':
                        # Force wallet payment method
                        payment.payment_method = 'wallet'

                    payment.save()

                    # The Payment model's save() method will automatically handle wallet deduction
                    # and create the appropriate WalletTransaction record if payment_method is 'wallet'

                    # Update inpatient medication record
                    inpatient_medication.is_paid = True
                    inpatient_medication.payment_source = payment_source
                    inpatient_medication.save()

                    # Audit log
                    log_audit_action(
                        request.user,
                        'create',
                        payment,
                        f"Recorded {payment_source} payment of ₦{payment.amount:.2f} for inpatient medication"
                    )

                    # Notification
                    InternalNotification.objects.create(
                        user=admission.attending_doctor,
                        message=f"Payment of ₦{payment.amount:.2f} recorded for inpatient medication via {payment_source}"
                    )

                    messages.success(request, f'Payment of ₦{payment.amount:.2f} recorded successfully via {payment_source.replace("_", " ").title()}.')
                    return redirect('inpatient:admission_detail', pk=admission.id)

            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')
    else:
        form = InpatientMedicationPaymentForm(
            invoice=invoice,
            patient_wallet=patient_wallet,
            initial={
                'amount': remaining_amount,
                'payment_date': timezone.now().date(),
                'payment_method': 'cash'
            }
        )

    context = {
        'form': form,
        'admission': admission,
        'prescription': prescription,
        'invoice': invoice,
        'patient_wallet': patient_wallet,
        'remaining_amount': remaining_amount,
        'inpatient_medication': inpatient_medication,
        'title': f'Payment for Inpatient Medication - {admission.patient.get_full_name()}'
    }

    return render(request, 'inpatient/medication_payment.html', context)


@login_required
def inpatient_medication_list(request, admission_id):
    """List all medications for an admission"""
    admission = get_object_or_404(Admission, id=admission_id)
    medications = InpatientMedication.objects.filter(admission=admission).select_related(
        'prescription', 'ordered_by'
    ).order_by('-order_date')

    context = {
        'admission': admission,
        'medications': medications,
        'title': f'Medications for {admission.patient.get_full_name()}'
    }

    return render(request, 'inpatient/medication_list.html', context)
