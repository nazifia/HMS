from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone

from pharmacy.models import ActiveStoreInventory
from saas.models import Hospital


class Command(BaseCommand):
    help = 'Send low stock and expiry alerts for pharmacy inventory'

    def handle(self, *args, **options):
        # One email per hospital: a management command runs with no current
        # tenant, so `objects` would return (and mail out) every tenant's stock
        # in one message. all_objects + an explicit hospital filter keeps each
        # hospital's inventory in its own email.
        for hospital in Hospital.objects.filter(is_active=True):
            message = self.build_message(hospital)
            if not message:
                continue
            recipient = hospital.email or getattr(settings, 'PHARMACY_ALERT_EMAIL', '')
            if not recipient:
                self.stdout.write(
                    self.style.WARNING(f'{hospital}: alerts skipped, no email on file')
                )
                continue
            send_mail(
                subject=f'Pharmacy Inventory Alerts - {hospital.name}',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'{hospital}: alerts sent to {recipient}'))

    def build_message(self, hospital):
        """Alert text for one hospital, or '' when it has nothing to report."""
        today = timezone.now().date()
        stock = ActiveStoreInventory.all_objects.filter(
            hospital=hospital
        ).select_related('medication', 'active_store__dispensary')

        sections = (
            (
                'Low Stock Items',
                stock.filter(stock_quantity__lte=models.F('reorder_level')),
                lambda i: f'{i.stock_quantity} units (Reorder level: {i.reorder_level})',
            ),
            (
                'Expired Items',
                stock.filter(expiry_date__lte=today),
                lambda i: f'Expired on {i.expiry_date}',
            ),
            (
                'Items Expiring Within 90 Days',
                stock.filter(expiry_date__gt=today, expiry_date__lte=today + timedelta(days=90)),
                lambda i: f'Expires on {i.expiry_date} ({i.days_until_expiry()} days)',
            ),
        )

        body = ''
        for title, items, detail in sections:
            items = list(items)
            if not items:
                continue
            body += f'{title}:\n'
            for item in items:
                body += (
                    f'- {item.medication.name} ({item.medication.strength}) '
                    f'at {item.active_store.dispensary.name}: {detail(item)}\n'
                )
            body += '\n'
        if not body:
            return ''
        return f'Pharmacy Inventory Alerts - {hospital.name}\n\n{body}'
