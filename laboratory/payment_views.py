from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from decimal import Decimal

from billing.models import Invoice, Payment
from patients.models import PatientWallet
from .payment_forms import LaboratoryPaymentForm
from .models import TestRequest


@login_required
@require_http_methods(["GET", "POST"])
def laboratory_payment(request, test_request_id):
    """Handle laboratory test payment processing with dual payment methods"""
    test_request = get_object_or_404(TestRequest, id=test_request_id)

    # Check if patient is NHIA - NHIA patients are exempt from lab test payments
    if test_request.patient.is_nhia_patient():
        messages.info(
            request,
            f'Patient {test_request.patient.get_full_name()} is an NHIA patient and is exempt from laboratory test payments. '
            'No payment is required.'
        )
        return redirect('laboratory:test_request_detail', test_request_id=test_request.id)

    # Get the associated invoice
    try:
        invoice = test_request.invoice
    except AttributeError:
        messages.error(request, "No invoice found for this test request.")
        return redirect('laboratory:test_request_detail', test_request_id=test_request.id)
    
    # Get or create patient wallet
    patient_wallet, created = PatientWallet.objects.get_or_create(
        patient=test_request.patient,
        defaults={'balance': Decimal('0.00')}
    )
    
    if request.method == 'POST':
        form = LaboratoryPaymentForm(
            request.POST,
            invoice=invoice,
            patient_wallet=patient_wallet
        )
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.invoice = invoice
                    payment.created_by = request.user
                    
                    # Set payment method based on payment source
                    payment_source = form.cleaned_data['payment_source']
                    if payment_source == 'patient_wallet':
                        payment.payment_method = 'wallet'
                        # Deduct from wallet
                        patient_wallet.balance -= payment.amount
                        patient_wallet.save()
                    
                    payment.save()
                    
                    # Update invoice and test request status if fully paid
                    if invoice.get_balance() <= 0:
                        invoice.status = 'paid'
                        invoice.save()
                        test_request.status = 'payment_confirmed'
                        test_request.save()
                    
                    # Log the payment
                    payment_method_display = 'Wallet' if payment_source == 'patient_wallet' else payment.get_payment_method_display()
                    messages.success(
                        request,
                        f"Payment of ₦{payment.amount:.2f} recorded successfully via {payment_method_display}."
                    )
                    
                    return redirect('laboratory:test_request_detail', test_request_id=test_request.id)
                    
            except Exception as e:
                messages.error(request, f"Payment processing failed: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LaboratoryPaymentForm(
            invoice=invoice,
            patient_wallet=patient_wallet
        )
    
    context = {
        'form': form,
        'test_request': test_request,
        'invoice': invoice,
        'patient_wallet': patient_wallet,
        'remaining_balance': invoice.get_balance(),
        'payments': Payment.objects.filter(invoice=invoice).order_by('-created_at'),
    }
    
    return render(request, 'laboratory/payment.html', context)


@login_required
def laboratory_payment_history(request, test_request_id):
    """View payment history for a laboratory test request"""
    test_request = get_object_or_404(TestRequest, id=test_request_id)
    
    try:
        invoice = test_request.invoice
        payments = Payment.objects.filter(invoice=invoice).order_by('-created_at')
    except AttributeError:
        invoice = None
        payments = []
    
    context = {
        'test_request': test_request,
        'invoice': invoice,
        'payments': payments,
    }
    
    return render(request, 'laboratory/payment_history.html', context)


@login_required
def confirm_lab_payment(request, test_request_id):
    """Confirm laboratory payment and update test request status"""
    test_request = get_object_or_404(TestRequest, id=test_request_id)
    
    try:
        invoice = test_request.invoice
        if invoice.get_balance() <= 0:
            test_request.status = 'payment_confirmed'
            test_request.save()
            messages.success(request, "Laboratory test payment confirmed. Test can now proceed.")
        else:
            messages.warning(request, "Payment is not complete. Please complete payment before confirming.")
    except AttributeError:
        messages.error(request, "No invoice found for this test request.")
    
    return redirect('laboratory:test_request_detail', test_request_id=test_request.id)