"""
Payment and Admission signals to handle wallet operations and invoice updates.
These signals decouple business logic from model save() methods.
"""
from django.db.models.signals import post_save, pre_save, pre_delete, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.db.models import Sum, F
from decimal import Decimal

from .models import Payment, Invoice
from patients.models import PatientWallet, WalletTransaction
from inpatient.models import Admission


# ==================== Payment Signal Handlers ====================

@receiver(pre_save, sender=Payment)
def capture_payment_original_values(sender, instance, **kwargs):
    """
    Capture original payment values before save for comparison in post_save.
    This is necessary because post_save cannot query for old values (DB is already updated).
    """
    if instance.pk:  # Only for updates, not creates
        try:
            old_instance = Payment.objects.get(pk=instance.pk)
            instance._original_payment_method = old_instance.payment_method
            instance._original_amount = old_instance.amount
        except Payment.DoesNotExist:
            pass


@receiver(post_save, sender=Payment)
def handle_payment_wallet_operations(sender, instance, created, **kwargs):
    """Handle wallet deductions/refunds when payments are created or updated."""
    if instance.payment_method != 'wallet':
        # Check if payment method changed FROM wallet to something else
        if hasattr(instance, '_original_payment_method') and instance._original_payment_method == 'wallet':
            # Refund the original amount
            _refund_wallet(instance, instance._original_amount, f"Payment method changed from wallet to {instance.payment_method}")
        return

    if created:
        # New wallet payment: deduct full amount ONLY if no WalletTransaction already exists
        # This prevents double-deduction when Payment is created as part of another process (e.g., admission)
        if not WalletTransaction.objects.filter(payment=instance).exists():
            _deduct_wallet_for_payment(instance)
    else:
        # Payment updated: check if amount changed
        if hasattr(instance, '_original_amount') and hasattr(instance, '_original_payment_method'):
            original_amount = instance._original_amount
            original_method = instance._original_payment_method

            if original_method != 'wallet':
                # Changed from non-wallet TO wallet: deduct full amount
                _deduct_wallet_for_payment(instance)
            elif instance.amount != original_amount:
                # Still wallet payment, amount changed: adjust by difference
                difference = instance.amount - original_amount
                if difference > 0:
                    # Increase: deduct additional amount
                    _adjust_wallet_for_payment(instance, amount=abs(difference), is_increase=True)
                elif difference < 0:
                    # Decrease: refund the difference
                    _adjust_wallet_for_payment(instance, amount=abs(difference), is_increase=False)


@receiver(pre_delete, sender=Payment)
def handle_payment_deletion_wallet_refund(sender, instance, **kwargs):
    """Refund wallet before payment is deleted if it was a wallet payment."""
    if instance.payment_method == 'wallet':
        _refund_wallet(instance, instance.amount, f"Reversal: Payment {instance.pk} deleted")


@receiver(post_save, sender=Payment)
def update_invoice_after_payment_save(sender, instance, created, **kwargs):
    """Update invoice's amount_paid and status whenever a payment is saved."""
    invoice = instance.invoice

    # Recalculate invoice total from ALL payments (not just wallet)
    total_paid = invoice.payments.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    # Update only if changed to avoid unnecessary saves
    if invoice.amount_paid != total_paid:
        invoice.amount_paid = total_paid
        # Let Invoice.save() handle status calculation
        invoice.save(update_fields=['amount_paid', 'status'])


@receiver(post_delete, sender=Payment)
def update_invoice_after_payment_delete(sender, instance, **kwargs):
    """Update invoice's amount_paid and status after a payment is deleted."""
    invoice = instance.invoice

    # Recalculate invoice total from remaining payments
    total_paid = invoice.payments.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    # Update only if changed to avoid unnecessary saves
    if invoice.amount_paid != total_paid:
        invoice.amount_paid = total_paid
        # Reset status to pending if no payments, otherwise let Invoice.save() handle it
        if total_paid == Decimal('0.00') and invoice.status not in ['draft', 'cancelled']:
            invoice.status = 'pending'
        invoice.save(update_fields=['amount_paid', 'status'])


# ==================== Admission Signal Handlers ====================

@receiver(pre_save, sender=Admission)
def capture_admission_original_values(sender, instance, **kwargs):
    """
    Capture original admission values before save for comparison in post_save.
    This is necessary because post_save cannot query for old values (DB is already updated).
    """
    if instance.pk:  # Only for updates, not creates
        try:
            old_instance = Admission.objects.get(pk=instance.pk)
            instance._original_billed_amount = old_instance.billed_amount
            instance._original_get_total_cost = old_instance.get_total_cost()
        except Admission.DoesNotExist:
            pass


