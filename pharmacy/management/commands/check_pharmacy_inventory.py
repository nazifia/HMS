from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import F
from pharmacy.models import Medication, MedicationInventory, BulkStoreInventory
from datetime import timedelta

class Command(BaseCommand):
    help = 'Check pharmacy inventory for expiring medications and low stock items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to check for expiring medications (default: 30)'
        )
        parser.add_argument(
            '--low-stock',
            action='store_true',
            help='Check for low stock items'
        )
        parser.add_argument(
            '--expiring',
            action='store_true',
            help='Check for expiring medications'
        )

    def handle(self, *args, **options):
        days = options['days']
        check_low_stock = options['low_stock']
        check_expiring = options['expiring']

        # If no specific check is requested, do both
        if not check_low_stock and not check_expiring:
            check_low_stock = True
            check_expiring = True

        self.stdout.write(
            self.style.SUCCESS(f'Starting pharmacy inventory check for the next {days} days...')
        )

        # Check for low stock items
        if check_low_stock:
            self.check_low_stock()

        # Check for expiring medications
        if check_expiring:
            self.check_expiring_medications(days)

        self.stdout.write(
            self.style.SUCCESS('Pharmacy inventory check completed successfully!')
        )

    def check_low_stock(self):
        """Check for medications with low stock levels"""
        self.stdout.write('Checking for low stock medications...')
        
        low_stock_items = MedicationInventory.objects.filter(
            stock_quantity__lte=F('reorder_level')
        ).select_related('medication', 'dispensary')

        if low_stock_items.exists():
            self.stdout.write(
                self.style.WARNING(f'Found {low_stock_items.count()} low stock items:')
            )
            for item in low_stock_items:
                self.stdout.write(
                    f'  - {item.medication.name} ({item.medication.strength}) '
                    f'at {item.dispensary.name}: {item.stock_quantity} units '
                    f'(reorder level: {item.reorder_level})'
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('No low stock medications found.')
            )

    def check_expiring_medications(self, days):
        """Check for medications expiring within the specified number of days"""
        self.stdout.write(f'Checking for medications expiring within {days} days...')
        
        expiry_date = timezone.now().date() + timedelta(days=days)
        
        # Check dispensary inventory
        expiring_items = MedicationInventory.objects.filter(
            medication__expiry_date__lte=expiry_date,
            medication__expiry_date__gte=timezone.now().date()
        ).select_related('medication', 'dispensary')

        # Check bulk store inventory
        expiring_bulk_items = BulkStoreInventory.objects.filter(
            medication__expiry_date__lte=expiry_date,
            medication__expiry_date__gte=timezone.now().date()
        ).select_related('medication', 'bulk_store')

        if expiring_items.exists() or expiring_bulk_items.exists():
            if expiring_items.exists():
                self.stdout.write(
                    self.style.WARNING(f'Found {expiring_items.count()} expiring medications in dispensaries:')
                )
                for item in expiring_items:
                    days_until_expiry = (item.medication.expiry_date - timezone.now().date()).days
                    self.stdout.write(
                        f'  - {item.medication.name} ({item.medication.strength}) '
                        f'at {item.dispensary.name} expires in {days_until_expiry} days '
                        f'({item.medication.expiry_date.strftime("%Y-%m-%d")})'
                    )

            if expiring_bulk_items.exists():
                self.stdout.write(
                    self.style.WARNING(f'Found {expiring_bulk_items.count()} expiring medications in bulk stores:')
                )
                for item in expiring_bulk_items:
                    days_until_expiry = (item.medication.expiry_date - timezone.now().date()).days
                    self.stdout.write(
                        f'  - {item.medication.name} ({item.medication.strength}) '
                        f'at {item.bulk_store.name} expires in {days_until_expiry} days '
                        f'({item.medication.expiry_date.strftime("%Y-%m-%d")})'
                    )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'No medications expiring within {days} days found.')
            )