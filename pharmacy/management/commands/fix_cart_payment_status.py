"""
Management command to fix cart payment status.
Updates carts with paid invoices to 'paid' status.

Usage:
    python manage.py fix_cart_payment_status
"""

from django.core.management.base import BaseCommand
from pharmacy.cart_models import PrescriptionCart


class Command(BaseCommand):
    help = 'Fix cart payment status - update carts with paid invoices to paid status'

    def handle(self, *args, **options):
        self.stdout.write('Checking for carts with paid invoices...')
        
        # Find carts with status 'invoiced' but invoice is paid
        carts_to_fix = PrescriptionCart.objects.filter(
            status='invoiced',
            invoice__status='paid'
        )
        
        count = carts_to_fix.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No carts need fixing. All carts are up to date!'))
            return
        
        self.stdout.write(f'Found {count} cart(s) with paid invoices but invoiced status')
        
        # Update cart statuses
        updated = 0
        for cart in carts_to_fix:
            cart.status = 'paid'
            cart.save(update_fields=['status'])
            updated += 1
            self.stdout.write(f'  ✓ Updated Cart #{cart.id} to paid status')
        
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully updated {updated} cart(s)!'))

