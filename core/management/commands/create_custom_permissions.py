"""
Management command to create custom permissions for HMS
Creates Permission objects for all custom permissions defined in APP_PERMISSIONS
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from core.permissions import APP_PERMISSIONS


class Command(BaseCommand):
    help = 'Create custom permissions for HMS application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating it',
        )

        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of permissions even if they exist',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Creating custom HMS permissions...')
        )

        # Get or create a ContentType for custom permissions
        # We'll use the core app's ContentType as a container
        content_type, _ = ContentType.objects.get_or_create(
            app_label='core',
            model='custompermission',
            defaults={'app_label': 'core', 'model': 'custompermission'}
        )

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for category, permissions in APP_PERMISSIONS.items():
            self.stdout.write(f'\nProcessing category: {category}')

            for codename, description in permissions.items():
                try:
                    # Check if permission already exists
                    permission, created = Permission.objects.get_or_create(
                        codename=codename,
                        defaults={
                            'name': description,
                            'content_type': content_type
                        }
                    )

                    if created:
                        if not options['dry_run']:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✓ Created: {codename} - {description}'
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'  [DRY RUN] Would create: {codename} - {description}'
                                )
                            )
                    else:
                        # Permission exists, update if force flag is set
                        if options['force']:
                            if not options['dry_run']:
                                permission.name = description
                                permission.content_type = content_type
                                permission.save()
                                updated_count += 1
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'  ↻ Updated: {codename} - {description}'
                                    )
                                )
                            else:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'  [DRY RUN] Would update: {codename} - {description}'
                                    )
                                )
                        else:
                            skipped_count += 1
                            self.stdout.write(
                                f'  - Exists: {codename}'
                            )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Error with {codename}: {str(e)}'
                        )
                    )

        # Summary
        self.stdout.write('\n' + '=' * 60)
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    'DRY RUN COMPLETE - No changes were made'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    '\nPermission Creation Summary:'
                )
            )
            self.stdout.write(f'  Created: {created_count}')
            self.stdout.write(f'  Updated: {updated_count}')
            self.stdout.write(f'  Skipped: {skipped_count}')
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nTotal permissions processed: {created_count + updated_count + skipped_count}'
                )
            )

        self.stdout.write('\n' + self.style.HTTP_INFO('Next Steps:'))
        self.stdout.write(
            '1. Assign permissions to users via the UI at /accounts/superuser/user-permissions/\n'
            '2. Users with these permissions will now see the corresponding sidebar items\n'
            '3. Use --force flag to update existing permissions\n'
        )
