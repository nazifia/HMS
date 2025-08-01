from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from decimal import Decimal

from billing.models import Invoice, Payment
from patients.models import PatientWallet
from .payment_forms import RadiologyPaymentForm
from .models import RadiologyOrder


@login_required
@require_http_methods(["GET", "POST"])
def radiology_payment(request, order_id):
    """Handle radiology test payment processing with dual payment methods"""
    radiology_order = get_object_or_404(RadiologyOrder, id=order_id)
    
    # Get the associated invoice
    try:
        invoice = radiology_order.invoice
    except AttributeError:
        messages.error(request, "No invoice found for this radiology order.")
        return redirect('radiology:order_detail', order_id=radiology_order.id)
    
    # Get or create patient wallet
    patient_wallet, created = PatientWallet.objects.get_or_create(
        patient=radiology_order.patient,
        defaults={'balance': Decimal('0.00')}
    )
    
    if request.method == 'POST':
        form = RadiologyPaymentForm(
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
                    
                    # Update invoice and radiology order status if fully paid
                    if invoice.get_balance() <= 0:
                        invoice.status = 'paid'
                        invoice.save()
                        radiology_order.status = 'payment_confirmed'
                        radiology_order.save()
                    
                    # Log the payment
                    payment_method_display = 'Wallet' if payment_source == 'patient_wallet' else payment.get_payment_method_display()
                    messages.success(
                        request,
                        f"Payment of ₦{payment.amount:.2f} recorded successfully via {payment_method_display}."
                    )
                    
                    return redirect('radiology:order_detail', order_id=radiology_order.id)
                    
            except Exception as e:
                messages.error(request, f"Payment processing failed: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RadiologyPaymentForm(
            invoice=invoice,
            patient_wallet=patient_wallet
        )
    
    context = {
        'form': form,
        'radiology_order': radiology_order,
        'invoice': invoice,
        'patient_wallet': patient_wallet,
        'remaining_balance': invoice.get_balance(),
        'payments': Payment.objects.filter(invoice=invoice).order_by('-created_at'),
    }
    
    return render(request, 'radiology/payment.html', context)


@login_required
def radiology_payment_history(request, order_id):
    """View payment history for a radiology order"""
    radiology_order = get_object_or_404(RadiologyOrder, id=order_id)
    
    try:
        invoice = radiology_order.invoice
        payments = Payment.objects.filter(invoice=invoice).order_by('-created_at')
    except AttributeError:
        invoice = None
        payments = []
    
    context = {
        'radiology_order': radiology_order,
        'invoice': invoice,
        'payments': payments,
    }
    
    return render(request, 'radiology/payment_history.html', context)


@login_required
def confirm_radiology_payment(request, order_id):
    """Confirm radiology payment and update order status"""
    radiology_order = get_object_or_404(RadiologyOrder, id=order_id)
    
    try:
        invoice = radiology_order.invoice
        if invoice.get_balance() <= 0:
            radiology_order.status = 'payment_confirmed'
            radiology_order.save()
            messages.success(request, "Radiology test payment confirmed. Test can now proceed.")
        else:
            messages.warning(request, "Payment is not complete. Please complete payment before confirming.")
    except AttributeError:
        messages.error(request, "No invoice found for this radiology order.")
    
    return redirect('radiology:order_detail', order_id=radiology_order.id)