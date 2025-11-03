from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from pharmacy.models import MedicationTransfer, BulkStoreInventory, ActiveStoreInventory
from datetime import date

User = get_user_model()


class Command(BaseCommand):
    help = 'Deliver all in-transit medication transfers to their destinations'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        # Get in-transit transfers
        in_transit_transfers = MedicationTransfer.objects.filter(status='in_transit')

        if not in_transit_transfers.exists():
            self.stdout.write(
                self.style.WARNING('No in-transit transfers found.')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Found {in_transit_transfers.count()} in-transit transfers to deliver.')
        )

        # Get an existing user or create system user
        try:
            system_user = User.objects.filter(username='admin').first()
            if not system_user:
                system_user = User.objects.first()
            if not system_user:
                # Create a system user with phone number
                system_user = User.objects.create(
                    username='system_delivery',
                    phone_number='0000000000',  # Default phone number for system
                    email='system@hms.local',
                    first_name='System',
                    last_name='User',
                    is_staff=False,
                    is_active=True,
                )
                system_user.set_password('system123!')
                system_user.save()
                self.stdout.write(self.style.SUCCESS('Created system user for processing'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Using existing user: {system_user.username}'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not create system user: {str(e)}'))
            system_user = None

        success_count = 0
        error_count = 0

        with transaction.atomic():
            for transfer in in_transit_transfers:
                try:
                    self.stdout.write(
                        f'\nProcessing Transfer #{transfer.id}: '
                        f'{transfer.medication.name} - {transfer.quantity} units to {transfer.to_active_store.dispensary.name}'
                    )

                    # Find bulk store inventory
                    bulk_inventory = BulkStoreInventory.objects.filter(
                        medication=transfer.medication,
                        bulk_store=transfer.from_bulk_store,
                        batch_number=transfer.batch_number,
                        stock_quantity__gte=transfer.quantity
                    ).first()

                    if not bulk_inventory:
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ERROR: Insufficient stock in bulk store. '
                                f'Available: {bulk_inventory.stock_quantity if bulk_inventory else 0}, '
                                f'Required: {transfer.quantity}'
                            )
                        )
                        error_count += 1
                        continue

                    # Check if medication is expired
                    if bulk_inventory.expiry_date and bulk_inventory.expiry_date < date.today():
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ERROR: Medication expired on {bulk_inventory.expiry_date}'
                            )
                        )
                        error_count += 1
                        continue

                    # Check if already delivered (double-check)
                    if transfer.status == 'delivered':
                        self.stdout.write(
                            self.style.WARNING(f'  WARNING: Transfer already marked as delivered. Skipping.')
                        )
                        success_count += 1
                        continue

                    # Reduce bulk store inventory
                    bulk_inventory.stock_quantity -= transfer.quantity
                    bulk_inventory.save()

                    self.stdout.write(
                        f'  ✓ Reduced bulk store inventory: {bulk_inventory.stock_quantity + transfer.quantity} -> {bulk_inventory.stock_quantity}'
                    )

                    # Add to active store inventory
                    active_inventory, created = ActiveStoreInventory.objects.get_or_create(
                        medication=transfer.medication,
                        active_store=transfer.to_active_store,
                        batch_number=transfer.batch_number,
                        defaults={
                            'stock_quantity': 0,
                            'reorder_level': transfer.medication.reorder_level if hasattr(transfer.medication, 'reorder_level') else 10,
                            'expiry_date': transfer.expiry_date or bulk_inventory.expiry_date,
                            'unit_cost': transfer.unit_cost or bulk_inventory.unit_cost,
                            'last_restock_date': timezone.now().date()
                        }
                    )

                    old_quantity = active_inventory.stock_quantity
                    if created:
                        active_inventory.stock_quantity = transfer.quantity
                        self.stdout.write(
                            f'  ✓ Created new active store inventory: {active_inventory.stock_quantity} units'
                        )
                    else:
                        active_inventory.stock_quantity += transfer.quantity
                        active_inventory.last_restock_date = timezone.now().date()
                        self.stdout.write(
                            f'  ✓ Updated active store inventory: {old_quantity} -> {active_inventory.stock_quantity} units'
                        )

                    active_inventory.save()

                    # Mark transfer as delivered
                    transfer.status = 'delivered'
                    transfer.delivered_by = system_user if system_user else transfer.requested_by
                    transfer.delivered_at = timezone.now()
                    transfer.save()

                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Transfer #{transfer.id} marked as DELIVERED')
                    )
                    success_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ERROR: {str(e)}')
                    )
                    error_count += 1
                    continue

        # Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS(f'DELIVERY COMPLETE'))
        self.stdout.write(f'Successfully delivered: {success_count}')
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Failed to deliver: {error_count}'))
        self.stdout.write('='*70)
