from django.core.management.base import BaseCommand
from patients.models import Patient, PatientWallet

class Command(BaseCommand):
    help = 'Checks and lists patients with and without wallets, and their wallet status.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Checking Patient Wallets ---'))

        patients_with_wallets = 0
        patients_without_wallets = 0
        active_wallets = 0
        inactive_wallets = 0

        for patient in Patient.objects.all():
            try:
                wallet = patient.wallet
                patients_with_wallets += 1
                if wallet.is_active:
                    active_wallets += 1
                    self.stdout.write(self.style.SUCCESS(f'Patient: {patient.get_full_name()} (ID: {patient.patient_id}) - Wallet ID: {wallet.id}, Balance: {wallet.balance}, Status: Active'))
                else:
                    inactive_wallets += 1
                    self.stdout.write(self.style.WARNING(f'Patient: {patient.get_full_name()} (ID: {patient.patient_id}) - Wallet ID: {wallet.id}, Balance: {wallet.balance}, Status: Inactive'))
            except PatientWallet.DoesNotExist:
                patients_without_wallets += 1
                self.stdout.write(self.style.ERROR(f'Patient: {patient.get_full_name()} (ID: {patient.patient_id}) - No wallet found.'))
            except AttributeError:
                # This handles cases where patient.wallet might not be a direct attribute 
                # if the related_name is different or not set up, though less likely with OneToOneField
                patients_without_wallets += 1
                self.stdout.write(self.style.ERROR(f'Patient: {patient.get_full_name()} (ID: {patient.patient_id}) - No wallet attribute found (potential setup issue).'))


        self.stdout.write(self.style.SUCCESS('\n--- Summary ---'))
        self.stdout.write(f'Total Patients Checked: {Patient.objects.count()}')
        self.stdout.write(self.style.SUCCESS(f'Patients with Wallets: {patients_with_wallets}'))
        self.stdout.write(f'  - Active Wallets: {active_wallets}')
        self.stdout.write(f'  - Inactive Wallets: {inactive_wallets}')
        self.stdout.write(self.style.ERROR(f'Patients without Wallets: {patients_without_wallets}'))

        if patients_without_wallets > 0:
            self.stdout.write(self.style.NOTICE('\nTo create wallets for patients without one, you can consider running a command like: manage.py create_patient_wallets'))
        self.stdout.write(self.style.SUCCESS('--- Finished Checking Patient Wallets ---'))