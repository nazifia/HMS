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
            # Get the service for admission
            service, _ = Service.objects.get_or_create(
                name="Admission Fee",
                defaults={'price': instance.get_total_cost(), 'category_id': 1} # Assuming category 1 is for inpatient services
            )

            # Create the invoice
            invoice = Invoice.objects.create(
                patient=instance.patient,
                invoice_date=timezone.now().date(),
                due_date=timezone.now().date(),
                status='pending',
                source_app='inpatient',
                created_by=instance.created_by,
                subtotal=instance.get_total_cost(),
                tax_amount=0, # Assuming no tax for now
                total_amount=instance.get_total_cost(),
                admission=instance  # Link invoice to admission
            )

            # Create the invoice item
            InvoiceItem.objects.create(
                invoice=invoice,
                service=service,
                quantity=1,
                unit_price=instance.get_total_cost(),
                tax_percentage=0,
                tax_amount=0,
                total_amount=instance.get_total_cost()
            )

            # Get or create patient wallet
            wallet, created = PatientWallet.objects.get_or_create(
                patient=instance.patient,
                defaults={'balance': 0}
            )

            # Deduct admission fee from wallet (allowing negative balance)
            if instance.get_total_cost() > 0:
                wallet.debit(
                    amount=instance.get_total_cost(),
                    description=f'Admission fee for {instance.patient.get_full_name()}',
                    transaction_type='admission_fee',
                    user=instance.created_by,
                    invoice=invoice
                )
                logger.info(f'Deducted ₦{instance.get_total_cost()} from wallet for admission {instance.id}. New balance: ₦{wallet.balance}')

        except Exception as e:
            logger.error(f'Error processing admission invoice and wallet deduction for admission {instance.id}: {str(e)}')
            # Don't raise the exception to avoid breaking the admission creation process
