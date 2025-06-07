from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from patients.models import Patient, PatientWallet, WalletTransaction
from django.contrib.auth.models import User
from decimal import Decimal


class Command(BaseCommand):
    help = 'Add initial funds to existing patient wallets'

    def add_arguments(self, parser):
        parser.add_argument(
            'amount',
            type=float,
            help='Amount to add to each wallet',
        )
        parser.add_argument(
            '--patient-id',
            type=str,
            help='Add funds to specific patient by patient ID',
        )
        parser.add_argument(
            '--patient-name',
            type=str,
            help='Add funds to specific patient by name (partial match)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be added without actually adding funds',
        )
        parser.add_argument(
            '--description',
            type=str,
            default='Initial wallet funding',
            help='Description for the transaction',
        )

    def handle(self, *args, **options):
        amount = Decimal(str(options['amount']))  # Convert to Decimal
        patient_id = options.get('patient_id')
        patient_name = options.get('patient_name')
        dry_run = options['dry_run']
        description = options['description']

        if amount <= 0:
            raise CommandError('Amount must be greater than 0')

        self.stdout.write(
            self.style.SUCCESS('Starting wallet funding process...')
        )

        # Determine which wallets to fund
        wallets_to_fund = []

        if patient_id:
            # Fund specific patient by ID
            try:
                patient = Patient.objects.get(patient_id=patient_id)
                wallet, created = PatientWallet.objects.get_or_create(patient=patient)
                if created:
                    self.stdout.write(f"Created new wallet for {patient.get_full_name()}")
                wallets_to_fund.append(wallet)
                self.stdout.write(f"Selected patient: {patient.get_full_name()} (ID: {patient.patient_id})")
            except Patient.DoesNotExist:
                raise CommandError(f'Patient with ID "{patient_id}" not found')

        elif patient_name:
            # Fund specific patient(s) by name
            patients = Patient.objects.filter(
                first_name__icontains=patient_name
            ) | Patient.objects.filter(
                last_name__icontains=patient_name
            )

            if not patients.exists():
                raise CommandError(f'No patients found matching name "{patient_name}"')

            self.stdout.write(f"Found {patients.count()} patient(s) matching '{patient_name}':")
            for patient in patients:
                wallet, created = PatientWallet.objects.get_or_create(patient=patient)
                if created:
                    self.stdout.write(f"Created new wallet for {patient.get_full_name()}")
                wallets_to_fund.append(wallet)
                self.stdout.write(f"   - {patient.get_full_name()} (ID: {patient.patient_id})")

        else:
            # Fund all existing wallets
            wallets_to_fund = list(PatientWallet.objects.all())
            self.stdout.write(f"Selected all existing wallets: {len(wallets_to_fund)} wallets")

        if not wallets_to_fund:
            self.stdout.write(
                self.style.WARNING('No wallets found to fund.')
            )
            return

        # Show summary
        total_amount = len(wallets_to_fund) * amount
        self.stdout.write(f"\n📊 FUNDING SUMMARY:")
        self.stdout.write(f"   Wallets to fund: {len(wallets_to_fund)}")
        self.stdout.write(f"   Amount per wallet: ₦{amount:.2f}")
        self.stdout.write(f"   Total amount to distribute: ₦{total_amount:.2f}")
        self.stdout.write(f"   Description: {description}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\n🔍 DRY RUN MODE - No funds will be added')
            )
            self.stdout.write(f"\nWallets that would be funded:")
            for wallet in wallets_to_fund:
                current_balance = wallet.balance
                new_balance = current_balance + amount
                self.stdout.write(
                    f"   - {wallet.patient.get_full_name()} (ID: {wallet.patient.patient_id})"
                    f" - Current: ₦{current_balance:.2f} → New: ₦{new_balance:.2f}"
                )
            return

        # Confirm funding
        self.stdout.write(
            f"\n💰 About to add ₦{amount:.2f} to {len(wallets_to_fund)} wallet(s)"
        )

        confirm = input("Do you want to proceed? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            self.stdout.write(
                self.style.WARNING('Operation cancelled by user.')
            )
            return

        # Add funds to wallets
        successful_funding = []
        failed_funding = []

        self.stdout.write(f"\n🚀 Adding funds to wallets...")

        with transaction.atomic():
            for wallet in wallets_to_fund:
                try:
                    old_balance = wallet.balance

                    # Use the wallet's credit method to add funds and create transaction
                    wallet.credit(
                        amount=amount,
                        description=description,
                        transaction_type='deposit',
                        user=None  # System operation
                    )

                    new_balance = wallet.balance
                    successful_funding.append(wallet)

                    self.stdout.write(
                        f"   ✅ {wallet.patient.get_full_name()} (ID: {wallet.patient.patient_id}): "
                        f"₦{old_balance:.2f} → ₦{new_balance:.2f}"
                    )

                except Exception as e:
                    failed_funding.append((wallet, str(e)))
                    self.stdout.write(
                        self.style.ERROR(
                            f"   ❌ Failed to fund {wallet.patient.get_full_name()}: {e}"
                        )
                    )

        # Final summary
        self.stdout.write(f"\n📈 RESULTS:")
        self.stdout.write(
            self.style.SUCCESS(f"   ✅ Successfully funded: {len(successful_funding)} wallets")
        )

        if failed_funding:
            self.stdout.write(
                self.style.ERROR(f"   ❌ Failed to fund: {len(failed_funding)} wallets")
            )
            self.stdout.write(f"\nFailed funding:")
            for wallet, error in failed_funding:
                self.stdout.write(f"   - {wallet.patient.get_full_name()}: {error}")

        if successful_funding:
            total_distributed = len(successful_funding) * amount
            self.stdout.write(
                f"\n💰 Total amount distributed: ₦{total_distributed:.2f}"
            )

        self.stdout.write(
            self.style.SUCCESS(f"\n🎉 Wallet funding process completed!")
        )

        # Show updated statistics
        if successful_funding:
            self.stdout.write(f"\n📊 UPDATED WALLET STATISTICS:")
            total_wallets = PatientWallet.objects.count()
            active_wallets = PatientWallet.objects.filter(is_active=True).count()
            total_balance = sum(w.balance for w in PatientWallet.objects.all())
            total_transactions = WalletTransaction.objects.count()

            self.stdout.write(f"   Total wallets in system: {total_wallets}")
            self.stdout.write(f"   Active wallets: {active_wallets}")
            self.stdout.write(f"   Total system balance: ₦{total_balance:.2f}")
            self.stdout.write(f"   Total transactions: {total_transactions}")
