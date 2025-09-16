"""
Django management command to recover outstanding admission balances
from patient wallets for all active admissions.

This command specifically handles cases where daily charges were not
applied for some period, creating outstanding balances that need to be recovered.

Usage examples:
python manage.py recover_outstanding_balances --dry-run
python manage.py recover_outstanding_balances --strategy immediate
python manage.py recover_outstanding_balances --strategy gradual --max-daily 5000
"""

import logging
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from inpatient.models import Admission
from patients.models import PatientWallet

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Recover outstanding admission balances from patient wallets for active admissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--strategy',
            type=str,
            choices=['immediate', 'gradual', 'daily_plus', 'balance_aware', 'balance_proportional', 'balance_limited', 'balance_aggressive'],
            default='balance_aware',
            help='Recovery strategy: immediate (all at once), gradual (one daily charge worth), daily_plus (50% of outstanding or daily charge), balance_aware (only what wallet can afford), balance_proportional (based on wallet balance ratio), balance_limited (limited negative balance), balance_aggressive (deduct regardless of balance)',
        )
        parser.add_argument(
            '--max-daily',
            type=float,
            default=None,
            help='Maximum amount to recover per admission (overrides strategy limits)',
        )
        parser.add_argument(
            '--min-outstanding',
            type=float,
            default=100.0,
            help='Minimum outstanding balance to process (default: ₦100)',
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
        strategy = options['strategy']
        max_daily = options.get('max_daily')
        min_outstanding = Decimal(str(options['min_outstanding']))
        max_negative_balance = Decimal(str(options['max_negative_balance']))
        balance_threshold = Decimal(str(options['balance_threshold']))

        if dry_run:
            self.stdout.write(
                self.style.WARNING('Running in dry-run mode. No charges will be applied.')
            )

        self.stdout.write(
            self.style.SUCCESS(f'Processing outstanding balance recovery using {strategy} strategy...')
        )

        # Get all active admissions with outstanding balances
        active_admissions = Admission.objects.filter(
            status='admitted',
            discharge_date__isnull=True
        ).select_related('patient', 'bed__ward', 'attending_doctor')

        admissions_with_outstanding = []
        for admission in active_admissions:
            outstanding = admission.get_outstanding_admission_cost()
            if outstanding >= min_outstanding:
                admissions_with_outstanding.append((admission, outstanding))

        self.stdout.write(f'Found {len(admissions_with_outstanding)} admissions with outstanding balances ≥ ₦{min_outstanding}.')

        if not admissions_with_outstanding:
            self.stdout.write(self.style.SUCCESS('No outstanding balances to recover.'))
            return

        processed_count = 0
        error_count = 0
        total_outstanding_found = Decimal('0.00')
        total_recovered = Decimal('0.00')

        for admission, outstanding_balance in admissions_with_outstanding:
            total_outstanding_found += outstanding_balance
            
            try:
                recovery_amount = self.calculate_recovery_amount(
                    admission, outstanding_balance, strategy, max_daily, max_negative_balance, balance_threshold
                )
                
                if recovery_amount > 0:
                    if not dry_run:
                        actual_recovered = self.process_recovery(admission, recovery_amount)
                        total_recovered += actual_recovered
                    else:
                        total_recovered += recovery_amount
                    
                    processed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ {admission.patient.get_full_name()}: Outstanding ₦{outstanding_balance}, '
                            f'{"Would recover" if dry_run else "Recovered"} ₦{recovery_amount}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠ {admission.patient.get_full_name()}: Outstanding ₦{outstanding_balance}, '
                            f'No recovery amount calculated'
                        )
                    )
                    
            except Exception as e:
                error_count += 1
                self.stderr.write(
                    self.style.ERROR(
                        f'✗ Error processing {admission.patient.get_full_name()}: {str(e)}'
                    )
                )
                logger.error(f'Error processing outstanding balance for admission {admission.id}: {str(e)}')

        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== OUTSTANDING BALANCE RECOVERY SUMMARY ==='))
        self.stdout.write(f'Admissions processed: {processed_count}')
        self.stdout.write(f'Total outstanding found: ₦{total_outstanding_found}')
        self.stdout.write(f'Total {"would be recovered" if dry_run else "recovered"}: ₦{total_recovered}')
        self.stdout.write(f'Remaining outstanding: ₦{total_outstanding_found - total_recovered}')
        self.stdout.write(f'Errors encountered: {error_count}')
        
        if not dry_run and total_recovered > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Outstanding balance recovery completed! ₦{total_recovered} recovered from patient wallets.'
                )
            )

    def calculate_recovery_amount(self, admission, outstanding_balance, strategy, max_daily, max_negative_balance, balance_threshold):
        """Calculate how much to recover based on wallet-balance-aware strategy"""
        if outstanding_balance <= 0:
            return Decimal('0.00')

        # Check if patient is NHIA - NHIA patients are exempt
        try:
            is_nhia_patient = (hasattr(admission.patient, 'nhia_info') and
                             admission.patient.nhia_info and
                             admission.patient.nhia_info.is_active)
        except:
            is_nhia_patient = False

        if is_nhia_patient:
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

        recovery_amount = Decimal('0.00')

        if strategy == 'immediate':
            # Recover all outstanding balance at once (original behavior)
            recovery_amount = outstanding_balance
        elif strategy == 'gradual':
            # Recover one daily charge worth (original behavior)
            recovery_amount = min(outstanding_balance, daily_charge)
        elif strategy == 'daily_plus':
            # Recover 50% of outstanding balance or daily charge (original behavior)
            recovery_amount = min(outstanding_balance, daily_charge, outstanding_balance * Decimal('0.5'))
        elif strategy == 'balance_aware':
            # Only recover what wallet can afford without going below threshold
            available_balance = current_balance - balance_threshold
            if available_balance > 0:
                recovery_amount = min(outstanding_balance, available_balance, daily_charge)
            else:
                recovery_amount = Decimal('0.00')  # Don't recover if balance too low
        elif strategy == 'balance_proportional':
            # Recover based on wallet balance ratio (more balance = more recovery)
            if current_balance > 0:
                # If positive balance, recover proportionally (up to daily charge)
                balance_ratio = min(current_balance / (daily_charge * 5), Decimal('1.0'))  # 5 days worth as reference
                recovery_amount = min(outstanding_balance, daily_charge * balance_ratio)
            else:
                # If negative balance, recover smaller amount
                recovery_amount = min(outstanding_balance, daily_charge * Decimal('0.25'))
        elif strategy == 'balance_limited':
            # Allow negative balance but with limits
            max_deduction = max_negative_balance + current_balance  # How much we can deduct before hitting limit
            if max_deduction > 0:
                recovery_amount = min(outstanding_balance, max_deduction, daily_charge * 2)
            else:
                recovery_amount = Decimal('0.00')  # Already at negative limit
        elif strategy == 'balance_aggressive':
            # Recover outstanding regardless of balance (but respect daily limits)
            recovery_amount = min(outstanding_balance, daily_charge * 3)  # Up to 3 days worth

        # Apply max daily recovery limit if specified
        if max_daily:
            recovery_amount = min(recovery_amount, Decimal(str(max_daily)))

        return recovery_amount

    def process_recovery(self, admission, recovery_amount):
        """Process the actual recovery transaction"""
        try:
            wallet = PatientWallet.objects.get(patient=admission.patient)
            previous_balance = wallet.balance
        except PatientWallet.DoesNotExist:
            logger.error(f'No wallet found for patient {admission.patient.get_full_name()}')
            return Decimal('0.00')

        with transaction.atomic():
            try:
                wallet.debit(
                    amount=recovery_amount,
                    description=f"Outstanding balance recovery - {admission.bed.ward.name} (prev balance: ₦{previous_balance})",
                    transaction_type="outstanding_admission_recovery",
                    user=admission.attending_doctor,
                    admission=admission
                )

                logger.info(
                    f'Outstanding balance recovery of ₦{recovery_amount} deducted from wallet for '
                    f'patient {admission.patient.get_full_name()} (Admission {admission.id}). '
                    f'Previous balance: ₦{previous_balance}, New balance: ₦{wallet.balance}'
                )

                return recovery_amount

            except Exception as e:
                logger.error(
                    f'Failed to process outstanding balance recovery for admission {admission.id}: {str(e)}'
                )
                raise e
