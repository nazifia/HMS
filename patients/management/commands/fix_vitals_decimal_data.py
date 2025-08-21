from django.core.management.base import BaseCommand
from django.db import connection
from patients.models import Vitals
import logging

class Command(BaseCommand):
    help = 'Fix invalid decimal data in vitals table that causes InvalidOperation errors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )
        parser.add_argument(
            '--delete-invalid',
            action='store_true',
            help='Delete records with invalid decimal data instead of fixing them',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        delete_invalid = options['delete_invalid']
        
        self.stdout.write('Checking for invalid decimal data in vitals table...')
        
        # Get all vital records
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM patients_vitals ORDER BY id")
            vital_ids = [row[0] for row in cursor.fetchall()]
        
        invalid_records = []
        valid_count = 0
        
        for vital_id in vital_ids:
            try:
                vital = Vitals.objects.get(id=vital_id)
                # Test decimal field access
                _ = vital.temperature
                _ = vital.height
                _ = vital.weight
                _ = vital.bmi
                valid_count += 1
            except Exception as e:
                invalid_records.append((vital_id, str(e)))
                self.stdout.write(
                    self.style.WARNING(f'Invalid record found: ID {vital_id} - {e}')
                )
        
        self.stdout.write(f'Found {len(invalid_records)} invalid records out of {len(vital_ids)} total records')
        self.stdout.write(f'Valid records: {valid_count}')
        
        if not invalid_records:
            self.stdout.write(self.style.SUCCESS('No invalid decimal data found!'))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
            for vital_id, error in invalid_records:
                self.stdout.write(f'Would process record ID {vital_id}: {error}')
            return
        
        # Process invalid records
        fixed_count = 0
        deleted_count = 0
        
        for vital_id, error in invalid_records:
            try:
                if delete_invalid:
                    # Delete the invalid record
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM patients_vitals WHERE id = %s", [vital_id])
                    deleted_count += 1
                    self.stdout.write(f'Deleted invalid record ID {vital_id}')
                else:
                    # Try to fix by setting invalid decimal fields to NULL
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE patients_vitals 
                            SET temperature = NULL, height = NULL, weight = NULL, bmi = NULL 
                            WHERE id = %s
                        """, [vital_id])
                    fixed_count += 1
                    self.stdout.write(f'Fixed record ID {vital_id} by setting decimal fields to NULL')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to process record ID {vital_id}: {e}')
                )
        
        if delete_invalid:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {deleted_count} invalid records')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully fixed {fixed_count} invalid records')
            )
        
        self.stdout.write('Run the command again to verify all issues are resolved.')
