from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from decimal import Decimal

from billing.models import Invoice, Payment
from billing.fee_utils import create_consultation_fee
from patients.models import PatientWallet
from .payment_forms import ConsultationPaymentForm
from .models import Consultation


def _find_consultation_invoice(consultation):
    """Find the invoice for a consultation via its appointment or the
    patient's latest consultation-fee invoice."""
    if consultation.appointment_id:
        invoice = (
            Invoice.objects.filter(appointment_id=consultation.appointment_id)
            .order_by('-created_at')
            .first()
        )
        if invoice:
            return invoice
    # ponytail: latest consultation invoice for patient; scope per-consultation if patients ever carry several open ones
    return (
        Invoice.objects.filter(
            patient=consultation.patient,
            source_app__in=['consultation', 'appointment'],
        )
        .order_by('-created_at')
        .first()
    )


@login_required
@require_http_methods(["GET", "POST"])
def consultation_payment(request, consultation_id):
    """Handle consultation payment processing with dual payment methods"""
    consultation = get_object_or_404(Consultation, id=consultation_id)

    # Get or create invoice for consultation
    invoice = _find_consultation_invoice(consultation)
    if invoice is None:
        invoice = create_consultation_fee(consultation.patient, user=request.user)
    if invoice is None:
        messages.error(request, "No billable consultation invoice for this patient.")
        return redirect('consultations:consultation_detail', consultation_id=consultation.id)

    # Get or create patient wallet
    patient_wallet, created = PatientWallet.objects.get_or_create(
        patient=consultation.patient,
        defaults={'balance': Decimal('0.00')}
    )
    
    if request.method == 'POST':
        form = ConsultationPaymentForm(
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
                        # Deduct from wallet using the enhanced debit method
                        patient_wallet.debit(
                            amount=payment.amount,
                            description=f"Consultation payment for invoice #{invoice.invoice_number}",
                            transaction_type="consultation_payment",
                            user=request.user,
                            invoice=invoice,
                            payment_instance=payment
                        )
                    
                    payment.save()
                    
                    # Update invoice status if fully paid
                    if invoice.get_balance() <= 0:
                        invoice.status = 'paid'
                        invoice.save()
                    
                    # Log the payment
                    payment_method_display = 'Wallet' if payment_source == 'patient_wallet' else payment.get_payment_method_display()
                    messages.success(
                        request,
                        f"Payment of ₦{payment.amount:.2f} recorded successfully via {payment_method_display}."
                    )
                    
                    return redirect('consultations:consultation_detail', consultation_id=consultation.id)
                    
            except Exception as e:
                messages.error(request, f"Payment processing failed: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ConsultationPaymentForm(
            invoice=invoice,
            patient_wallet=patient_wallet
        )
    
    context = {
        'form': form,
        'consultation': consultation,
        'invoice': invoice,
        'patient_wallet': patient_wallet,
        'remaining_balance': invoice.get_balance(),
        'payments': Payment.objects.filter(invoice=invoice).order_by('-created_at'),
    }
    
    return render(request, 'consultations/payment.html', context)


@login_required
def consultation_payment_history(request, consultation_id):
    """View payment history for a consultation"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    invoice = _find_consultation_invoice(consultation)
    payments = (
        Payment.objects.filter(invoice=invoice).order_by('-created_at')
        if invoice
        else []
    )
    
    context = {
        'consultation': consultation,
        'invoice': invoice,
        'payments': payments,
    }
    
    return render(request, 'consultations/payment_history.html', context)


@login_required
def get_wallet_balance(request, patient_id):
    """AJAX endpoint to get patient wallet balance"""
    try:
        wallet = PatientWallet.objects.get(patient_id=patient_id)
        return JsonResponse({
            'success': True,
            'balance': float(wallet.balance)
        })
    except PatientWallet.DoesNotExist:
        return JsonResponse({
            'success': True,
            'balance': 0.00
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })