from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from patients.models import Patient, PatientWallet
from django.contrib.auth.models import User
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create wallets for all registered patients who do not have wallets yet'

    def add_arguments(self, parser):
        parser.add_argument(
            '--initial-balance',
            type=float,
            default=0.0,
            help='Initial balance to set for new wallets (default: 0.0)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating wallets',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Create wallets even for inactive patients',
        )

    def handle(self, *args, **options):
        initial_balance = Decimal(str(options['initial_balance']))  # Convert to Decimal
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write(
            self.style.SUCCESS('Starting patient wallet creation process...')
        )

        # Get all patients
        if force:
            patients = Patient.objects.all()
            self.stdout.write(f"Processing all patients (including inactive)...")
        else:
            patients = Patient.objects.filter(is_active=True)
            self.stdout.write(f"Processing active patients only...")

        # Find patients without wallets
        patients_without_wallets = []
        patients_with_wallets = []

        for patient in patients:
            try:
                wallet = patient.wallet
                patients_with_wallets.append(patient)
            except PatientWallet.DoesNotExist:
                patients_without_wallets.append(patient)

        total_patients = patients.count()
        patients_needing_wallets = len(patients_without_wallets)
        patients_already_have_wallets = len(patients_with_wallets)

        self.stdout.write(f"\n📊 SUMMARY:")
        self.stdout.write(f"   Total patients: {total_patients}")
        self.stdout.write(f"   Patients with wallets: {patients_already_have_wallets}")
        self.stdout.write(f"   Patients needing wallets: {patients_needing_wallets}")

        if patients_needing_wallets == 0:
            self.stdout.write(
                self.style.SUCCESS('\n✅ All patients already have wallets!')
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\n🔍 DRY RUN MODE - No wallets will be created')
            )
            self.stdout.write(f"\nPatients who would get wallets:")
            for patient in patients_without_wallets:
                self.stdout.write(
                    f"   - {patient.get_full_name()} (ID: {patient.patient_id}) - Balance: ₦{initial_balance:.2f}"
                )
            return

        # Confirm creation
        if patients_needing_wallets > 0:
            self.stdout.write(
                f"\n💰 About to create {patients_needing_wallets} wallets with initial balance of ₦{initial_balance:.2f}"
            )

            confirm = input("Do you want to proceed? (yes/no): ")
            if confirm.lower() not in ['yes', 'y']:
                self.stdout.write(
                    self.style.WARNING('Operation cancelled by user.')
                )
                return

        # Create wallets
        created_wallets = []
        failed_wallets = []

        self.stdout.write(f"\n🚀 Creating wallets...")

        with transaction.atomic():
            for patient in patients_without_wallets:
                try:
                    wallet = PatientWallet.objects.create(
                        patient=patient,
                        balance=initial_balance,
                        is_active=True
                    )

                    # If initial balance > 0, create an initial transaction
                    if initial_balance > 0:
                        from patients.models import WalletTransaction
                        WalletTransaction.objects.create(
                            wallet=wallet,
                            transaction_type='deposit',
                            amount=initial_balance,
                            balance_after=initial_balance,
                            description=f'Initial wallet setup with balance of ₦{initial_balance:.2f}',
                            status='completed'
                        )

                    created_wallets.append(wallet)
                    self.stdout.write(
                        f"   ✅ Created wallet for {patient.get_full_name()} (ID: {patient.patient_id})"
                    )

                except Exception as e:
                    failed_wallets.append((patient, str(e)))
                    self.stdout.write(
                        self.style.ERROR(
                            f"   ❌ Failed to create wallet for {patient.get_full_name()} (ID: {patient.patient_id}): {e}"
                        )
                    )

        # Final summary
        self.stdout.write(f"\n📈 RESULTS:")
        self.stdout.write(
            self.style.SUCCESS(f"   ✅ Successfully created: {len(created_wallets)} wallets")
        )

        if failed_wallets:
            self.stdout.write(
                self.style.ERROR(f"   ❌ Failed to create: {len(failed_wallets)} wallets")
            )
            self.stdout.write(f"\nFailed wallets:")
            for patient, error in failed_wallets:
                self.stdout.write(f"   - {patient.get_full_name()}: {error}")

        if initial_balance > 0:
            total_initial_amount = len(created_wallets) * initial_balance
            self.stdout.write(
                f"\n💰 Total initial balance distributed: ₦{total_initial_amount:.2f}"
            )

        self.stdout.write(
            self.style.SUCCESS(f"\n🎉 Wallet creation process completed!")
        )

        # Show some statistics
        if created_wallets:
            self.stdout.write(f"\n📊 WALLET STATISTICS:")
            total_wallets = PatientWallet.objects.count()
            active_wallets = PatientWallet.objects.filter(is_active=True).count()
            total_balance = sum(w.balance for w in PatientWallet.objects.all())

            self.stdout.write(f"   Total wallets in system: {total_wallets}")
            self.stdout.write(f"   Active wallets: {active_wallets}")
            self.stdout.write(f"   Total system balance: ₦{total_balance:.2f}")
