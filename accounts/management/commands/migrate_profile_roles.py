"""
Management command to migrate legacy CustomUserProfile.role assignments
to the new CustomUser.roles M2M field.

This command helps transition from the old single-role system (profile.role)
to the new multi-role system (user.roles).

Usage:
    python manage.py migrate_profile_roles
    python manage.py migrate_profile_roles --dry-run
    python manage.py migrate_profile_roles --role-mapping=mapping.json
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Role, CustomUserProfile
import json
import logging

logger = logging.getLogger(__name__)

# Default role mapping from old profile.role values to new Role names
DEFAULT_ROLE_MAPPING = {
    'admin': 'admin',
    'doctor': 'doctor',
    'nurse': 'nurse',
    'receptionist': 'receptionist',
    'pharmacist': 'pharmacist',
    'lab_technician': 'lab_technician',
    'radiology_staff': 'radiology_staff',
    'accountant': 'accountant',
    'health_record_officer': 'health_record_officer',
}


class Command(BaseCommand):
    help = 'Migrate legacy profile.role assignments to user.roles M2M'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes'
        )
        parser.add_argument(
            '--role-mapping',
            type=str,
            help='JSON file path with custom role mapping (overrides defaults)'
        )
        parser.add_argument(
            '--create-missing-roles',
            action='store_true',
            help='Automatically create roles that don\'t exist in the system'
        )
        parser.add_argument(
            '--clear-profile-roles',
            action='store_true',
            help='Clear profile.role field after successful migration'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        role_mapping_file = options.get('role_mapping')
        create_missing = options.get('create_missing_roles', False)
        clear_profile = options.get('clear_profile_roles', False)
        verbose = options.get('verbose', False)

        self.stdout.write('=' * 80)
        self.stdout.write('HMS Role Migration: Legacy profile.role → user.roles')
        self.stdout.write('=' * 80)

        # Load role mapping
        role_mapping = DEFAULT_ROLE_MAPPING.copy()
        if role_mapping_file:
            self.stdout.write(f'\nLoading custom role mapping from: {role_mapping_file}')
            try:
                with open(role_mapping_file, 'r') as f:
                    custom_mapping = json.load(f)
                role_mapping.update(custom_mapping)
                self.stdout.write(self.style.SUCCESS('Custom mapping loaded.'))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to load role mapping file: {e}')
                )
                return

        self.stdout.write(f'\nRole mapping ({len(role_mapping)} entries):')
        for old, new in sorted(role_mapping.items()):
            self.stdout.write(f'  {old:30s} → {new}')

        # Get all users with profile.role set
        profiles = CustomUserProfile.objects.filter(role__isnull=False).exclude(role='')
        total_profiles = profiles.count()

        if total_profiles == 0:
            self.stdout.write('\nNo profile.role assignments found. Migration not needed.')
            return

        self.stdout.write(f'\nFound {total_profiles} user profile(s) with role assignments.')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n*** DRY RUN MODE - No changes will be made ***'))

        # Validate roles exist
        self.stdout.write('\nValidating target roles...')
        missing_roles = set()
        available_roles = {}

        for new_role_name in set(role_mapping.values()):
            try:
                role = Role.objects.get(name=new_role_name)
                available_roles[new_role_name] = role
            except Role.DoesNotExist:
                missing_roles.add(new_role_name)

        if missing_roles:
            self.stdout.write(
                self.style.WARNING(f'Missing roles in database: {len(missing_roles)}')
            )
            for role_name in sorted(missing_roles):
                self.stdout.write(f'  - {role_name}')

            if create_missing:
                self.stdout.write(self.style.SUCCESS('\nCreating missing roles...'))
                for role_name in sorted(missing_roles):
                    role = Role.objects.create(name=role_name)
                    available_roles[role_name] = role
                    self.stdout.write(f'  Created role: {role_name}')
            else:
                self.stdout.write(
                    self.style.WARNING('\nUse --create-missing-roles to create these roles automatically.')
                )
                if not verbose:
                    self.stdout.write('Skipping profiles that map to missing roles.')
                # Filter out profiles with unmapped roles if not creating
        else:
            self.stdout.write(self.style.SUCCESS('All required roles exist.'))

        # Process each profile
        stats = {
            'processed': 0,
            'migrated': 0,
            'skipped': 0,
            'errors': 0,
        }

        for profile in profiles:
            user = profile.user
            old_role = profile.role

            stats['processed'] += 1

            # Find new role name
            new_role_name = role_mapping.get(old_role)
            if not new_role_name:
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping user {user.username}: No mapping for role "{old_role}"'
                        )
                    )
                stats['skipped'] += 1
                continue

            # Check if role exists
            role = available_roles.get(new_role_name)
            if not role:
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping user {user.username}: Role "{new_role_name}" not found'
                        )
                    )
                stats['skipped'] += 1
                continue

            # Perform migration
            if dry_run:
                if verbose:
                    self.stdout.write(
                        f'[DRY RUN] Would assign role "{new_role_name}" to user {user.username}'
                    )
                stats['migrated'] += 1
            else:
                try:
                    user.roles.add(role)

                    if clear_profile:
                        profile.role = ''
                        profile.save()
                        if verbose:
                            self.stdout.write(
                                f'Migrated: {user.username} - {old_role} → {new_role_name} '
                                f'(profile.role cleared)'
                            )
                    else:
                        if verbose:
                            self.stdout.write(
                                f'Migrated: {user.username} - {old_role} → {new_role_name} '
                                f'(profile.role kept for backward compatibility)'
                            )

                    stats['migrated'] += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error migrating user {user.username}: {e}')
                    )
                    stats['errors'] += 1

        # Summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('MIGRATION SUMMARY')
        self.stdout.write('=' * 80)
        self.stdout.write(f'Total profiles examined: {total_profiles}')
        self.stdout.write(f'Profiles processed:     {stats["processed"]}')
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated:  {stats["migrated"]}'))
        if stats['skipped'] > 0:
            self.stdout.write(self.style.WARNING(f'Skipped:               {stats["skipped"]}'))
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f'Errors:                {stats["errors"]}'))

        if dry_run:
            self.stdout.write(self.style.WARNING('\n*** DRY RUN COMPLETE - No changes made ***'))
        else:
            self.stdout.write(self.style.SUCCESS('\nMigration completed successfully.'))

            if not clear_profile:
                self.stdout.write(
                    '\nNote: profile.role fields were NOT cleared for backward compatibility. '
                    'Run with --clear-profile-roles to clear them after verification.'
                )

            self.stdout.write(
                '\nNext steps:'
            )
            self.stdout.write('  1. Verify user role assignments in admin interface')
            self.stdout.write('  2. Test permission checks across the application')
            self.stdout.write('  3. Run: python manage.py validate_permissions')
            self.stdout.write('  4. Once verified, run with --clear-profile-roles if desired')
