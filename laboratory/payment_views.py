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
from core.billing_office_integration import BillingOfficePaymentProcessor


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
        amount = request.POST.get('amount', '0')
        payment_source = request.POST.get('payment_source', 'billing_office')
        payment_method = request.POST.get('payment_method', 'cash')
        transaction_id = request.POST.get('transaction_id', '')
        notes = request.POST.get('notes', '')
        
        # Process payment using billing office integration
        success, message, payment = BillingOfficePaymentProcessor.process_payment(
            request=request,
            invoice=invoice,
            amount=Decimal(amount),
            payment_source=payment_source,
            payment_method=payment_method,
            transaction_id=transaction_id,
            notes=notes,
            module_name='Laboratory'
        )
        
        if success:
            messages.success(request, message)
            
            # Update test request status if fully paid
            if invoice.get_balance() <= 0:
                test_request.status = 'payment_confirmed'
                test_request.save()
            
            return redirect('laboratory:test_request_detail', test_request_id=test_request.id)
        else:
            messages.error(request, message)
    else:
        # Use enhanced context from billing office integration
        context = BillingOfficePaymentProcessor.get_payment_context(
            request, invoice, 'Laboratory'
        )
        
        # Add laboratory-specific context
        context.update({
            'test_request': test_request,
        })
        
        # Create form for initial rendering
        form = LaboratoryPaymentForm(
            invoice=invoice,
            patient_wallet=context['patient_wallet']
        )
        context['form'] = form
    
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