from django.core.management.base import BaseCommand
from django.db import transaction
from patients.models import Patient


class Command(BaseCommand):
    help = 'Activate or deactivate patients by ID or activate all inactive patients'

    def add_arguments(self, parser):
        parser.add_argument(
            '--patient-id',
            type=str,
            help='Specific patient ID to activate/deactivate',
        )
        parser.add_argument(
            '--all-inactive',
            action='store_true',
            help='Activate all currently inactive patients',
        )
        parser.add_argument(
            '--deactivate',
            action='store_true',
            help='Deactivate the specified patient (default is activate)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        patient_id = options['patient_id']
        all_inactive = options['all_inactive']
        deactivate = options['deactivate']
        dry_run = options['dry_run']

        if not patient_id and not all_inactive:
            self.stdout.write(
                self.style.ERROR('You must specify either --patient-id or --all-inactive')
            )
            return

        if patient_id and all_inactive:
            self.stdout.write(
                self.style.ERROR('You cannot use both --patient-id and --all-inactive')
            )
            return

        self.stdout.write(
            self.style.SUCCESS('Patient Activation/Deactivation Tool')
        )
        self.stdout.write('=' * 50)

        with transaction.atomic():
            if patient_id:
                # Handle specific patient
                try:
                    patient = Patient.objects.get(patient_id=patient_id)
                    old_status = patient.is_active
                    new_status = not deactivate  # True if activating, False if deactivating
                    
                    if old_status == new_status:
                        action = "active" if new_status else "inactive"
                        self.stdout.write(
                            self.style.WARNING(f'Patient {patient_id} is already {action}')
                        )
                        return
                    
                    if dry_run:
                        action = "deactivate" if deactivate else "activate"
                        self.stdout.write(f"🔄 Would {action}: {patient.get_full_name()} ({patient_id})")
                    else:
                        patient.is_active = new_status
                        patient.save(update_fields=['is_active'])
                        action = "deactivated" if deactivate else "activated"
                        status_badge = "❌" if deactivate else "✅"
                        self.stdout.write(
                            self.style.SUCCESS(f'{status_badge} {action.title()}: {patient.get_full_name()} ({patient_id})')
                        )
                        
                except Patient.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'Patient with ID {patient_id} not found')
                    )
                    return

            elif all_inactive:
                # Handle all inactive patients
                if deactivate:
                    self.stdout.write(
                        self.style.ERROR('Cannot use --deactivate with --all-inactive')
                    )
                    return
                
                inactive_patients = Patient.objects.filter(is_active=False)
                
                if not inactive_patients.exists():
                    self.stdout.write(
                        self.style.SUCCESS('✅ No inactive patients found. All patients are already active!')
                    )
                    return
                
                self.stdout.write(f"Found {inactive_patients.count()} inactive patients:")
                self.stdout.write("-" * 40)
                
                activated_count = 0
                for patient in inactive_patients:
                    if dry_run:
                        self.stdout.write(f"🔄 Would activate: {patient.get_full_name()} ({patient.patient_id})")
                    else:
                        patient.is_active = True
                        patient.save(update_fields=['is_active'])
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Activated: {patient.get_full_name()} ({patient.patient_id})')
                        )
                        activated_count += 1
                
                if dry_run:
                    transaction.set_rollback(True)
                    self.stdout.write(
                        self.style.WARNING(f'\n🔍 DRY RUN - Would activate {inactive_patients.count()} patients')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'\n🎉 Successfully activated {activated_count} patients!')
                    )

        # Show current status summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('Current Patient Status Summary:')
        self.stdout.write('-' * 30)
        
        active_count = Patient.objects.filter(is_active=True).count()
        inactive_count = Patient.objects.filter(is_active=False).count()
        total_count = Patient.objects.count()
        
        self.stdout.write(f'✅ Active patients: {active_count}')
        self.stdout.write(f'❌ Inactive patients: {inactive_count}')
        self.stdout.write(f'📊 Total patients: {total_count}')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nTo apply changes, run the command without --dry-run')
            )
