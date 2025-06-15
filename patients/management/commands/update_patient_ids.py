from django.core.management.base import BaseCommand
from django.db import transaction
from patients.models import Patient
from django.utils import timezone
import re


class Command(BaseCommand):
    help = 'Update existing patient IDs to remove letters and hyphens, making them numeric only'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if some IDs might conflict',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write(
            self.style.SUCCESS('Starting Patient ID Update Process')
        )
        self.stdout.write('=' * 60)

        # Find all patients with old format IDs (containing letters or hyphens)
        old_format_patients = Patient.objects.filter(
            patient_id__regex=r'[A-Za-z\-]'
        ).order_by('registration_date')

        if not old_format_patients.exists():
            self.stdout.write(
                self.style.SUCCESS('✅ No patients found with old format IDs. All IDs are already numeric!')
            )
            return

        self.stdout.write(f"Found {old_format_patients.count()} patients with old format IDs")
        self.stdout.write("-" * 40)

        # Track updates
        updated_count = 0
        error_count = 0
        id_mapping = {}

        with transaction.atomic():
            for patient in old_format_patients:
                old_id = patient.patient_id
                
                # Generate new numeric ID based on registration date
                reg_date = patient.registration_date
                year = reg_date.year
                month = reg_date.month
                prefix = f"{year}{month:02d}"

                # Find the next available number for this prefix
                existing_ids = Patient.objects.filter(
                    patient_id__startswith=prefix,
                    patient_id__regex=r'^\d+$'  # Only numeric IDs
                ).values_list('patient_id', flat=True)

                # Extract numbers and find the next available
                existing_numbers = []
                for existing_id in existing_ids:
                    try:
                        number = int(existing_id[len(prefix):])
                        existing_numbers.append(number)
                    except (ValueError, IndexError):
                        continue

                # Find next available number
                if existing_numbers:
                    new_number = max(existing_numbers) + 1
                else:
                    new_number = 1

                new_id = f"{prefix}{new_number:04d}"

                # Check for conflicts
                if Patient.objects.filter(patient_id=new_id).exists() and not force:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Conflict: {old_id} -> {new_id} (ID already exists)")
                    )
                    error_count += 1
                    continue

                # Store mapping
                id_mapping[old_id] = new_id

                if dry_run:
                    self.stdout.write(f"🔄 Would update: {old_id} -> {new_id}")
                else:
                    try:
                        patient.patient_id = new_id
                        patient.save(update_fields=['patient_id'])
                        self.stdout.write(
                            self.style.SUCCESS(f"✅ Updated: {old_id} -> {new_id}")
                        )
                        updated_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"❌ Error updating {old_id}: {str(e)}")
                        )
                        error_count += 1

            if dry_run:
                # Rollback transaction for dry run
                transaction.set_rollback(True)

        # Summary
        self.stdout.write("=" * 60)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"🔍 DRY RUN COMPLETE - No changes made")
            )
            self.stdout.write(f"Would update: {len(id_mapping)} patients")
            self.stdout.write(f"Potential errors: {error_count}")
            self.stdout.write("\nTo apply changes, run: python manage.py update_patient_ids")
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✅ UPDATE COMPLETE")
            )
            self.stdout.write(f"Successfully updated: {updated_count} patients")
            if error_count > 0:
                self.stdout.write(
                    self.style.ERROR(f"Errors encountered: {error_count}")
                )

        # Show some examples of the mapping
        if id_mapping:
            self.stdout.write("\nExample ID mappings:")
            self.stdout.write("-" * 30)
            for i, (old, new) in enumerate(list(id_mapping.items())[:5]):
                self.stdout.write(f"{old} -> {new}")
            if len(id_mapping) > 5:
                self.stdout.write(f"... and {len(id_mapping) - 5} more")
