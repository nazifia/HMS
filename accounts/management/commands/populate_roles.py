from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import Role
from accounts.permissions import (
    ROLE_PERMISSIONS,
    PERMISSION_DEFINITIONS,
    get_django_permission,
    validate_permission_definitions,
)
import logging
import warnings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate HMS system with initial roles and permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate permission definitions without making changes'
        )
        parser.add_argument(
            '--list-permissions',
            action='store_true',
            help='List all available permissions and their assignment status'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually creating/updating'
        )
        parser.add_argument(
            '--skip-permissions',
            action='store_true',
            help='Create/update roles only, without assigning permissions'
        )

    def handle(self, *args, **options):
        validate_only = options.get('validate', False)
        list_permissions = options.get('list_permissions', False)
        dry_run = options.get('dry_run', False)
        skip_permissions = options.get('skip_permissions', False)

        if validate_only:
            self._validate_permissions()
            return

        if list_permissions:
            self._list_permissions()
            return

        self.stdout.write(self.style.SUCCESS('Starting HMS role population...'))

        # Validate permission definitions first
        is_valid, errors, warnings_list = validate_permission_definitions()
        if not is_valid:
            self.stdout.write(self.style.ERROR('Permission definition validation failed:'))
            for error in errors:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
            self.stdout.write(self.style.WARNING('Please fix these errors before proceeding.'))
            return
        else:
            self.stdout.write(self.style.SUCCESS('Permission definitions validated successfully.'))

        # Get all available Django permissions once
        available_permissions = {}
        all_django_perms = Permission.objects.all().select_related('content_type')
        for perm in all_django_perms:
            key = f"{perm.content_type.app_label}.{perm.codename}"
            available_permissions[key] = perm

        self.stdout.write(f'Found {len(available_permissions)} permissions in database')

        # Process roles from ROLE_PERMISSIONS (using custom permission keys)
        roles_data = ROLE_PERMISSIONS.copy()

        # Add admin role with empty permissions (superuser gets all)
        roles_data['admin'] = {
            'description': 'System Administrator - Full access to all HMS modules and user management',
            'permissions': []
        }

        stats = {
            'roles_created': 0,
            'roles_updated': 0,
            'permissions_assigned': 0,
            'missing_permissions': set(),
        }

        for role_name, role_data in roles_data.items():
            if dry_run:
                self.stdout.write(f"[DRY RUN] Would process role: {role_name}")
                continue

            # Create or update role
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={'description': role_data['description']}
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'Created role: {role.name}'))
                stats['roles_created'] += 1
            else:
                # Update description
                role.description = role_data['description']
                role.save()
                self.stdout.write(self.style.WARNING(f'Updated role: {role.name}'))
                stats['roles_updated'] += 1

            # Assign permissions if not skipping
            if not skip_permissions and role_data['permissions']:
                django_perms = []
                missing_custom_keys = []

                for custom_key in role_data['permissions']:
                    django_codename = get_django_permission(custom_key)
                    if django_codename in available_permissions:
                        django_perms.append(available_permissions[django_codename])
                    else:
                        missing_custom_keys.append(custom_key)
                        stats['missing_permissions'].add(custom_key)

                # Set permissions
                if django_perms and not dry_run:
                    role.permissions.set(django_perms)
                    stats['permissions_assigned'] += len(django_perms)

                self.stdout.write(
                    f'  Assigned {len(django_perms)} permissions to {role.name}'
                )

                if missing_custom_keys:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  WARNING: {len(missing_custom_keys)} permissions not found in database:'
                        )
                    )
                    for missing in missing_custom_keys[:5]:  # Show first 5
                        self.stdout.write(f'    - {missing}')
                    if len(missing_custom_keys) > 5:
                        self.stdout.write(f'    ... and {len(missing_custom_keys) - 5} more')

        if not dry_run:
            self.stdout.write(self.style.SUCCESS('Successfully populated HMS roles!'))

            # Display summary
            total_roles = Role.objects.count()
            self.stdout.write(f'\nTotal roles in system: {total_roles}')

            for role in Role.objects.all():
                user_count = role.customuser_roles.count()
                permission_count = role.permissions.count()
                self.stdout.write(
                    f'  {role.name}: {user_count} users, {permission_count} permissions'
                )

            # Show missing permissions summary
            if stats['missing_permissions']:
                self.stdout.write(
                    self.style.WARNING(
                        f'\nWARNING: {len(stats["missing_permissions"])} custom permissions '
                        f'were not found in the database.'
                    )
                )
                self.stdout.write('This may indicate:')
                self.stdout.write('  1. Required migrations have not been run')
                self.stdout.write('  2. Some apps are not installed')
                self.stdout.write('  3. Permission definitions need updating')
                self.stdout.write('\nRun this command with --validate to check definitions.')
        else:
            self.stdout.write(self.style.SUCCESS('\n[DRY RUN] No changes made.'))

    def _validate_permissions(self):
        """Validate permission definitions and check against database."""
        self.stdout.write('Validating permission definitions...')

        is_valid, errors, warnings_list = validate_permission_definitions()
        if not is_valid:
            self.stdout.write(self.style.ERROR('Validation failed:'))
            for error in errors:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
            return

        self.stdout.write(self.style.SUCCESS('Permission definitions are structurally valid.'))

        # Check against database
        self.stdout.write('\nChecking permissions in database...')
        from django.contrib.auth.models import Permission
        from accounts.permissions import PERMISSION_DEFINITIONS, get_django_permission

        db_perms = set()
        for perm in Permission.objects.all():
            db_perms.add(f"{perm.content_type.app_label}.{perm.codename}")

        defined_django_perms = set()
        missing_perms = set()
        for custom_key, defn in PERMISSION_DEFINITIONS.items():
            django_codename = defn['django_codename']
            defined_django_perms.add(django_codename)
            if django_codename not in db_perms:
                missing_perms.add((custom_key, django_codename))

        self.stdout.write(f'Defined Django permissions: {len(defined_django_perms)}')
        self.stdout.write(f'Available in database: {len(defined_django_perms & db_perms)}')
        self.stdout.write(f'Missing from database: {len(missing_perms)}')

        if missing_perms:
            self.stdout.write(self.style.WARNING('\nMissing permissions:'))
            for custom_key, django_codename in sorted(missing_perms)[:20]:
                self.stdout.write(f'  {custom_key} -> {django_codename}')
            if len(missing_perms) > 20:
                self.stdout.write(f'  ... and {len(missing_perms) - 20} more')
            self.stdout.write('\nTo fix: Create migrations for affected apps or adjust definitions.')
        else:
            self.stdout.write(self.style.SUCCESS('\nAll defined permissions exist in database!'))

    def _list_permissions(self):
        """List all permissions and their assignment status."""
        self.stdout.write('Permission Listing\n' + '=' * 80)

        from accounts.permissions import PERMISSION_DEFINITIONS, ROLE_PERMISSIONS
        from accounts.models import Role

        # Get all roles
        roles = {role.name: role for role in Role.objects.all()}

        self.stdout.write(f'\nTotal Roles: {len(roles)}')
        self.stdout.write(f'Total Permission Categories: {len(set(d["category"] for d in PERMISSION_DEFINITIONS.values()))}')

        # List by category
        categories = {}
        for custom_key, defn in PERMISSION_DEFINITIONS.items():
            cat = defn['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((custom_key, defn))

        for category, perms in sorted(categories.items()):
            self.stdout.write(f'\n{category.upper().replace("_", " ")}')
            self.stdout.write('-' * 80)
            for custom_key, defn in sorted(perms):
                assigned_roles = []
                for role_name, role_data in ROLE_PERMISSIONS.items():
                    if custom_key in role_data['permissions']:
                        assigned_roles.append(role_name)

                role_status = ', '.join(assigned_roles) if assigned_roles else 'None'
                self.stdout.write(f'  {custom_key:<30} -> {defn["django_codename"]:<40} [{role_status}]')
