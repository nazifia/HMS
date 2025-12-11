from django.core.management.base import BaseCommand
from patients.models import SharedWallet, WalletMembership, Patient, PatientWallet, RetainershipPatient
from django.db import transaction
from decimal import Decimal

class Command(BaseCommand):
    help = 'Create a retainership shared wallet and link retainership patients to it'

    def add_arguments(self, parser):
        parser.add_argument('wallet_name', type=str, help='Name of the retainership wallet')
        parser.add_argument('retainership_reg_number', type=str, 
                          help='Retainership registration number')
        parser.add_argument('patient_ids', nargs='+', type=int, 
                          help='List of retainership patient IDs to add to the wallet')
        parser.add_argument('--primary', type=int, 
                          help='Primary patient ID for this wallet')
        parser.add_argument('--initial-balance', type=float, default=0.0,
                          help='Initial balance for the shared wallet')

    def handle(self, *args, **options):
        wallet_name = options['wallet_name']
        retainership_reg_number = options['retainership_reg_number']
        patient_ids = options['patient_ids']
        primary_patient_id = options['primary']
        initial_balance = Decimal(str(options['initial_balance']))

        try:
            with transaction.atomic():
                # Create the retainership shared wallet
                shared_wallet = SharedWallet.objects.create(
                    wallet_name=wallet_name,
                    wallet_type='retainership',
                    retainership_registration=retainership_reg_number,
                    balance=initial_balance
                )
                self.stdout.write(self.style.SUCCESS(f'Created retainership wallet: {shared_wallet}'))

                # Link retainership patients to the wallet
                for patient_id in patient_ids:
                    try:
                        patient = Patient.objects.get(id=patient_id)
                        
                        # Verify this is a retainership patient
                        try:
                            retainership_info = patient.retainership_info
                            self.stdout.write(self.style.SUCCESS(f'Confirmed retainership patient: {retainership_info}'))
                        except RetainershipPatient.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f'Patient {patient.get_full_name()} is not a retainership patient'))
                            continue
                        
                        # Get or create patient wallet
                        patient_wallet, created = PatientWallet.objects.get_or_create(
                            patient=patient,
                            defaults={'balance': Decimal('0.00')}
                        )
                        
                        # Link to shared wallet
                        patient_wallet.shared_wallet = shared_wallet
                        patient_wallet.save()
                        
                        # Create membership
                        is_primary = patient.id == primary_patient_id if primary_patient_id else False
                        membership = WalletMembership.objects.create(
                            wallet=shared_wallet,
                            patient=patient,
                            is_primary=is_primary
                        )
                        
                        self.stdout.write(self.style.SUCCESS(f'Linked retainership patient {patient.get_full_name()} to wallet (Primary: {is_primary})'))
                        
                    except Patient.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'Patient with ID {patient_id} not found'))

                # Set primary patient if not already set
                if primary_patient_id and not shared_wallet.members.filter(is_primary=True).exists():
                    try:
                        primary_patient = Patient.objects.get(id=primary_patient_id)
                        membership = WalletMembership.objects.get(
                            wallet=shared_wallet,
                            patient=primary_patient
                        )
                        membership.is_primary = True
                        membership.save()
                        self.stdout.write(self.style.SUCCESS(f'Set {primary_patient.get_full_name()} as primary member'))
                    except (Patient.DoesNotExist, WalletMembership.DoesNotExist):
                        self.stdout.write(self.style.WARNING('Could not set primary patient'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating retainership wallet: {str(e)}'))
            raise