@receiver(post_save, sender=Admission)
def handle_admission_wallet_debit(sender, instance, created, **kwargs):
    """Automatically deduct admission fees from patient's wallet when created or updated."""
    # Only process admitted patients with a bed
    if instance.status != 'admitted' or not instance.bed:
        return

    # Calculate admission cost
    admission_cost = instance.get_total_cost()
    if admission_cost <= 0:
        return  # NHIA patients or zero cost

    try:
        patient_wallet = PatientWallet.objects.get(patient=instance.patient)

        if created:
            # New admission: charge the full amount
            patient_wallet.debit(
                amount=admission_cost,
                description=f"Admission fees for {instance.admission_date.strftime('%Y-%m-%d')}",
                transaction_type="admission_fee",
                user=instance.created_by,
                admission=instance
            )
            # Update admission billed_amount to track what was charged
            # Use update_fields to avoid triggering another signal unnecessarily
            Admission.objects.filter(pk=instance.pk).update(billed_amount=admission_cost)
        else:
            # Existing admission: check if cost increased
            if hasattr(instance, '_original_get_total_cost'):
                old_cost = instance._original_get_total_cost

                # If the cost increased, charge the difference
                if admission_cost > old_cost:
                    additional_charge = admission_cost - old_cost
                    patient_wallet.debit(
                        amount=additional_charge,
                        description=f"Additional admission charges (duration extended)",
                        transaction_type="daily_admission_charge",
                        user=instance.created_by,
                        admission=instance
                    )
                    # Update billed_amount to reflect new total
                    Admission.objects.filter(pk=instance.pk).update(billed_amount=admission_cost)

    except PatientWallet.DoesNotExist:
        pass  # No wallet, cannot process
    except Exception:
        pass  # Safe fallback


# ==================== Invoice Signal Handlers ====================

@receiver(post_save, sender=Invoice)
def update_invoice_status_based_on_payments(sender, instance, **kwargs):
    """Ensure invoice status is consistent with amount_paid vs total_amount."""
    # Calculate expected status
    if instance.total_amount > 0:
        if instance.amount_paid >= instance.total_amount:
            expected_status = 'paid'
        elif instance.amount_paid > 0:
            expected_status = 'partially_paid'
        else:
            # No payment yet - keep current status unless it's already paid/partially_paid
            # This preserves manually set 'draft' or 'cancelled'
            return
    else:
        # Zero amount invoices - keep current status
        return

    # Update if status doesn't match expected
    if instance.status != expected_status:
        instance.status = expected_status
        # Save without triggering another signal (avoid recursion)
        Invoice.objects.filter(pk=instance.pk).update(status=expected_status)


# ==================== Wallet Transaction Signal Handlers ====================

# Note: Wallet balance is already updated by the PatientWallet.debit() and credit()
# methods, so we don't need to update it again here. This section is reserved for
# any additional side effects that should happen after a WalletTransaction is created.


# ==================== Helper Functions ====================

def _deduct_wallet_for_payment(payment, amount=None, description=None):
    """Deduct payment amount from patient's wallet."""
    amount = amount or payment.amount
    try:
        patient_wallet = PatientWallet.objects.get(patient=payment.invoice.patient)
        patient_wallet.debit(
            amount=amount,
            description=description or f"Payment for Invoice #{payment.invoice.invoice_number} via Wallet",
            transaction_type="payment",
            user=payment.received_by,
            invoice=payment.invoice,
            payment_instance=payment
        )
    except PatientWallet.DoesNotExist:
        pass


def _refund_wallet(payment, amount, description=None):
    """Refund an amount back to the wallet."""
    try:
        patient_wallet = PatientWallet.objects.get(patient=payment.invoice.patient)
        patient_wallet.credit(
            amount=amount,
            description=description or f"Refund for Payment {payment.pk}",
            transaction_type='refund',
            user=payment.received_by,
            invoice=payment.invoice,
            payment_instance=payment
        )
    except PatientWallet.DoesNotExist:
        pass


def _adjust_wallet_for_payment(payment, amount, is_increase):
    """Adjust wallet balance for payment amount changes (uses 'adjustment' transaction type)."""
    try:
        patient_wallet = PatientWallet.objects.get(patient=payment.invoice.patient)
        if is_increase:
            patient_wallet.debit(
                amount=amount,
                description=f"Increased payment amount by {amount}",
                transaction_type='adjustment',
                user=payment.received_by,
                invoice=payment.invoice,
                payment_instance=payment
            )
        else:
            patient_wallet.credit(
                amount=amount,
                description=f"Decreased payment amount by {amount}",
                transaction_type='adjustment',
                user=payment.received_by,
                invoice=payment.invoice,
                payment_instance=payment
            )
    except PatientWallet.DoesNotExist:
        pass
