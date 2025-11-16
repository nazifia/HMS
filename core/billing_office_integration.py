"""
Billing Office Integration Utilities for HMS

This module provides centralized billing office payment processing functionality
that can be used across all modules (pharmacy, laboratory, radiology, theatre, etc.)

The main purpose is to allow billing office staff to process payments on behalf
of patients, while maintaining the existing patient wallet functionality.
"""

from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from typing import Dict, Tuple, Optional, Any

from billing.models import Invoice, Payment
from patients.models import PatientWallet, WalletTransaction
from core.audit_utils import log_audit_action
from core.models import InternalNotification
from django import forms


class BillingOfficePaymentProcessor:
    """
    Centralized payment processor for billing office payments.
    
    This class provides a unified interface for processing payments from the billing office
    while preserving existing wallet payment functionality.
    """
    
    PAYMENT_SOURCES = {
        'billing_office': 'Billing Office Payment',
        'patient_wallet': 'Patient Wallet Payment',
        'department': 'Department Collection',
        'insurance': 'Insurance Payment',
        'corporate': 'Corporate Payment'
    }
    
    @staticmethod
    def process_payment(
        request,
        invoice: Invoice,
        amount: Decimal,
        payment_source: str = 'billing_office',
        payment_method: str = 'cash',
        transaction_id: str = '',
        notes: str = '',
        module_name: str = 'General',
        **kwargs
    ) -> Tuple[bool, str, Optional[Payment]]:
        """
        Process payment with billing office integration.
        
        Args:
            request: Django request object
            invoice: Invoice to pay
            amount: Payment amount
            payment_source: Source of payment ('billing_office', 'patient_wallet', etc.)
            payment_method: Payment method ('cash', 'card', 'wallet', etc.)
            transaction_id: Optional transaction ID/reference
            notes: Optional notes
            module_name: Name of the module for logging
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (success: bool, message: str, payment: Optional[Payment])
        """
        
        try:
            with transaction.atomic():
                # Validate amount
                if amount <= 0:
                    return False, "Payment amount must be greater than zero.", None
                
                # Check against remaining balance
                remaining_balance = invoice.get_balance()
                if amount > remaining_balance:
                    return False, f"Payment amount (₦{amount:,.2f}) exceeds remaining balance (₦{remaining_balance:,.2f}).", None
                
                # Get or create patient wallet
                patient_wallet = BillingOfficePaymentProcessor._get_or_create_wallet(invoice.patient)
                
                # Force wallet method for wallet payments
                if payment_source == 'patient_wallet':
                    payment_method = 'wallet'
                
                # Create payment record
                payment = Payment.objects.create(
                    invoice=invoice,
                    amount=amount,
                    payment_method=payment_method,
                    payment_date=timezone.now().date(),
                    transaction_id=transaction_id,
                    notes=f"{notes} ({BillingOfficePaymentProcessor.PAYMENT_SOURCES.get(payment_source, payment_source)})",
                    received_by=request.user
                )
                
                # Handle wallet payment
                if payment_source == 'patient_wallet':
                    try:
                        # Use wallet's debit method to ensure proper transaction creation
                        patient_wallet.debit(
                            amount=amount,
                            description=f'{module_name} payment for invoice #{invoice.invoice_number}',
                            transaction_type=f'{module_name.lower()}_payment',
                            user=request.user,
                            invoice=invoice,
                            payment_instance=payment
                        )
                    except ValueError as e:
                        return False, f"Wallet payment failed: {str(e)}", None
                
                # Update invoice
                invoice.amount_paid += amount
                if invoice.amount_paid >= invoice.total_amount:
                    invoice.status = 'paid'
                    # Mark that this is a manual payment processed by billing staff
                    invoice._manual_payment_processed = True
                elif invoice.amount_paid > 0:
                    invoice.status = 'partially_paid'
                
                invoice.save()
                
                # Log audit action
                log_audit_action(
                    request.user,
                    'create',
                    payment,
                    f'Billing office processed {payment_source} payment of ₦{amount:.2f} for invoice #{invoice.invoice_number}'
                )
                
                # Send notification to relevant staff
                BillingOfficePaymentProcessor._send_notifications(
                    invoice, payment, payment_source, amount, module_name
                )
                
                success_message = f'✅ Payment of ₦{amount:.2f} processed successfully via {BillingOfficePaymentProcessor.PAYMENT_SOURCES.get(payment_source, payment_source)}.'
                
                return True, success_message, payment
                
        except Exception as e:
            return False, f"Error processing payment: {str(e)}", None
    
    @staticmethod
    def _get_or_create_wallet(patient) -> PatientWallet:
        """Get or create patient wallet"""
        wallet, created = PatientWallet.objects.get_or_create(
            patient=patient,
            defaults={'balance': Decimal('0.00')}
        )
        return wallet
    
    @staticmethod
    def _send_notifications(invoice: Invoice, payment: Payment, payment_source: str, amount: Decimal, module_name: str):
        """Send notifications to relevant staff"""
        try:
            # Try to notify the invoice creator
            if invoice.created_by:
                InternalNotification.objects.create(
                    user=invoice.created_by,
                    message=f'Billing office processed payment of ₦{amount:.2f} for invoice #{invoice.invoice_number} via {payment_source}'
                )
            
            # Try to notify module-specific staff
            if hasattr(invoice, 'prescription') and invoice.prescription and invoice.prescription.doctor:
                InternalNotification.objects.create(
                    user=invoice.prescription.doctor,
                    message=f'Billing office processed payment of ₦{amount:.2f} for prescription #{invoice.prescription.id} via {payment_source}'
                )
            elif hasattr(invoice, 'test_request') and invoice.test_request:
                # Notify lab staff if available
                pass
            elif hasattr(invoice, 'admission') and invoice.admission:
                # Notify attending doctor if available
                if hasattr(invoice.admission, 'attending_doctor') and invoice.admission.attending_doctor:
                    InternalNotification.objects.create(
                        user=invoice.admission.attending_doctor,
                        message=f'Billing office processed payment of ₦{amount:.2f} for admission #{invoice.admission.id} via {payment_source}'
                    )
                    
        except Exception as e:
            # Don't fail the payment if notification fails
            pass
    
    @staticmethod
    def get_payment_context(request, invoice, module_name='General', **kwargs):
        """
        Get context for payment form rendering.
        
        Args:
            request: Django request object
            invoice: Invoice object
            module_name: Name of the module
            **kwargs: Additional context parameters
            
        Returns:
            Dictionary with context for template rendering
        """
        
        # Get or create patient wallet
        patient_wallet = BillingOfficePaymentProcessor._get_or_create_wallet(invoice.patient)
        
        # Calculate remaining amount
        remaining_amount = invoice.get_balance()
        
        # Get existing payments
        payments = invoice.payments.all().order_by('-payment_date')
        
        context = {
            'invoice': invoice,
            'patient_wallet': patient_wallet,
            'remaining_amount': remaining_amount,
            'payments': payments,
            'module_name': module_name,
            'title': f'{module_name} Payment - Invoice #{invoice.invoice_number}',
            'payment_sources': BillingOfficePaymentProcessor.PAYMENT_SOURCES,
            # Additional module-specific context
            **kwargs
        }
        
        return context
    
    @staticmethod
    def validate_payment_data(invoice: Invoice, amount: Decimal, payment_source: str, patient_wallet: Optional[PatientWallet] = None) -> Tuple[bool, str]:
        """
        Validate payment data before processing.
        
        Args:
            invoice: Invoice to validate against
            amount: Payment amount
            payment_source: Source of payment
            patient_wallet: Patient wallet (if available)
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        
        # Validate amount
        if amount <= 0:
            return False, "Payment amount must be greater than zero."
        
        # Check remaining balance
        remaining_balance = invoice.get_balance()
        if amount > remaining_balance:
            return False, f"Payment amount (₦{amount:,.2f}) exceeds remaining balance (₦{remaining_balance:,.2f})."
        
        # Validate wallet payment if applicable
        if payment_source == 'patient_wallet':
            if not patient_wallet:
                return False, "Patient wallet not found."
            
            # Note: We allow negative balances, so no validation needed here
        
        return True, ""


class BillingOfficeFormMixin:
    """
    Mixin for payment forms to add billing office functionality.
    """
    
    PAYMENT_SOURCE_CHOICES = [
        ('billing_office', 'Billing Office'),
        ('patient_wallet', 'Patient Wallet'),
        ('department', 'Department Collection'),
        ('insurance', 'Insurance Payment'),
        ('corporate', 'Corporate Payment'),
    ]
    
    def __init__(self, *args, **kwargs):
        self.invoice = kwargs.pop('invoice', None)
        self.patient_wallet = kwargs.pop('patient_wallet', None)
        super().__init__(*args, **kwargs)
        
        # Add payment_source field if not already present
        if 'payment_source' not in self.fields:
            self.fields['payment_source'] = forms.ChoiceField(
                choices=self.PAYMENT_SOURCE_CHOICES,
                widget=forms.Select(attrs={'class': 'form-select'}),
                initial='billing_office',
                help_text="Select where the payment is being processed from"
            )
        
        # Set payment method choices based on payment source
        self._update_payment_method_choices()
    
    def _update_payment_method_choices(self):
        """Update payment method choices based on payment source"""
        if hasattr(self, 'cleaned_data') and self.cleaned_data.get('payment_source') == 'patient_wallet':
            # For wallet payments, only allow wallet method
            if 'payment_method' in self.fields:
                self.fields['payment_method'].choices = [('wallet', 'Wallet')]
        else:
            # For other sources, allow standard payment methods
            if 'payment_method' in self.fields:
                self.fields['payment_method'].choices = [
                    ('cash', 'Cash'),
                    ('card', 'Card/POS'),
                    ('bank_transfer', 'Bank Transfer'),
                    ('cheque', 'Cheque'),
                ]
    
    def clean(self):
        cleaned_data = super().clean()
        payment_source = cleaned_data.get('payment_source')
        payment_method = cleaned_data.get('payment_method')
        amount = cleaned_data.get('amount')
        
        # Force wallet payment method for wallet payments
        if payment_source == 'patient_wallet':
            cleaned_data['payment_method'] = 'wallet'
        
        # Validate payment data
        if self.invoice and amount:
            is_valid, error_message = BillingOfficePaymentProcessor.validate_payment_data(
                self.invoice, amount, payment_source, self.patient_wallet
            )
            if not is_valid:
                raise forms.ValidationError(error_message)
        
        return cleaned_data


def create_billing_office_payment_view(module_name, template_name=None, success_url_name=None):
    """
    Factory function to create billing office payment views for different modules.
    
    Args:
        module_name: Name of the module (e.g., 'pharmacy', 'laboratory', 'radiology')
        template_name: Optional custom template name
        success_url_name: Optional URL name for success redirect
        
    Returns:
        View function for handling billing office payments
    """
    
    def billing_office_payment_view(request, invoice_id):
        """Generic billing office payment view"""
        from django.shortcuts import get_object_or_404, redirect, render
        from django.contrib.auth.decorators import login_required
        from django.http import JsonResponse
        
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Get context for rendering
        context = BillingOfficePaymentProcessor.get_payment_context(
            request, invoice, module_name
        )
        
        if request.method == 'POST':
            amount = Decimal(request.POST.get('amount', '0'))
            payment_source = request.POST.get('payment_source', 'billing_office')
            payment_method = request.POST.get('payment_method', 'cash')
            transaction_id = request.POST.get('transaction_id', '')
            notes = request.POST.get('notes', '')
            
            # Process payment
            success, message, payment = BillingOfficePaymentProcessor.process_payment(
                request=request,
                invoice=invoice,
                amount=amount,
                payment_source=payment_source,
                payment_method=payment_method,
                transaction_id=transaction_id,
                notes=notes,
                module_name=module_name
            )
            
            if success:
                messages.success(request, message)
                
                # Handle AJAX requests
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': message,
                        'payment_id': payment.id,
                        'remaining_balance': float(invoice.get_balance()),
                        'is_paid': invoice.is_paid()
                    })
                
                # Redirect to success URL
                if success_url_name:
                    return redirect(success_url_name, invoice_id=invoice.id)
                else:
                    return redirect('billing:detail', invoice_id=invoice.id)
            else:
                messages.error(request, message)
                
                # Handle AJAX requests
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': message
                    })
        
        # Use custom template or default
        template = template_name or 'payments/billing_office_payment.html'
        return render(request, template, context)
    
    return login_required(billing_office_payment_view)
