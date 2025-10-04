"""
Django management command to automatically deduct daily admission charges
from patient wallets for all active admissions at 12:00 AM.

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
        parser.add_argument(
            '--recover-outstanding',
            action='store_true',
            help='Also recover outstanding balances from previous days',
        )
        parser.add_argument(
            '--recovery-strategy',
            type=str,
            choices=['immediate', 'gradual', 'daily_plus', 'balance_aware', 'balance_proportional', 'balance_limited', 'balance_aggressive'],
            default='balance_aware',
            help='Strategy for recovering outstanding balances: immediate (all at once), gradual (double daily until caught up), daily_plus (daily + portion of outstanding), balance_aware (only what wallet can afford), balance_proportional (based on wallet balance ratio), balance_limited (limited negative balance), balance_aggressive (deduct regardless of balance)',
        )
        parser.add_argument(
            '--max-daily-recovery',
            type=float,
            default=None,
            help='Maximum amount to recover per day for outstanding balances (in addition to daily charge)',
        )
        parser.add_argument(
            '--max-negative-balance',
            type=float,
            default=10000.0,
            help='Maximum negative balance to allow when using balance-limited strategy (default: ₦10,000)',
        )
        parser.add_argument(
            '--balance-threshold',
            type=float,
            default=1000.0,
            help='Minimum positive balance to maintain when using balance-aware strategy (default: ₦1,000)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        target_date = options.get('date')
        recover_outstanding = options['recover_outstanding']
        recovery_strategy = options['recovery_strategy']
        max_daily_recovery = options.get('max_daily_recovery')
        max_negative_balance = Decimal(str(options['max_negative_balance']))
        balance_threshold = Decimal(str(options['balance_threshold']))

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

        mode_description = "daily admission charges"
        if recover_outstanding:
            mode_description += f" with outstanding balance recovery ({recovery_strategy} strategy)"
            if max_daily_recovery:
                mode_description += f", max recovery: ₦{max_daily_recovery}/day"

        self.stdout.write(
            self.style.SUCCESS(f'Processing {mode_description} for {target_date}...')
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
        total_outstanding_recovered = Decimal('0.00')

        for admission in active_admissions:
            try:
                # Process regular daily charge
                daily_result = self.process_admission_charge(admission, target_date, dry_run)

                # Process outstanding balance recovery if enabled
                outstanding_result = Decimal('0.00')
                if recover_outstanding:
                    outstanding_result = self.process_outstanding_balance(
                        admission, target_date, recovery_strategy, max_daily_recovery,
                        max_negative_balance, balance_threshold, dry_run
                    )

                total_result = (daily_result or Decimal('0.00')) + outstanding_result

                if total_result > 0:
                    processed_count += 1
                    total_charges += (daily_result or Decimal('0.00'))
                    total_outstanding_recovered += outstanding_result

                    charge_details = []
                    if daily_result:
                        charge_details.append(f"Daily: ₦{daily_result}")
                    if outstanding_result:
                        charge_details.append(f"Outstanding: ₦{outstanding_result}")

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Processed admission {admission.id} for {admission.patient.get_full_name()}: {", ".join(charge_details)} (Total: ₦{total_result})'
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
        self.stdout.write(f'Total daily charges applied: ₦{total_charges}')
        if recover_outstanding:
            self.stdout.write(f'Total outstanding balance recovered: ₦{total_outstanding_recovered}')
            self.stdout.write(f'Total amount deducted: ₦{total_charges + total_outstanding_recovered}')
        self.stdout.write(f'Errors encountered: {error_count}')

        if not dry_run and processed_count > 0:
            message = f'Daily admission charges automatically deducted from patient wallets for {target_date}!'
            if recover_outstanding and total_outstanding_recovered > 0:
                message += f' Outstanding balance recovery: ₦{total_outstanding_recovered} recovered.'
            self.stdout.write(self.style.SUCCESS(message))

    def process_admission_charge(self, admission, charge_date, dry_run=False):
        """
        Process daily charge for a single admission.
        Returns the charge amount if successful, None if skipped.
        """
        # Check if patient is NHIA - NHIA patients are exempt from admission fees
        if admission.patient.is_nhia_patient():
            logger.info(f'Patient {admission.patient.get_full_name()} is NHIA - no daily charges applied.')
            return None
        
        # Apply daily charges to all other patient types (regular, private pay, insurance, etc.)
        # This ensures that admission charges are auto-deducted for all non-NHIA patients

        # Apply daily charges to all other patient types (regular, private pay, insurance, etc.)
        # This ensures that admission charges are auto-deducted for all non-NHIA patients

        # Check if admission was active on the charge date
        admission_date = admission.admission_date.date()
        discharge_date = admission.discharge_date.date() if admission.discharge_date else None

        # Skip if charge date is before admission
        if charge_date < admission_date:
            return None

        # Skip if charge date is after discharge (if discharged)
        if discharge_date and charge_date > discharge_date:
            return None

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

        # Check if daily charge already exists for this date to prevent double deduction
        from patients.models import WalletTransaction
        existing_charge = WalletTransaction.objects.filter(
            wallet=wallet,
            admission=admission,
            transaction_type='daily_admission_charge',
            created_at__date=charge_date
        ).exists()

        if existing_charge and not dry_run:
            logger.info(f'Daily charge already exists for {admission.patient.get_full_name()} on {charge_date} - skipping.')
            return None

        if dry_run:
            return daily_charge

        # Automatically deduct daily charge from patient wallet
        with transaction.atomic():
            try:
                # Deduct from patient wallet
                wallet.debit(
                    amount=daily_charge,
                    description=f"Daily admission charge for {charge_date} - {admission.bed.ward.name}",
                    transaction_type="daily_admission_charge",
                    user=admission.attending_doctor,
                    admission=admission
                )

                logger.info(
                    f'Daily charge of ₦{daily_charge} automatically deducted from wallet for '
                    f'patient {admission.patient.get_full_name()} (Admission {admission.id}) on {charge_date}. '
                    f'New wallet balance: ₦{wallet.balance}'
                )

                # Send notification if wallet balance is low or negative
                if wallet.balance < 0:
                    logger.warning(
                        f'Patient {admission.patient.get_full_name()} wallet balance is now negative: ₦{wallet.balance}'
                    )
                elif wallet.balance < daily_charge:
                    logger.warning(
                        f'Patient {admission.patient.get_full_name()} wallet balance is low: ₦{wallet.balance}'
                    )

            except Exception as e:
                logger.error(
                    f'Failed to deduct daily charge for admission {admission.id}: {str(e)}'
                )
                # Continue processing other admissions even if one fails
                return None

        return daily_charge

    def process_outstanding_balance(self, admission, charge_date, recovery_strategy='balance_aware', max_daily_recovery=None, max_negative_balance=None, balance_threshold=None, dry_run=False):
        """
        Process outstanding balance recovery for an admission using wallet-balance-aware strategies.
        Returns the amount recovered.
        """
        # Check if patient is NHIA - NHIA patients are exempt from admission fees
        if admission.patient.is_nhia_patient():
            return Decimal('0.00')
        
        # Apply outstanding balance recovery to all other patient types (regular, private pay, insurance, etc.)
        # This ensures that outstanding balances are recovered for all non-NHIA patients

        # Calculate outstanding balance
        outstanding_balance = admission.get_outstanding_admission_cost()
        if outstanding_balance <= 0:
            return Decimal('0.00')

        # Get daily charge for calculations
        if not admission.bed or not admission.bed.ward:
            return Decimal('0.00')

        daily_charge = admission.bed.ward.charge_per_day

        # Get current wallet balance
        try:
            wallet = PatientWallet.objects.get(patient=admission.patient)
            current_balance = wallet.balance
        except PatientWallet.DoesNotExist:
            logger.error(f'No wallet found for patient {admission.patient.get_full_name()}')
            return Decimal('0.00')

        # Set default values for balance-aware parameters
        if max_negative_balance is None:
            max_negative_balance = Decimal('10000.00')
        if balance_threshold is None:
            balance_threshold = Decimal('1000.00')

        # Determine recovery amount based on strategy
        recovery_amount = Decimal('0.00')

        if recovery_strategy == 'immediate':
            # Recover all outstanding balance at once (original behavior)
            recovery_amount = outstanding_balance
        elif recovery_strategy == 'gradual':
            # Recover one additional daily charge worth (original behavior)
            recovery_amount = min(outstanding_balance, daily_charge)
        elif recovery_strategy == 'daily_plus':
            # Recover 50% of outstanding balance or daily charge (original behavior)
            recovery_amount = min(outstanding_balance, daily_charge, outstanding_balance * Decimal('0.5'))
        elif recovery_strategy == 'balance_aware':
            # Only recover what wallet can afford without going below threshold
            available_balance = current_balance - balance_threshold
            if available_balance > 0:
                recovery_amount = min(outstanding_balance, available_balance, daily_charge)
            else:
                recovery_amount = Decimal('0.00')  # Don't recover if balance too low
        elif recovery_strategy == 'balance_proportional':
            # Recover based on wallet balance ratio (more balance = more recovery)
            if current_balance > 0:
                # If positive balance, recover proportionally (up to daily charge)
                balance_ratio = min(current_balance / (daily_charge * 5), Decimal('1.0'))  # 5 days worth as reference
                recovery_amount = min(outstanding_balance, daily_charge * balance_ratio)
            else:
                # If negative balance, recover smaller amount
                recovery_amount = min(outstanding_balance, daily_charge * Decimal('0.25'))
        elif recovery_strategy == 'balance_limited':
            # Allow negative balance but with limits
            max_deduction = max_negative_balance + current_balance  # How much we can deduct before hitting limit
            if max_deduction > 0:
                recovery_amount = min(outstanding_balance, max_deduction, daily_charge * 2)
            else:
                recovery_amount = Decimal('0.00')  # Already at negative limit
        elif recovery_strategy == 'balance_aggressive':
            # Recover outstanding regardless of balance (but respect daily limits)
            recovery_amount = min(outstanding_balance, daily_charge * 3)  # Up to 3 days worth

        # Apply max daily recovery limit if specified
        if max_daily_recovery:
            recovery_amount = min(recovery_amount, Decimal(str(max_daily_recovery)))

        if recovery_amount <= 0:
            return Decimal('0.00')

        if dry_run:
            return recovery_amount

        # Wallet already retrieved above for balance-aware calculations

        # Deduct outstanding balance recovery
        with transaction.atomic():
            try:
                wallet.debit(
                    amount=recovery_amount,
                    description=f"Outstanding balance recovery - {admission.bed.ward.name} ({recovery_strategy} strategy, prev balance: ₦{current_balance})",
                    transaction_type="outstanding_admission_recovery",
                    user=admission.attending_doctor,
                    admission=admission
                )

                logger.info(
                    f'Outstanding balance recovery of ₦{recovery_amount} deducted from wallet for '
                    f'patient {admission.patient.get_full_name()} (Admission {admission.id}) on {charge_date}. '
                    f'Strategy: {recovery_strategy}. Previous balance: ₦{current_balance}, New balance: ₦{wallet.balance}'
                )

                return recovery_amount

            except Exception as e:
                logger.error(
                    f'Failed to deduct outstanding balance recovery for admission {admission.id}: {str(e)}'
                )
                return Decimal('0.00')
