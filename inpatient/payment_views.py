from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
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
def process_outstanding_admission_payment(request, admission_id):
    """Process outstanding admission payment from patient wallet"""
    admission = get_object_or_404(Admission, id=admission_id)
    
    # Get patient wallet
    patient_wallet = None
    try:
        patient_wallet = PatientWallet.objects.get(patient=admission.patient)
    except PatientWallet.DoesNotExist:
        messages.error(request, 'Patient does not have a wallet.')
        return redirect('inpatient:admission_detail', pk=admission.id)
    
    # Calculate outstanding amount
    outstanding_amount = admission.get_outstanding_admission_cost()

    if outstanding_amount <= 0:
        messages.info(request, 'This admission has already been fully paid.')
        return redirect('inpatient:admission_detail', pk=admission.id)

    # Validate wallet balance before showing payment form
    wallet_balance = patient_wallet.balance
    if wallet_balance <= 0:
        messages.error(request, 'Patient wallet has insufficient balance to process any payment.')
        return redirect('inpatient:admission_detail', pk=admission.id)
    
    # Check if user has permission to process wallet payments
    # Only billing staff and authorized personnel should be able to process wallet payments
    user_roles = request.user.roles.values_list('name', flat=True)
    if not any(role in ['billing_staff', 'admin', 'cashier'] for role in user_roles):
        messages.error(request, 'You do not have permission to process wallet payments.')
        return redirect('inpatient:admission_detail', pk=admission.id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Check wallet balance before processing
                wallet_balance = patient_wallet.balance

                # Only deduct what's available in the wallet, not exceeding outstanding amount
                actual_payment_amount = min(wallet_balance, outstanding_amount)

                if actual_payment_amount <= 0:
                    messages.error(request, 'Insufficient wallet balance to process payment.')
                    return redirect('inpatient:admission_detail', pk=admission.id)

                # Process payment from wallet - only deduct the actual amount available
                patient_wallet.debit(
                    amount=actual_payment_amount,
                    description=f'Payment for outstanding admission #{admission.id} (₦{actual_payment_amount:.2f} of ₦{outstanding_amount:.2f})',
                    transaction_type='admission_payment',
                    user=request.user,
                    admission=admission  # Link to admission
                )

                # Update admission payment status with the actual amount deducted
                admission.amount_paid += actual_payment_amount
                admission.save(update_fields=['amount_paid'])

                # Calculate new outstanding amount after payment
                new_outstanding_amount = admission.get_outstanding_admission_cost()

                # Audit log with detailed information
                log_audit_action(
                    request.user,
                    'create',
                    admission,
                    f'Processed partial wallet payment of ₦{actual_payment_amount:.2f} for admission #{admission.id} (Outstanding: ₦{new_outstanding_amount:.2f})'
                )

                # Notification with detailed information
                if admission.attending_doctor:
                    InternalNotification.objects.create(
                        user=admission.attending_doctor,
                        message=f'Partial wallet payment of ₦{actual_payment_amount:.2f} processed for admission #{admission.id}. Remaining outstanding: ₦{new_outstanding_amount:.2f}'
                    )

                # Provide appropriate success message based on whether payment was partial or full
                if actual_payment_amount < outstanding_amount:
                    messages.success(
                        request,
                        f'Partial payment of ₦{actual_payment_amount:.2f} processed from patient wallet. '
                        f'Remaining outstanding: ₦{new_outstanding_amount:.2f}. '
                        f'Wallet balance: ₦{patient_wallet.balance:.2f}.'
                    )
                else:
                    messages.success(
                        request,
                        f'Outstanding payment of ₦{actual_payment_amount:.2f} processed successfully from patient wallet. '
                        f'Admission is now fully paid.'
                    )

                return redirect('inpatient:admission_detail', pk=admission.id)

        except Exception as e:
            messages.error(request, f'Error processing payment: {str(e)}')
            return redirect('inpatient:admission_detail', pk=admission.id)
    
    context = {
        'admission': admission,
        'patient_wallet': patient_wallet,
        'outstanding_amount': outstanding_amount,
        'title': f'Process Outstanding Payment - Admission #{admission.id}'
    }
    
    return render(request, 'inpatient/process_outstanding_admission_payment.html', context)


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


@login_required
@require_POST
@csrf_exempt  # Only for this AJAX endpoint - consider using CSRF token in production
def ajax_process_outstanding_admission_payment(request, admission_id):
    """AJAX endpoint for processing outstanding admission payment from patient wallet"""
    try:
        admission = get_object_or_404(Admission, id=admission_id)

        # Get patient wallet
        patient_wallet = None
        try:
            patient_wallet = PatientWallet.objects.get(patient=admission.patient)
        except PatientWallet.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Patient does not have a wallet.'
            }, status=400)

        # Calculate outstanding amount
        outstanding_amount = admission.get_outstanding_admission_cost()

        if outstanding_amount <= 0:
            return JsonResponse({
                'success': False,
                'message': 'This admission has already been fully paid.'
            }, status=400)

        # Validate wallet balance before processing
        wallet_balance = patient_wallet.balance
        if wallet_balance <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Patient wallet has insufficient balance to process any payment.'
            }, status=400)

        # Check if user has permission to process wallet payments
        user_roles = request.user.roles.values_list('name', flat=True)
        if not any(role in ['billing_staff', 'admin', 'cashier'] for role in user_roles):
            return JsonResponse({
                'success': False,
                'message': 'You do not have permission to process wallet payments.'
            }, status=403)

        # Process payment from wallet
        with transaction.atomic():
            # Check wallet balance before processing
            wallet_balance = patient_wallet.balance

            # Only deduct what's available in the wallet, not exceeding outstanding amount
            actual_payment_amount = min(wallet_balance, outstanding_amount)

            if actual_payment_amount <= 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Insufficient wallet balance to process payment.'
                }, status=400)

            # Process payment from wallet - only deduct the actual amount available
            patient_wallet.debit(
                amount=actual_payment_amount,
                description=f'Payment for outstanding admission #{admission.id} (₦{actual_payment_amount:.2f} of ₦{outstanding_amount:.2f})',
                transaction_type='admission_payment',
                user=request.user,
                admission=admission  # Link to admission
            )

            # Update admission payment status with the actual amount deducted
            admission.amount_paid += actual_payment_amount
            admission.save(update_fields=['amount_paid'])

            # Calculate new outstanding amount after payment
            new_outstanding_amount = admission.get_outstanding_admission_cost()

            # Audit log with detailed information
            log_audit_action(
                request.user,
                'create',
                admission,
                f'Processed partial wallet payment of ₦{actual_payment_amount:.2f} for admission #{admission.id} (Outstanding: ₦{new_outstanding_amount:.2f})'
            )

            # Notification with detailed information
            if admission.attending_doctor:
                InternalNotification.objects.create(
                    user=admission.attending_doctor,
                    message=f'Partial wallet payment of ₦{actual_payment_amount:.2f} processed for admission #{admission.id}. Remaining outstanding: ₦{new_outstanding_amount:.2f}'
                )

        # Get updated wallet balance
        updated_wallet_balance = patient_wallet.balance
        updated_outstanding_amount = admission.get_outstanding_admission_cost()

        # Provide appropriate message based on whether payment was partial or full
        if actual_payment_amount < outstanding_amount:
            message = f'Partial payment of ₦{actual_payment_amount:.2f} processed from patient wallet. Remaining outstanding: ₦{updated_outstanding_amount:.2f}.'
        else:
            message = f'Outstanding payment of ₦{actual_payment_amount:.2f} processed successfully from patient wallet.'

        return JsonResponse({
            'success': True,
            'message': message,
            'data': {
                'wallet_balance': float(updated_wallet_balance),
                'outstanding_amount': float(updated_outstanding_amount),
                'amount_paid': float(actual_payment_amount),
                'admission_id': admission.id,
                'is_partial_payment': actual_payment_amount < outstanding_amount
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error processing payment: {str(e)}'
        }, status=500)