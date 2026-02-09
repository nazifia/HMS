from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Admission
from billing.models import Invoice, InvoiceItem, Service
from patients.models import PatientWallet, WalletTransaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Admission)
def create_admission_invoice_and_deduct_wallet(sender, instance, created, **kwargs):
    """
    When an admission is created (for non-NHIA patients), automatically:
    1. Create an invoice for the admission fee
    2. Create a wallet payment (which triggers billing signals to deduct from wallet)
    3. Update admission billed_amount if wallet deduction succeeds
    """
    if created:
        try:
            # Check if patient is NHIA - NHIA patients are exempt from admission fees
            if instance.patient.is_nhia_patient():
                logger.info(f'Patient {instance.patient.get_full_name()} is NHIA - no admission fee charged.')
                return

            admission_cost = instance.get_total_cost()

            if admission_cost <= 0:
                logger.info(f'No admission cost for admission {instance.id} - no invoice created.')
                return

            # Check if admission fee has already been processed to prevent double deduction
            existing_fee = WalletTransaction.objects.filter(
                patient_wallet__patient=instance.patient,
                transaction_type='admission_fee',
                admission=instance
            ).exists()

            if existing_fee:
                logger.info(f'Admission fee already deducted for admission {instance.id} - skipping.')
                return

            # Get or create service for admission
            service, _ = Service.objects.get_or_create(
                name="Admission Fee",
                defaults={'price': admission_cost, 'category_id': 1}
            )

            # Create the invoice
            invoice = Invoice.objects.create(
                patient=instance.patient,
                invoice_date=timezone.now().date(),
                due_date=timezone.now().date(),
                status='pending',
                source_app='inpatient',
                created_by=instance.created_by,
                subtotal=admission_cost,
                tax_amount=0,
                total_amount=admission_cost,
                admission=instance
            )

            # Create the invoice item
            InvoiceItem.objects.create(
                invoice=invoice,
                service=service,
                quantity=1,
                unit_price=admission_cost,
                tax_percentage=0,
                tax_amount=0,
                total_amount=admission_cost
            )

            # Create payment record (wallet) - this will trigger billing signals.
            # The billing signal will attempt to deduct from wallet. We set a flag
            # to indicate that this payment is part of admission processing.
            from billing.models import Payment
            payment = Payment.objects.create(
                invoice=invoice,
                amount=admission_cost,
                payment_method='wallet',
                payment_date=timezone.now().date(),
                received_by=instance.created_by,
                notes=f'Automatic wallet deduction for admission fee'
            )

            logger.info(f'Payment {payment.id} created for admission fee. Billing signals will handle wallet deduction.')

            # Check if wallet transaction was created (wallet deduction succeeded)
            try:
                wt = WalletTransaction.objects.get(payment=payment)
                # Success: wallet deduction succeeded
                Admission.objects.filter(pk=instance.pk).update(billed_amount=admission_cost)
                logger.info(f'Admission fee ₦{admission_cost} processed via wallet. New admission billed_amount: ₦{admission_cost}')
            except WalletTransaction.DoesNotExist:
                # Failed: wallet deduction didn't happen (maybe no wallet or insufficient balance)
                # Invoice remains pending, billed_amount stays 0
                logger.warning(f'Wallet deduction failed for admission {instance.id}. Invoice {invoice.id} remains unpaid.')

        except ValueError as e:
            logger.warning(f'Validation error in wallet deduction for admission {instance.id}: {str(e)}')
        except Exception as e:
            logger.error(
                f'Unexpected error processing admission invoice and wallet deduction for admission {instance.id}: {str(e)}',
                exc_info=True
            )
