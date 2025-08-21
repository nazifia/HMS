from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from pharmacy.models import ActiveStoreInventory
from django.db import models
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Send low stock and expiry alerts for pharmacy inventory'

    def handle(self, *args, **options):
        # Get low stock items
        low_stock_items = ActiveStoreInventory.objects.filter(
            stock_quantity__lte=models.F('reorder_level')
        ).select_related('medication', 'active_store__dispensary')

        # Get expired items
        expired_items = ActiveStoreInventory.objects.filter(
            expiry_date__lte=timezone.now().date()
        ).select_related('medication', 'active_store__dispensary')

        # Get items expiring within 30 days
        near_expiry_items = ActiveStoreInventory.objects.filter(
            expiry_date__gt=timezone.now().date(),
            expiry_date__lte=timezone.now().date() + timedelta(days=30)
        ).select_related('medication', 'active_store__dispensary')

        # Prepare alert message
        alert_message = "Pharmacy Inventory Alerts

"

        if low_stock_items:
            alert_message += "Low Stock Items:
"
            for item in low_stock_items:
                alert_message += f"- {item.medication.name} ({item.medication.strength}) at {item.active_store.dispensary.name}: {item.stock_quantity} units (Reorder level: {item.reorder_level})
"
            alert_message += "
"

        if expired_items:
            alert_message += "Expired Items:
"
            for item in expired_items:
                alert_message += f"- {item.medication.name} ({item.medication.strength}) at {item.active_store.dispensary.name}: Expired on {item.expiry_date}
"
            alert_message += "
"

        if near_expiry_items:
            alert_message += "Items Expiring Within 30 Days:
"
            for item in near_expiry_items:
                alert_message += f"- {item.medication.name} ({item.medication.strength}) at {item.active_store.dispensary.name}: Expires on {item.expiry_date} ({item.days_until_expiry()} days)
"
            alert_message += "
"

        # Send email if there are alerts
        if low_stock_items or expired_items or near_expiry_items:
            send_mail(
                subject='Pharmacy Inventory Alerts',
                message=alert_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.PHARMACY_MANAGER_EMAIL],
                fail_silently=False,
            )
            self.stdout.write(
                self.style.SUCCESS('Successfully sent pharmacy inventory alerts')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No pharmacy inventory alerts to send')
            )