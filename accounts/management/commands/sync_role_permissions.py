"""
Management command to sync role permissions with canonical definitions.

This command ensures that role permissions in the database match the
canonical PERMISSION_DEFINITIONS and ROLE_PERMISSIONS specifications.

Usage:
    python manage.py sync_role_permissions
    python manage.py sync_role_permissions --fix
    python manage.py sync_role_permissions --dry-run
    python manage.py sync_role_permissions --role=doctor,nurse
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from accounts.models import Role
from accounts.permissions import (
    PERMISSION_DEFINITIONS,
    ROLE_PERMISSIONS,
    get_django_permission,
)
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync role permissions with canonical definitions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix mismatches'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes'
        )
        parser.add_argument(
            '--role',
            type=str,
            help='Comma-separated list of specific roles to sync (default: all)'
        )
        parser.add_argument(
            '--create-missing-permissions',
            action='store_true',
            help='Create missing custom permissions in the database (if possible)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )

    def handle(self, *args, **options):
        fix_mode = options['fix']
        dry_run = options['dry_run']
        role_filter = options.get('role')
        create_missing = options.get('create_missing_permissions', False)
        verbose = options.get('verbose', False)

        self.stdout.write('=' * 80)
        self.stdout.write('HMS Role Permission Sync')
        self.stdout.write('=' * 80)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made\n'))
        if fix_mode:
            self.stdout.write(self.style.WARNING('FIX MODE - Changes will be applied\n'))

        # Get all Django permissions once
        django_perms = {}
        all_perms = Permission.objects.all().select_related('content_type')
        for perm in all_perms:
            key = f"{perm.content_type.app_label}.{perm.codename}"
            django_perms[key] = perm

        # Determine which roles to process
        if role_filter:
            role_names = [r.strip() for r in role_filter.split(',')]
            roles_to_process = []
            for name in role_names:
                try:
                    role = Role.objects.get(name=name)
                    roles_to_process.append(role)
                except Role.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Role "{name}" does not exist, skipping.')
                    )
        else:
            roles_to_process = list(Role.objects.all())

        self.stdout.write(f'Processing {len(roles_to_process)} roles\n')

        # Statistics
        stats = {
            'roles_checked': 0,
            'permissions_added': 0,
            'permissions_removed': 0,
            'missing_custom_perms': set(),
            'roles_with_issues': 0,
        }

        for role in roles_to_process:
            role_name = role.name
            self.stdout.write(f'Role: {role_name}')
            self.stdout.write('-' * 40)

            # Get expected permissions for this role from ROLE_PERMISSIONS
            if role_name not in ROLE_PERMISSIONS:
                self.stdout.write(
                    self.style.WARNING(f'  Role not in ROLE_PERMISSIONS, skipping')
                )
                continue

            expected_permission_keys = ROLE_PERMISSIONS[role_name]['permissions']

            # Convert custom keys to Django Permission objects
            expected_django_perms = set()
            missing_custom_keys = []

            for custom_key in expected_permission_keys:
                django_codename = get_django_permission(custom_key)

                # Check if Django permission exists
                if django_codename in django_perms:
                    expected_django_perms.add(django_perms[django_codename])
                else:
                    missing_custom_keys.append(custom_key)
                    stats['missing_custom_perms'].add(custom_key)

            # Get current permissions
            current_permissions = set(role.permissions.all())

            # Calculate differences
            to_add = expected_django_perms - current_permissions
            to_remove = current_permissions - expected_django_perms

            stats['roles_checked'] += 1

            # Report findings
            if to_add:
                self.stdout.write(
                    self.style.WARNING(f'  Missing {len(to_add)} permission(s):')
                )
                for perm in sorted(to_add, key=lambda p: p.codename)[:5]:
                    self.stdout.write(f'    + {perm.content_type.app_label}.{perm.codename}')
                if len(to_add) > 5:
                    self.stdout.write(f'    ... and {len(to_add) - 5} more')

            if to_remove:
                self.stdout.write(
                    self.style.WARNING(f'  Extra {len(to_remove)} permission(s):')
                )
                for perm in sorted(to_remove, key=lambda p: p.codename)[:5]:
                    self.stdout.write(f'    - {perm.content_type.app_label}.{perm.codename}')
                if len(to_remove) > 5:
                    self.stdout.write(f'    ... and {len(to_remove) - 5} more')

            if to_add or to_remove:
                stats['roles_with_issues'] += 1

            # Apply fixes if requested
            if fix_mode and not dry_run:
                if to_add:
                    role.permissions.add(*to_add)
                    stats['permissions_added'] += len(to_add)
                    if verbose:
                        self.stdout.write(
                            self.style.SUCCESS(f'  Added {len(to_add)} permission(s)')
                        )

                if to_remove:
                    role.permissions.remove(*to_remove)
                    stats['permissions_removed'] += len(to_remove)
                    if verbose:
                        self.stdout.write(
                            self.style.SUCCESS(f'  Removed {len(to_remove)} permission(s)')
                        )
            elif dry_run and (to_add or to_remove):
                self.stdout.write(
                    self.style.WARNING('  [DRY RUN] Would sync permissions')
                )

            if not to_add and not to_remove:
                self.stdout.write(self.style.SUCCESS('  ✓ Permissions match definition'))

            self.stdout.write('')  # Blank line between roles

        # Report missing custom permissions
        if stats['missing_custom_perms']:
            self.stdout.write('=' * 80)
            self.stdout.write('MISSING CUSTOM PERMISSIONS')
            self.stdout.write('=' * 80)
            self.stdout.write(
                f'{len(stats["missing_custom_perms"])} custom permissions not found in database:\n'
            )
            for custom_key in sorted(stats['missing_custom_perms']):
                info = PERMISSION_DEFINITIONS.get(custom_key, {})
                django_codename = info.get('django_codename', 'N/A')
                self.stdout.write(f'  {custom_key:30s} -> {django_codename}')

            if create_missing and fix_mode and not dry_run:
                self.stdout.write('\nNote: Custom permissions must exist in Django auth_permission table.')
                self.stdout.write('They are typically created by Django when you run makemigrations/migrate.')
                self.stdout.write('Ensure all apps have been migrated before syncing permissions.')

        # Summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('SYNC SUMMARY')
        self.stdout.write('=' * 80)
        self.stdout.write(f'Roles checked:                 {stats["roles_checked"]}')
        self.stdout.write(f'Roles with issues:             {stats["roles_with_issues"]}')
        self.stdout.write(
            self.style.SUCCESS(f'Permissions that would be added: {stats["permissions_added"]}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Permissions that would be removed: {stats["permissions_removed"]}')
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a dry run. No changes applied.'))
        if fix_mode and not dry_run:
            self.stdout.write(self.style.SUCCESS('\nSync completed successfully!'))
            self.stdout.write('\nNext steps:')
            self.stdout.write('  1. Test permissions for affected roles')
            self.stdout.write('  2. Run: python manage.py validate_permissions')
            self.stdout.write('  3. Review user role assignments')

        if stats['roles_with_issues'] == 0 and not stats['missing_custom_perms']:
            self.stdout.write(self.style.SUCCESS('\n✅ All role permissions are in sync!'))
