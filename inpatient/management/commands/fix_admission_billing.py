from django.core.management.base import BaseCommand
from django.db import transaction
from inpatient.models import Admission
from billing.models import Invoice, InvoiceItem, Service
from patients.models import PatientWallet
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fix admission billing for admissions that do not have invoices or wallet deductions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admission-id',
            type=int,
            help='Fix specific admission by ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        admission_id = options.get('admission_id')
        dry_run = options.get('dry_run')

        if admission_id:
            admissions = Admission.objects.filter(id=admission_id)
            if not admissions.exists():
                self.stdout.write(self.style.ERROR(f'Admission with ID {admission_id} not found.'))
                return
        else:
            # Find all admissions without invoices
            admissions = Admission.objects.filter(
                invoices__isnull=True,
                status='admitted'
            )

        self.stdout.write(f'Found {admissions.count()} admissions to process.')

        for admission in admissions:
            self.stdout.write(f'\nProcessing admission {admission.id} for patient {admission.patient.get_full_name()}')
            
            if dry_run:
                self.stdout.write(f'  Would create invoice for ₦{admission.get_total_cost()}')
                self.stdout.write(f'  Would deduct ₦{admission.get_total_cost()} from wallet')
                continue

            try:
                with transaction.atomic():
                    # Get the service for admission
                    service, created = Service.objects.get_or_create(
                        name="Admission Fee", 
                        defaults={'price': admission.get_total_cost(), 'category_id': 1}
                    )
                    
                    if created:
                        self.stdout.write(f'  Created Admission Fee service')

                    # Create the invoice
                    invoice = Invoice.objects.create(
                        patient=admission.patient,
                        invoice_date=timezone.now().date(),
                        due_date=timezone.now().date(),
                        status='pending',
                        source_app='inpatient',
                        created_by=admission.created_by,
                        subtotal=admission.get_total_cost(),
                        tax_amount=0,
                        total_amount=admission.get_total_cost(),
                        admission=admission
                    )
                    self.stdout.write(f'  Created invoice {invoice.id} for ₦{admission.get_total_cost()}')

                    # Create the invoice item
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        service=service,
                        quantity=1,
                        unit_price=admission.get_total_cost(),
                        tax_percentage=0,
                        tax_amount=0,
                        total_amount=admission.get_total_cost()
                    )
                    self.stdout.write(f'  Created invoice item')

                    # Get or create patient wallet
                    wallet, wallet_created = PatientWallet.objects.get_or_create(
                        patient=admission.patient,
                        defaults={'balance': 0}
                    )
                    
                    if wallet_created:
                        self.stdout.write(f'  Created wallet for patient')

                    # Deduct admission fee from wallet
                    if admission.get_total_cost() > 0:
                        old_balance = wallet.balance
                        wallet.debit(
                            amount=admission.get_total_cost(),
                            description=f'Admission fee for {admission.patient.get_full_name()}',
                            transaction_type='admission_fee',
                            user=admission.created_by,
                            invoice=invoice
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  Deducted ₦{admission.get_total_cost()} from wallet. '
                                f'Balance: ₦{old_balance} → ₦{wallet.balance}'
                            )
                        )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  Error processing admission {admission.id}: {str(e)}')
                )
                logger.error(f'Error fixing admission billing for admission {admission.id}: {str(e)}')

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'\nCompleted processing {admissions.count()} admissions.')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'\nDry run completed. Use --no-dry-run to apply changes.')
            )
