from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Admission
from billing.models import Invoice, InvoiceItem, Service
from django.utils import timezone

@receiver(post_save, sender=Admission)
def create_admission_invoice(sender, instance, created, **kwargs):
    if created:
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
            total_amount=instance.get_total_cost()
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
