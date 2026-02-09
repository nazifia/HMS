"""
Management command to validate the role and permission system.

Performs comprehensive checks for common configuration issues and
reports on the health of the RBAC system.

Usage:
    python manage.py validate_permissions
    python manage.py validate_permissions --fix  # attempt automatic fixes
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Role, CustomUserProfile
from accounts.permissions import (
    PERMISSION_DEFINITIONS,
    ROLE_PERMISSIONS,
    validate_permission_definitions,
)
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = 'Validate role and permission configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to automatically fix certain issues'
        )
        parser.add_argument(
            '--checks',
            type=str,
            help='Comma-separated list of checks to run (e.g., "circular,orphans,users")'
        )
        parser.add_argument(
            '--exclude',
            type=str,
            help='Comma-separated list of checks to skip'
        )

    def handle(self, *args, **options):
        fix_mode = options['fix']
        checks_filter = options.get('checks')
        exclude_checks = options.get('exclude', '')

        # Determine which checks to run
        all_checks = {
            'definitions': self.check_permission_definitions,
            'circular': self.check_circular_references,
            'orphans': self.check_orphaned_roles,
            'users': self.check_user_roles,
            'legacy': self.check_legacy_profile_roles,
            'missing': self.check_missing_default_roles,
            'permissions': self.check_role_permission_consistency,
        }

        if checks_filter:
            checks_to_run = [c for c in checks_filter.split(',') if c in all_checks]
        else:
            checks_to_run = list(all_checks.keys())

        exclude_list = [s for s in exclude_checks.split(',') if s] if exclude_checks else []
        checks_to_run = [c for c in checks_to_run if c not in exclude_list]

        self.stdout.write('=' * 80)
        self.stdout.write('HMS Role & Permission Validation')
        self.stdout.write('=' * 80)

        if fix_mode:
            self.stdout.write(self.style.WARNING('FIX MODE: Attempting automatic fixes\n'))

        total_issues = 0
        fixed_issues = 0

        for check_name in checks_to_run:
            self.stdout.write(f'\n{"="*80}')
            self.stdout.write(f'CHECK: {check_name.upper()}')
            self.stdout.write('=' * 80)

            try:
                issues, fixed = all_checks[check_name](fix_mode)
                total_issues += issues
                fixed_issues += fixed
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error running check {check_name}: {e}')
                )
                logger.exception(f'Error in check {check_name}')

        # Final summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('VALIDATION SUMMARY')
        self.stdout.write('=' * 80)
        self.stdout.write(f'Total issues found: {total_issues}')
        if fix_mode:
            self.stdout.write(self.style.SUCCESS(f'Issues fixed: {fixed_issues}'))
            if total_issues > fixed_issues:
                remaining = total_issues - fixed_issues
                self.stdout.write(self.style.WARNING(f'Remaining issues: {remaining}'))
        else:
            self.stdout.write(self.style.SUCCESS('Run with --fix to attempt automatic fixes'))

        if total_issues == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ All checks passed!'))
        else:
            self.stdout.write(self.style.ERROR(f'\n❌ {total_issues} issue(s) found'))

        # Recommendations
        if total_issues > 0:
            self.stdout.write('\nRecommendations:')
            if any(c in checks_to_run for c in ['circular', 'orphans']):
                self.stdout.write('  - Review role hierarchy in admin interface')
            if 'users' in checks_to_run:
                self.stdout.write('  - Assign appropriate roles to users')
            if 'legacy' in checks_to_run:
                self.stdout.write('  - Run: python manage.py migrate_profile_roles')
            if 'permissions' in checks_to_run:
                self.stdout.write('  - Run: python manage.py sync_role_permissions --fix')
            if 'definitions' in checks_to_run:
                self.stdout.write('  - Update PERMISSION_DEFINITIONS in accounts/permissions.py')

    def check_permission_definitions(self, fix_mode=False):
        """Validate structural integrity of PERMISSION_DEFINITIONS."""
        issues = 0
        fixed = 0

        is_valid, errors, warnings_list = validate_permission_definitions()

        if not is_valid:
            self.stdout.write(self.style.ERROR('Permission definition errors:'))
            for error in errors:
                self.stdout.write(self.style.ERROR(f'  ✗ {error}'))
                issues += 1
        else:
            self.stdout.write(self.style.SUCCESS('Permission definitions are structurally valid.'))

        if warnings_list:
            self.stdout.write(self.style.WARNING('Warnings:'))
            for warning in warnings_list:
                self.stdout.write(self.style.WARNING(f'  ⚠ {warning}'))
                issues += 1

        # Check against database
        from django.contrib.auth.models import Permission

        db_perms = set()
        for perm in Permission.objects.all():
            db_perms.add(f"{perm.content_type.app_label}.{perm.codename}")

        defined_perms = set()
        for custom_key, defn in PERMISSION_DEFINITIONS.items():
            defined_perms.add(defn['django_codename'])

        missing = defined_perms - db_perms
        extra = db_perms - defined_perms

        if missing:
            self.stdout.write(self.style.WARNING(f'\n{len(missing)} defined permissions missing from database:'))
            for perm in sorted(missing)[:10]:
                self.stdout.write(f'  - {perm}')
            if len(missing) > 10:
                self.stdout.write(f'  ... and {len(missing) - 10} more')
            issues += len(missing)

        return issues, fixed

    def check_circular_references(self, fix_mode=False):
        """Check for circular references in role hierarchy."""
        issues = 0
        fixed = 0

        roles = Role.objects.all()
        circular_roles = []

        for role in roles:
            if role.check_circular_reference(role.parent):
                circular_roles.append(role)
                issues += 1

        if circular_roles:
            self.stdout.write(self.style.ERROR('Circular references detected:'))
            for role in circular_roles:
                self.stdout.write(f'  ✗ Role "{role.name}" has circular parent reference')
                if fix_mode:
                    # Auto-fix: remove the parent that creates the circle
                    # This is a simple fix - might need manual review
                    role.parent = None
                    role.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Fixed: Removed parent from {role.name}')
                    )
                    fixed += 1
        else:
            self.stdout.write(self.style.SUCCESS('No circular references found.'))

        return issues, fixed

    def check_orphaned_roles(self, fix_mode=False):
        """Check for roles with no users and no children (potential cleanup candidates)."""
        issues = 0
        fixed = 0

        roles = Role.objects.all()
        orphaned = []

        for role in roles:
            user_count = role.customuser_roles.count()
            child_count = role.children.count()

            if user_count == 0 and child_count == 0:
                orphaned.append(role)
                issues += 1

        if orphaned:
            self.stdout.write(self.style.WARNING('Orphaned roles (no users, no children):'))
            for role in orphaned:
                self.stdout.write(f'  ⚠ {role.name} (created: {role.created_at if hasattr(role, "created_at") else "N/A"})')
                if fix_mode:
                    # Ask for confirmation or just list them
                    # Don't auto-delete in fix mode - too dangerous
                    pass

            if fix_mode:
                self.stdout.write(
                    self.style.WARNING(
                        f'  To delete {len(orphaned)} orphaned roles, run with --delete-orphans flag (not implemented)'
                    )
                )
        else:
            self.stdout.write(self.style.SUCCESS('No orphaned roles found.'))

        return issues, fixed

    def check_user_roles(self, fix_mode=False):
        """Check for users with no roles assigned."""
        issues = 0
        fixed = 0

        # Get all active users
        users = User.objects.filter(is_active=True)

        users_without_roles = []
        for user in users:
            roles = user.roles.all()
            if not roles.exists():
                # Check legacy profile.role as well
                has_profile_role = hasattr(user, 'profile') and user.profile.role
                if not has_profile_role:
                    users_without_roles.append(user)
                    issues += 1

        if users_without_roles:
            self.stdout.write(self.style.ERROR(f'Users with no roles: {len(users_without_roles)}'))
            for user in users_without_roles[:10]:
                self.stdout.write(f'  ✗ {user.username} ({user.get_full_name()})')
            if len(users_without_roles) > 10:
                self.stdout.write(f'  ... and {len(users_without_roles) - 10} more')

            if fix_mode:
                self.stdout.write(
                    self.style.WARNING(
                        '\nCannot auto-assign roles without knowing which role is appropriate.'
                    )
                )
        else:
            self.stdout.write(self.style.SUCCESS('All active users have at least one role.'))

        return issues, fixed

    def check_legacy_profile_roles(self, fix_mode=False):
        """Check for any remaining profile.role assignments."""
        issues = 0
        fixed = 0

        profiles_with_roles = CustomUserProfile.objects.filter(
            role__isnull=False
        ).exclude(role='')

        count = profiles_with_roles.count()

        if count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Legacy profile.role assignments found: {count}'
                )
            )

            # Show unique role values
            unique_roles = set(
                profiles_with_roles.values_list('role', flat=True)
            )
            self.stdout.write('Unique legacy role values:')
            for role in sorted(unique_roles):
                user_count = profiles_with_roles.filter(role=role).count()
                self.stdout.write(f'  - {role}: {user_count} user(s)')

            if fix_mode:
                self.stdout.write(
                    self.style.SUCCESS(
                        '\nThese users likely have roles already assigned via user.roles. '
                        'Consider running with --clear-profile-roles in migrate_profile_roles command.'
                    )
                )
        else:
            self.stdout.write(self.style.SUCCESS('No legacy profile.role assignments found.'))

        return count, fixed

    def check_missing_default_roles(self, fix_mode=False):
        """Check if all expected default roles exist in the system."""
        from accounts.permissions import ROLE_PERMISSIONS

        issues = 0
        fixed = 0

        expected_roles = set(ROLE_PERMISSIONS.keys())
        existing_roles = set(Role.objects.values_list('name', flat=True))

        missing_roles = expected_roles - existing_roles

        if missing_roles:
            self.stdout.write(self.style.ERROR(f'Missing default roles: {len(missing_roles)}'))
            for role in sorted(missing_roles):
                self.stdout.write(f'  ✗ {role}')

            if fix_mode:
                self.stdout.write('\nCreating missing default roles...')
                from accounts.permissions import ROLE_PERMISSIONS
                for role_name in sorted(missing_roles):
                    role_data = ROLE_PERMISSIONS.get(role_name, {})
                    Role.objects.create(
                        name=role_name,
                        description=role_data.get('description', '')
                    )
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Created role: {role_name}'))
                    fixed += 1
                    issues -= 1  # We fixed this one
        else:
            self.stdout.write(self.style.SUCCESS('All default roles exist.'))

        return len(missing_roles), fixed

    def check_role_permission_consistency(self, fix_mode=False):
        """Check if role permissions match ROLE_PERMISSIONS definitions."""
        issues = 0
        fixed = 0

        self.stdout.write('Checking role permission consistency...')

        for role_name, role_data in ROLE_PERMISSIONS.items():
            try:
                role = Role.objects.get(name=role_name)
            except Role.DoesNotExist:
                continue

            expected_permissions = role_data.get('permissions', [])
            current_permissions = set(
                role.permissions.values_list('codename', flat=True)
            )

            # Convert expected custom keys to Django codenames
            from accounts.permissions import get_django_permission
            expected_django_codenames = set()
            for custom_key in expected_permissions:
                django_codename = get_django_permission(custom_key)
                if '.' in django_codename:
                    codename = django_codename.split('.')[1]
                else:
                    codename = django_codename
                expected_django_codenames.add(codename)

            missing_perms = expected_django_codenames - current_permissions
            extra_perms = current_permissions - expected_django_codenames

            if missing_perms:
                self.stdout.write(
                    self.style.WARNING(f'Role "{role_name}" missing permissions:')
                )
                for perm in sorted(missing_perms)[:5]:
                    self.stdout.write(f'  - {perm}')
                if len(missing_perms) > 5:
                    self.stdout.write(f'  ... and {len(missing_perms) - 5} more')
                issues += len(missing_perms)

            if extra_perms:
                self.stdout.write(
                    self.style.WARNING(f'Role "{role_name}" has extra permissions:')
                )
                for perm in sorted(extra_perms)[:5]:
                    self.stdout.write(f'  + {perm}')
                if len(extra_perms) > 5:
                    self.stdout.write(f'  ... and {len(extra_perms) - 5} more')
                issues += len(extra_perms)

            if not missing_perms and not extra_perms:
                if fix_mode or True:  # Always show success in summary
                    self.stdout.write(self.style.SUCCESS(f'✓ Role "{role_name}" permissions OK'))

        return issues, fixed
