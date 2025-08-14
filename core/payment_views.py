from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from decimal import Decimal
from django.db.models import Q, Sum

from billing.models import Invoice, Payment
from patients.models import PatientWallet, WalletTransaction
from .payment_forms import (
    BasePaymentForm, QuickPaymentForm, BulkPaymentForm, PaymentSearchForm, FlexiblePaymentForm
)


@login_required
@require_http_methods(["GET", "POST"])
def process_payment(request, invoice_id, module_name='general', template_name=None):
    """
    Universal payment processing view that can be used by all modules
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Get or create patient wallet
    patient_wallet, created = PatientWallet.objects.get_or_create(
        patient=invoice.patient,
        defaults={'balance': Decimal('0.00')}
    )
    
    if request.method == 'POST':
        form = BasePaymentForm(
            request.POST,
            invoice=invoice,
            patient_wallet=patient_wallet,
            module_name=module_name
        )
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.invoice = invoice
                    payment.created_by = request.user
                    
                    # Handle payment source
                    payment_source = form.cleaned_data['payment_source']
                    
                    if payment_source == 'patient_wallet':
                        payment.payment_method = 'wallet'
                        # Deduct from wallet using the enhanced debit method
                        patient_wallet.debit(
                            amount=payment.amount,
                            description=f"{module_name} payment for invoice #{invoice.invoice_number}",
                            transaction_type=f"{module_name.lower()}_payment",
                            user=request.user,
                            invoice=invoice,
                            payment_instance=payment
                        )
                    
                    payment.save()
                    
                    # Update invoice amount paid
                    invoice.amount_paid += payment.amount
                    if invoice.amount_paid >= invoice.total_amount:
                        invoice.status = 'paid'
                    elif invoice.amount_paid > 0:
                        invoice.status = 'partially_paid'
                    invoice.save()
                    
                    # Success message with payment details
                    payment_method = payment.get_payment_method_display()
                    source_display = payment_source.replace('_', ' ').title()
                    
                    messages.success(
                        request,
                        f'Payment of ₦{payment.amount:,.2f} processed successfully via {payment_method} '
                        f'({source_display}). Invoice balance: ₦{invoice.get_balance():,.2f}'
                    )
                    
                    # Return JSON response for AJAX requests
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': 'Payment processed successfully',
                            'payment_id': payment.id,
                            'remaining_balance': float(invoice.get_balance()),
                            'is_paid': invoice.is_paid()
                        })
                    
                    # Redirect based on module
                    return redirect_after_payment(invoice, module_name)
                    
            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': str(e)
                    })
    else:
        form = BasePaymentForm(
            invoice=invoice,
            patient_wallet=patient_wallet,
            module_name=module_name,
            initial={
                'payment_date': timezone.now().date(),
                'amount': invoice.get_balance()
            }
        )
    
    # Prepare context
    context = {
        'form': form,
        'invoice': invoice,
        'patient_wallet': patient_wallet,
        'remaining_balance': invoice.get_balance(),
        'payments': Payment.objects.filter(invoice=invoice).order_by('-created_at'),
        'module_name': module_name,
        'title': f'{module_name} Payment Processing',
        'service_info': get_service_info(invoice, module_name),
        'back_url': get_back_url(invoice, module_name),
    }
    
    # Use custom template if provided, otherwise use unified template
    template = template_name or 'payments/unified_payment.html'
    return render(request, template, context)


@login_required
def payment_history(request, invoice_id, module_name='general', template_name=None):
    """
    Universal payment history view that can be used by all modules
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)
    payments = Payment.objects.filter(invoice=invoice).order_by('-created_at')
    
    context = {
        'invoice': invoice,
        'payments': payments,
        'module_name': module_name,
        'title': f'{module_name} Payment History',
        'service_info': get_service_info(invoice, module_name),
        'back_url': get_back_url(invoice, module_name),
        'payment_url': get_payment_url(invoice, module_name),
    }
    
    template = template_name or 'payments/payment_history.html'
    return render(request, template, context)


