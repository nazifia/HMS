"""
Management command to create missing custom permissions from PERMISSION_DEFINITIONS.

This command ensures all permissions referenced in PERMISSION_DEFINITIONS exist
in the django.contrib.auth.models.Permission table.

Usage:
    python manage.py create_missing_permissions
    python manage.py create_missing_permissions --dry-run
    python manage.py create_missing_permissions --only-custom
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from accounts.permissions import PERMISSION_DEFINITIONS
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create missing permissions from PERMISSION_DEFINITIONS'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without making changes'
        )
        parser.add_argument(
            '--only-custom',
            action='store_true',
            help='Only create custom permissions (is_custom=True)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        only_custom = options['only_custom']
        verbose = options['verbose']

        self.stdout.write('=' * 80)
        self.stdout.write('Create Missing Permissions')
        self.stdout.write('=' * 80)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made\n'))

        # Get all existing permissions for fast lookup
        existing_perms = {}
        for perm in Permission.objects.all().select_related('content_type'):
            key = f"{perm.content_type.app_label}.{perm.codename}"
            existing_perms[key] = perm

        self.stdout.write(f'Existing permissions in database: {len(existing_perms)}\n')

        to_create = []
        skipped = []
        errors = []

        for custom_key, defn in PERMISSION_DEFINITIONS.items():
            django_codename = defn['django_codename']
            model_name = defn['model']
            description = defn.get('description', f'Can {django_codename}')
            is_custom = defn.get('is_custom', False)

            # Skip if only custom and this is not custom
            if only_custom and not is_custom:
                if verbose:
                    self.stdout.write(f'Skipping (standard): {django_codename}')
                continue

            # Check if already exists
            if django_codename in existing_perms:
                if verbose:
                    self.stdout.write(f'Already exists: {django_codename}')
                continue

            to_create.append({
                'django_codename': django_codename,
                'model_name': model_name,
                'description': description,
                'is_custom': is_custom,
            })

        self.stdout.write(f'Permissions to create: {len(to_create)}')

        if dry_run:
            for item in to_create:
                self.stdout.write(f'  Would create: {item["django_codename"]} ({item["description"]})')
            self.stdout.write(self.style.WARNING('\nDRY RUN - No permissions created'))
            return

        # Now create them
        created_count = 0
        for item in to_create:
            django_codename = item['django_codename']
            model_name = item['model_name']
            description = item['description']

            # Parse app_label and codename
            if '.' not in django_codename:
                errors.append(f'Invalid django_codename: {django_codename}')
                continue
            app_label, codename = django_codename.split('.', 1)

            # Get model class to find ContentType
            try:
                model = apps.get_model(app_label, model_name)
                if model is None:
                    errors.append(f'Model not found: {app_label}.{model_name}')
                    continue
                ct = ContentType.objects.get_for_model(model)
            except LookupError as e:
                errors.append(f'Model lookup failed {app_label}.{model_name}: {e}')
                continue
            except Exception as e:
                errors.append(f'Error getting ContentType for {app_label}.{model_name}: {e}')
                continue

            # Create permission
            try:
                perm, created = Permission.objects.get_or_create(
                    content_type=ct,
                    codename=codename,
                    defaults={'name': description}
                )
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Created: {django_codename}'))
                else:
                    # Race condition? Already exists
                    pass
            except Exception as e:
                errors.append(f'Failed to create {django_codename}: {e}')
                self.stderr.write(self.style.ERROR(f'Error: {e}'))

        # Summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('SUMMARY')
        self.stdout.write('=' * 80)
        self.stdout.write(f'Created: {created_count}')
        self.stdout.write(f'Skipped (already exist): {len(existing_perms)}')
        self.stdout.write(f'Total permissions now: {len(existing_perms) + created_count}')
        if errors:
            self.stdout.write(self.style.ERROR(f'Errors: {len(errors)}'))
            for err in errors[:10]:
                self.stdout.write(self.style.ERROR(f'  - {err}'))
            if len(errors) > 10:
                self.stdout.write(self.style.ERROR(f'  ... and {len(errors) - 10} more'))

        if not dry_run and created_count > 0:
            self.stdout.write(self.style.SUCCESS('\nNext steps:'))
            self.stdout.write('  1. Run: python manage.py sync_role_permissions --fix')
            self.stdout.write('  2. Run: python manage.py validate_permissions')
