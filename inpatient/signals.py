from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Admission
from billing.models import Invoice, InvoiceItem, Service
from patients.models import PatientWallet
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Admission)
def create_admission_invoice_and_deduct_wallet(sender, instance, created, **kwargs):
    if created:
        try:
            # Check if patient is NHIA - NHIA patients are exempt from admission fees
            is_nhia_patient = False
            try:
                is_nhia_patient = (hasattr(instance.patient, 'nhia_info') and
                                 instance.patient.nhia_info and
                                 instance.patient.nhia_info.is_active)
            except:
                # If NHIA app is not available or any error, treat as non-NHIA
                is_nhia_patient = False

            if is_nhia_patient:
                logger.info(f'Patient {instance.patient.get_full_name()} is NHIA - no admission fee charged.')
                return

            admission_cost = instance.get_total_cost()

            if admission_cost <= 0:
                logger.info(f'No admission cost for admission {instance.id} - no invoice created.')
                return

            # Check if admission fee has already been deducted to prevent double deduction
            from patients.models import WalletTransaction
            existing_admission_fee = WalletTransaction.objects.filter(
                wallet__patient=instance.patient,
                transaction_type='admission_fee',
                description__icontains=f'Admission fee for {instance.patient.get_full_name()}'
            ).exists()

            if existing_admission_fee:
                logger.info(f'Admission fee already deducted for patient {instance.patient.get_full_name()} - skipping.')
                return

            # Get the service for admission
            service, _ = Service.objects.get_or_create(
                name="Admission Fee",
                defaults={'price': admission_cost, 'category_id': 1} # Assuming category 1 is for inpatient services
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
                tax_amount=0, # Assuming no tax for now
                total_amount=admission_cost,
                admission=instance  # Link invoice to admission
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

            # Automatically deduct admission fee from patient wallet (even if it goes negative)
            from patients.models import PatientWallet
            from django.db import transaction

            with transaction.atomic():
                # Get or create patient wallet
                wallet, created_wallet = PatientWallet.objects.get_or_create(
                    patient=instance.patient,
                    defaults={'balance': 0}
                )

                if created_wallet:
                    logger.info(f'Created new wallet for patient {instance.patient.get_full_name()}')

                # Deduct admission fee from wallet (allowing negative balance)
                wallet.debit(
                    amount=admission_cost,
                    description=f'Admission fee for {instance.patient.get_full_name()} - {instance.bed.ward.name if instance.bed else "General"}',
                    transaction_type='admission_fee',
                    user=instance.created_by,
                    invoice=invoice
                )

                logger.info(f'Automatically deducted ₦{admission_cost} admission fee from wallet for patient {instance.patient.get_full_name()}. New balance: ₦{wallet.balance}')

                # Update invoice status to paid since wallet was charged
                invoice.status = 'paid'
                invoice.save()

                # Create payment record
                from billing.models import Payment
                Payment.objects.create(
                    invoice=invoice,
                    amount=admission_cost,
                    payment_method='wallet',
                    payment_date=timezone.now().date(),
                    received_by=instance.created_by,
                    notes=f'Automatic wallet deduction for admission fee'
                )

                logger.info(f'Invoice {invoice.id} marked as paid via wallet deduction.')

        except Exception as e:
            logger.error(f'Error processing admission invoice and wallet deduction for admission {instance.id}: {str(e)}')
            # Don't raise the exception to avoid breaking the admission creation process
