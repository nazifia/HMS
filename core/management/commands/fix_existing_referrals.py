"""
Management command to fix existing referrals that may not have proper
department associations. This ensures all referrals will be visible on
destination department dashboards.

Usage:
    python manage.py fix_existing_referrals [--dry-run]
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from consultations.models import Referral
from accounts.models import Department
from consultations.referral_mappings import (
    get_department_for_unit,
    get_department_for_specialty
)


class Command(BaseCommand):
    help = 'Fix existing referrals to ensure they have proper department associations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        self.stdout.write("Analyzing existing referrals...")
        
        # Get all referrals that need fixing
        referrals = Referral.objects.all().select_related('referred_to_department')
        
        total_referrals = referrals.count()
        fixed_count = 0
        already_correct = 0
        errors = []
        
        self.stdout.write(f"Total referrals found: {total_referrals}")
        
        for referral in referrals:
            try:
                result = self.fix_referral(referral, dry_run)
                if result == 'fixed':
                    fixed_count += 1
                elif result == 'already_correct':
                    already_correct += 1
                    
            except Exception as e:
                error_msg = f"Error processing referral {referral.id}: {str(e)}"
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(error_msg))
        
        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("SUMMARY"))
        self.stdout.write("="*60)
        self.stdout.write(f"Total referrals processed: {total_referrals}")
        self.stdout.write(f"Already correct: {already_correct}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f"Would fix: {fixed_count}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Fixed: {fixed_count}"))
        
        if errors:
            self.stdout.write(self.style.ERROR(f"Errors: {len(errors)}"))
            for error in errors[:5]:  # Show first 5 errors
                self.stdout.write(self.style.ERROR(f"  - {error}"))
        
        self.stdout.write("\nDone!")
    
    def fix_referral(self, referral, dry_run):
        """
        Fix a single referral's department association.
        
        Returns:
            'fixed' - if changes were made
            'already_correct' - if no changes needed
        """
        needs_save = False
        
        # Case 1: Referral has unit but no department - map unit to department
        if referral.referred_to_unit and not referral.referred_to_department:
            dept_name = get_department_for_unit(referral.referred_to_unit)
            if dept_name:
                try:
                    department = Department.objects.get(name__iexact=dept_name)
                    if not dry_run:
                        referral.referred_to_department = department
                        needs_save = True
                    self.stdout.write(
                        f"  Referral {referral.id}: Mapping unit '{referral.referred_to_unit}' "
                        f"to department '{department.name}'"
                    )
                except Department.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Referral {referral.id}: Department '{dept_name}' not found "
                            f"for unit '{referral.referred_to_unit}'"
                        )
                    )
        
        # Case 2: Referral has specialty but no department - map specialty to department
        elif referral.referred_to_specialty and not referral.referred_to_department:
            dept_name = get_department_for_specialty(
                referral.referred_to_specialty,
                preferred_unit=referral.referred_to_unit
            )
            if dept_name:
                try:
                    department = Department.objects.get(name__iexact=dept_name)
                    if not dry_run:
                        referral.referred_to_department = department
                        needs_save = True
                    self.stdout.write(
                        f"  Referral {referral.id}: Mapping specialty '{referral.referred_to_specialty}' "
                        f"to department '{department.name}'"
                    )
                except Department.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Referral {referral.id}: Department '{dept_name}' not found "
                            f"for specialty '{referral.referred_to_specialty}'"
                        )
                    )
        
        # Case 3: Referral has department name in unit field but no department set
        elif referral.referred_to_unit and not referral.referred_to_department:
            try:
                # Try to find department by name (case-insensitive)
                department = Department.objects.get(name__iexact=referral.referred_to_unit)
                if not dry_run:
                    referral.referred_to_department = department
                    needs_save = True
                self.stdout.write(
                    f"  Referral {referral.id}: Setting department from unit name "
                    f"'{referral.referred_to_unit}' -> '{department.name}'"
                )
            except Department.DoesNotExist:
                pass  # No matching department found
        
        # Case 4: Referral has department name in specialty field but no department set
        elif referral.referred_to_specialty and not referral.referred_to_department:
            try:
                # Try to find department by name (case-insensitive)
                department = Department.objects.get(name__iexact=referral.referred_to_specialty)
                if not dry_run:
                    referral.referred_to_department = department
                    needs_save = True
                self.stdout.write(
                    f"  Referral {referral.id}: Setting department from specialty name "
                    f"'{referral.referred_to_specialty}' -> '{department.name}'"
                )
            except Department.DoesNotExist:
                pass  # No matching department found
        
        # Save changes if not in dry-run mode
        if needs_save and not dry_run:
            referral.save(update_fields=['referred_to_department'])
            return 'fixed'
        elif needs_save and dry_run:
            return 'fixed'
        
        return 'already_correct'