@login_required
@require_http_methods(["POST"])
def quick_payment(request, invoice_id):
    """
    Quick payment processing for immediate transactions
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    form = QuickPaymentForm(request.POST, max_amount=invoice.get_balance())
    
    if form.is_valid():
        try:
            with transaction.atomic():
                payment = Payment.objects.create(
                    invoice=invoice,
                    amount=form.cleaned_data['amount'],
                    payment_method=form.cleaned_data['payment_method'],
                    payment_date=timezone.now().date(),
                    reference_number=form.cleaned_data.get('reference', ''),
                    created_by=request.user
                )
                
                # Update invoice
                invoice.amount_paid += payment.amount
                if invoice.amount_paid >= invoice.total_amount:
                    invoice.status = 'paid'
                elif invoice.amount_paid > 0:
                    invoice.status = 'partially_paid'
                invoice.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Quick payment of ₦{payment.amount:,.2f} processed successfully',
                    'payment_id': payment.id,
                    'remaining_balance': float(invoice.get_balance()),
                    'is_paid': invoice.is_paid()
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid payment data',
        'errors': form.errors
    })


@login_required
def bulk_payment_processing(request):
    """
    Process multiple payments at once
    """
    if request.method == 'POST':
        invoice_ids = request.POST.getlist('invoice_ids')
        invoices = Invoice.objects.filter(id__in=invoice_ids, status__in=['pending', 'partially_paid'])
        
        form = BulkPaymentForm(request.POST, invoices=invoices)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    payments_created = 0
                    total_amount = Decimal('0.00')
                    
                    for payment_data in form.get_invoice_payments():
                        invoice = payment_data['invoice']
                        amount = payment_data['amount']
                        
                        payment = Payment.objects.create(
                            invoice=invoice,
                            amount=amount,
                            payment_method=form.cleaned_data['payment_method'],
                            payment_date=form.cleaned_data['payment_date'],
                            notes=form.cleaned_data.get('notes', ''),
                            created_by=request.user
                        )
                        
                        # Update invoice
                        invoice.amount_paid += amount
                        if invoice.amount_paid >= invoice.total_amount:
                            invoice.status = 'paid'
                        elif invoice.amount_paid > 0:
                            invoice.status = 'partially_paid'
                        invoice.save()
                        
                        payments_created += 1
                        total_amount += amount
                    
                    messages.success(
                        request,
                        f'Bulk payment completed: {payments_created} payments totaling ₦{total_amount:,.2f} processed successfully'
                    )
                    
                    return redirect('billing:invoice_list')
                    
            except Exception as e:
                messages.error(request, f'Error processing bulk payment: {str(e)}')
    else:
        invoice_ids = request.GET.getlist('invoice_ids')
        invoices = Invoice.objects.filter(id__in=invoice_ids, status__in=['pending', 'partially_paid'])
        form = BulkPaymentForm(invoices=invoices)
    
    context = {
        'form': form,
        'invoices': invoices,
        'title': 'Bulk Payment Processing',
        'total_amount': sum(invoice.get_balance() for invoice in invoices)
    }
    
    return render(request, 'payments/bulk_payment.html', context)


def get_service_info(invoice, module_name):
    """Get service information based on module"""
    service_info = {
        'name': f'{module_name} Service',
        'patient_name': invoice.patient.get_full_name(),
        'patient_id': invoice.patient.patient_id,
        'date': invoice.invoice_date,
        'total_amount': invoice.total_amount,
        'amount_paid': invoice.amount_paid,
        'balance': invoice.get_balance(),
        'status': invoice.get_status_display(),
        'status_color': get_status_color(invoice.status)
    }
    
    # Add module-specific information
    if hasattr(invoice, 'test_request') and invoice.test_request:
        service_info['name'] = f'Laboratory Tests'
        service_info['details'] = f'{invoice.test_request.tests.count()} tests'
    elif hasattr(invoice, 'radiology_order') and invoice.radiology_order:
        service_info['name'] = f'Radiology: {invoice.radiology_order.test.name}'
    elif hasattr(invoice, 'prescription') and invoice.prescription:
        service_info['name'] = f'Pharmacy: Prescription #{invoice.prescription.id}'
    
    return service_info


def get_status_color(status):
    """Get Bootstrap color class for status"""
    colors = {
        'paid': 'success',
        'partially_paid': 'warning',
        'pending': 'danger',
        'overdue': 'danger',
        'cancelled': 'secondary'
    }
    return colors.get(status, 'secondary')


def get_back_url(invoice, module_name):
    """Get appropriate back URL based on module"""
    # This would be customized based on your URL patterns
    return f'/{module_name.lower()}/'


def get_payment_url(invoice, module_name):
    """Get payment URL based on module"""
    # This would be customized based on your URL patterns
    return f'/{module_name.lower()}/payment/{invoice.id}/'


def redirect_after_payment(invoice, module_name):
    """Redirect to appropriate page after payment"""
    # This would be customized based on your URL patterns
    return redirect(f'{module_name.lower()}:detail', id=invoice.id)


@login_required
@require_http_methods(["GET", "POST"])
def flexible_payment_processing(request, invoice_id, module_name='general'):
    """
    Enhanced flexible payment processing with multiple payment methods and negative wallet support
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)

    # Get or create patient wallet
    patient_wallet, created = PatientWallet.objects.get_or_create(
        patient=invoice.patient,
        defaults={'balance': Decimal('0.00')}
    )

    if request.method == 'POST':
        form = FlexiblePaymentForm(
            request.POST,
            invoice=invoice,
            patient_wallet=patient_wallet
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    payment_breakdown = form.get_payment_breakdown()
                    payments_created = []

                    # Process wallet payment if any
                    if payment_breakdown['wallet_amount'] > 0:
                        wallet_payment = Payment.objects.create(
                            invoice=invoice,
                            amount=payment_breakdown['wallet_amount'],
                            payment_method='wallet',
                            payment_date=timezone.now().date(),
                            notes=f"Wallet payment - {form.cleaned_data.get('notes', '')}",
                            created_by=request.user
                        )

                        # Deduct from wallet (allows negative balance)
                        patient_wallet.debit(
                            amount=payment_breakdown['wallet_amount'],
                            description=f"{module_name} payment for invoice #{invoice.invoice_number}",
                            transaction_type=f"{module_name.lower()}_payment",
                            user=request.user,
                            invoice=invoice,
                            payment_instance=wallet_payment
                        )

                        payments_created.append(('Wallet', payment_breakdown['wallet_amount']))

                    # Process cash/card payment if any
                    if payment_breakdown['cash_amount'] > 0:
                        payment_method = form.cleaned_data['payment_method']
                        if payment_method == 'mixed':
                            payment_method = 'cash'  # Default for mixed payments

                        cash_payment = Payment.objects.create(
                            invoice=invoice,
                            amount=payment_breakdown['cash_amount'],
                            payment_method=payment_method,
                            payment_date=timezone.now().date(),
                            reference_number=form.cleaned_data.get('cash_reference', ''),
                            notes=f"Cash/Card payment - {form.cleaned_data.get('notes', '')}",
                            created_by=request.user
                        )

                        payments_created.append((payment_method.title(), payment_breakdown['cash_amount']))

                    # Update invoice status
                    total_paid = sum(amount for _, amount in payments_created)
                    invoice.amount_paid += total_paid

                    if invoice.amount_paid >= invoice.total_amount:
                        invoice.status = 'paid'
                    elif invoice.amount_paid > 0:
                        invoice.status = 'partially_paid'
                    invoice.save()

                    # Create success message
                    payment_details = ', '.join([f'{method}: ₦{amount:,.2f}' for method, amount in payments_created])

                    success_message = f'Payment processed successfully! {payment_details}. '
                    success_message += f'Invoice balance: ₦{invoice.get_balance():,.2f}'

                    if payment_breakdown['has_wallet_warning']:
                        success_message += f' (Wallet balance: ₦{payment_breakdown["new_wallet_balance"]:,.2f})'

                    messages.success(request, success_message)

                    # Return JSON response for AJAX requests
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': 'Payment processed successfully',
                            'payments_created': len(payments_created),
                            'total_paid': float(total_paid),
                            'remaining_balance': float(invoice.get_balance()),
                            'new_wallet_balance': float(patient_wallet.balance),
                            'is_paid': invoice.is_paid()
                        })

                    return redirect_after_payment(invoice, module_name)

            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': str(e)
                    })
    else:
        form = FlexiblePaymentForm(
            invoice=invoice,
            patient_wallet=patient_wallet
        )

    # Prepare context
    context = {
        'form': form,
        'invoice': invoice,
        'patient_wallet': patient_wallet,
        'remaining_balance': invoice.get_balance(),
        'payments': Payment.objects.filter(invoice=invoice).order_by('-created_at'),
        'module_name': module_name,
        'title': f'Flexible Payment Processing - {module_name}',
        'service_info': get_service_info(invoice, module_name),
        'back_url': get_back_url(invoice, module_name),
    }

    return render(request, 'payments/flexible_payment.html', context)
