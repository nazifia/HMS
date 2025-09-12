"""
Django management command to link existing admission-related wallet transactions
to their corresponding admissions.

This command should be run once after adding the admission FK to WalletTransaction.
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from datetime import timedelta

from patients.models import WalletTransaction
from inpatient.models import Admission
from billing.models import Invoice

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Link existing admission-related wallet transactions to their admissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('Running in dry-run mode. No changes will be made.')
            )

        self.stdout.write('Linking existing admission transactions to admissions...')

        # Link admission fee transactions via invoice
        admission_fee_linked = self.link_admission_fees(dry_run)
        
        # Link daily admission charge transactions via date matching
        daily_charge_linked = self.link_daily_charges(dry_run)
        
        self.stdout.write(self.style.SUCCESS('\n=== SUMMARY ==='))
        self.stdout.write(f'Admission fee transactions linked: {admission_fee_linked}')
        self.stdout.write(f'Daily charge transactions linked: {daily_charge_linked}')
        self.stdout.write(f'Total transactions linked: {admission_fee_linked + daily_charge_linked}')
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS('Admission transaction linking completed!')
            )

    def link_admission_fees(self, dry_run=False):
        """Link admission fee transactions to admissions via invoice relationship"""
        self.stdout.write('\nLinking admission fee transactions...')
        
        linked_count = 0
        
        # Get admission fee transactions that have an invoice but no admission link
        admission_fee_transactions = WalletTransaction.objects.filter(
            transaction_type='admission_fee',
            admission__isnull=True,
            invoice__isnull=False
        )
        
        self.stdout.write(f'Found {admission_fee_transactions.count()} admission fee transactions to process.')
        
        for transaction in admission_fee_transactions:
            try:
                # Check if the invoice is linked to an admission
                if hasattr(transaction.invoice, 'admission') and transaction.invoice.admission:
                    admission = transaction.invoice.admission
                    
                    # Verify the admission patient matches the transaction wallet patient
                    if admission.patient == transaction.wallet.patient:
                        if not dry_run:
                            transaction.admission = admission
                            transaction.save(update_fields=['admission'])
                        
                        linked_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'[OK] Linked admission fee transaction {transaction.id} to admission {admission.id}'
                            )
                        )
                    else:
                        self.stderr.write(
                            self.style.WARNING(
                                f'[WARNING] Patient mismatch for transaction {transaction.id} - skipping'
                            )
                        )
                        
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(
                        f'[ERROR] Error processing admission fee transaction {transaction.id}: {str(e)}'
                    )
                )
        
        return linked_count

    def link_daily_charges(self, dry_run=False):
        """Link daily admission charge transactions to admissions via date matching"""
        self.stdout.write('\nLinking daily charge transactions...')
        
        linked_count = 0
        
        # Get daily charge transactions that have no admission link
        daily_charge_transactions = WalletTransaction.objects.filter(
            transaction_type='daily_admission_charge',
            admission__isnull=True
        )
        
        self.stdout.write(f'Found {daily_charge_transactions.count()} daily charge transactions to process.')
        
        for transaction in daily_charge_transactions:
            try:
                # Find admissions for this patient that were active on the transaction date
                transaction_date = transaction.created_at.date()
                
                # Look for admissions that were active on this date
                active_admissions = Admission.objects.filter(
                    patient=transaction.wallet.patient,
                    admission_date__date__lte=transaction_date
                ).filter(
                    # Either not discharged yet, or discharged after this date
                    models.Q(discharge_date__isnull=True) |
                    models.Q(discharge_date__date__gte=transaction_date)
                )
                
                if active_admissions.count() == 1:
                    # Only link if there's exactly one matching admission to avoid ambiguity
                    admission = active_admissions.first()
                    
                    if not dry_run:
                        transaction.admission = admission
                        transaction.save(update_fields=['admission'])
                    
                    linked_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'[OK] Linked daily charge transaction {transaction.id} to admission {admission.id}'
                        )
                    )
                elif active_admissions.count() > 1:
                    self.stdout.write(
                        self.style.WARNING(
                            f'[WARNING] Multiple active admissions found for transaction {transaction.id} on {transaction_date} - skipping'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'[WARNING] No active admission found for transaction {transaction.id} on {transaction_date} - skipping'
                        )
                    )
                        
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(
                        f'[ERROR] Error processing daily charge transaction {transaction.id}: {str(e)}'
                    )
                )
        
        return linked_count
