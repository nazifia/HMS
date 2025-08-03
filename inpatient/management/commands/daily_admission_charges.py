"""
Django management command to automatically deduct daily admission charges 
from patient wallets at 12:00 AM for all active admissions.

This command should be run daily via cron job at 12:00 AM.
Example cron entry:
0 0 * * * cd /path/to/hms && python manage.py daily_admission_charges
"""

import logging
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta

from inpatient.models import Admission
from patients.models import PatientWallet
from billing.models import Invoice, InvoiceItem, Service
from core.utils import send_notification_email

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Automatically deduct daily admission charges from patient wallets for active admissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Process charges for specific date (YYYY-MM-DD format). Defaults to today.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        target_date = options.get('date')
        
        if target_date:
            try:
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                self.stderr.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD format.')
                )
                return
        else:
            target_date = timezone.now().date()

        if dry_run:
            self.stdout.write(
                self.style.WARNING('Running in dry-run mode. No charges will be applied.')
            )

        self.stdout.write(
            self.style.SUCCESS(f'Processing daily admission charges for {target_date}...')
        )

        # Get all active admissions (admitted status and not discharged)
        active_admissions = Admission.objects.filter(
            status='admitted',
            discharge_date__isnull=True,
            admission_date__date__lte=target_date  # Only admissions that started before or on target date
        ).select_related('patient', 'bed__ward', 'attending_doctor')

        self.stdout.write(f'Found {active_admissions.count()} active admissions to process.')

        processed_count = 0
        error_count = 0
        total_charges = Decimal('0.00')

        for admission in active_admissions:
            try:
                result = self.process_admission_charge(admission, target_date, dry_run)
                if result:
                    processed_count += 1
                    total_charges += result
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Processed admission {admission.id} for {admission.patient.get_full_name()}: ₦{result}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠ Skipped admission {admission.id} for {admission.patient.get_full_name()}: No charge applicable'
                        )
                    )
            except Exception as e:
                error_count += 1
                self.stderr.write(
                    self.style.ERROR(
                        f'✗ Error processing admission {admission.id} for {admission.patient.get_full_name()}: {str(e)}'
                    )
                )
                logger.error(f'Error processing daily charge for admission {admission.id}: {str(e)}')

        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== SUMMARY ==='))
        self.stdout.write(f'Total admissions processed: {processed_count}')
        self.stdout.write(f'Total charges applied: ₦{total_charges}')
        self.stdout.write(f'Errors encountered: {error_count}')
        
        if not dry_run and processed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Daily admission charges for {target_date} completed successfully!'
                )
            )

    def process_admission_charge(self, admission, charge_date, dry_run=False):
        """
        Process daily charge for a single admission.
        Returns the charge amount if successful, None if skipped.
        """
        # Calculate daily charge
        if not admission.bed or not admission.bed.ward:
            return None
            
        daily_charge = admission.bed.ward.charge_per_day
        if daily_charge <= 0:
            return None

        # Get or create patient wallet
        wallet, created = PatientWallet.objects.get_or_create(
            patient=admission.patient,
            defaults={'balance': Decimal('0.00')}
        )

        if created and not dry_run:
            logger.info(f'Created wallet for patient {admission.patient.get_full_name()}')

        if dry_run:
            return daily_charge

        # Create daily charge transaction
        with transaction.atomic():
            # Create or get admission service
            service, _ = Service.objects.get_or_create(
                name="Daily Admission Charge",
                defaults={
                    'price': daily_charge,
                    'category_id': 1,  # Assuming category 1 is for inpatient services
                    'description': 'Daily charge for hospital admission'
                }
            )

            # Create invoice for daily charge
            invoice = Invoice.objects.create(
                patient=admission.patient,
                invoice_date=charge_date,
                due_date=charge_date,
                status='pending',
                source_app='inpatient',
                created_by=admission.attending_doctor,
                subtotal=daily_charge,
                tax_amount=Decimal('0.00'),
                total_amount=daily_charge,
                admission=admission
            )

            # Add invoice item
            InvoiceItem.objects.create(
                invoice=invoice,
                service=service,
                description=f"Daily admission charge for {charge_date}",
                quantity=1,
                unit_price=daily_charge,
                tax_percentage=Decimal('0.00'),
                tax_amount=Decimal('0.00'),
                discount_amount=Decimal('0.00'),
                total_amount=daily_charge
            )

            # Deduct from wallet
            wallet.debit(
                amount=daily_charge,
                description=f'Daily admission charge for {charge_date} - {admission.patient.get_full_name()}',
                transaction_type='daily_admission_charge',
                user=admission.attending_doctor,
                invoice=invoice
            )

            logger.info(
                f'Applied daily charge of ₦{daily_charge} for admission {admission.id} on {charge_date}. '
                f'New wallet balance: ₦{wallet.balance}'
            )

        return daily_charge
