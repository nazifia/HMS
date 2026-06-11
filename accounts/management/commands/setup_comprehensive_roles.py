"""
Management command to set up comprehensive role-based permissions for all roles.

Roles are created/updated from the canonical ROLE_PERMISSIONS spec, then
permission assignment is delegated to the authoritative `sync_role_permissions`
command (--fix). The legacy synthetic-permission helpers have been removed.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from accounts.models import Role
from accounts.permissions import ROLE_PERMISSIONS, user_has_permission


class Command(BaseCommand):
    help = 'Set up comprehensive role-based permissions for all roles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would change without applying (passed to sync_role_permissions)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS('Setting up comprehensive role-based permissions...'))

        # Ensure every canonical role exists with an up-to-date description.
        roles_processed = []
        for role_name, role_data in ROLE_PERMISSIONS.items():
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={'description': role_data['description']}
            )
            if not created and role.description != role_data['description']:
                role.description = role_data['description']
                role.save(update_fields=['description'])
            roles_processed.append(role_name)
            self.stdout.write(f'  Role ready: {role_name}')

        # Delegate authoritative permission assignment to sync_role_permissions.
        self.stdout.write('\nDelegating permission assignment to sync_role_permissions...')
        sync_kwargs = {'dry_run': True} if dry_run else {'fix': True}
        call_command('sync_role_permissions', **sync_kwargs)

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('ROLE PERMISSION SUMMARY'))
        self.stdout.write('=' * 60)
        for role_name in roles_processed:
            role = Role.objects.get(name=role_name)
            permissions = role.permissions.all()
            self.stdout.write(f'\n{role_name.upper()}:')
            self.stdout.write(f'  Description: {role.description}')
            self.stdout.write(f'  Permissions: {permissions.count()}')

        self._test_role_permissions()

        self.stdout.write(
            self.style.SUCCESS('\nComprehensive role-based permission setup completed!')
        )

    def _test_role_permissions(self):
        """Diagnostic: verify sidebar-relevant permissions resolve per role."""

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('TESTING ROLE PERMISSIONS'))
        self.stdout.write('=' * 60)

        from django.contrib.auth import get_user_model
        User = get_user_model()

        test_permissions = [
            'view_dashboard',
            'create_patient',
            'create_appointment',
            'enter_results',
            'view_laboratory_reports',
            'manage_departments',
            'view_user_management',
            'manage_roles'
        ]

        for role_name in ROLE_PERMISSIONS.keys():
            try:
                user = User.objects.filter(roles__name=role_name).first()
                if not user:
                    continue

                self.stdout.write(f'\n{role_name.upper()} role permissions:')
                for perm in test_permissions:
                    has_perm = user.has_perm(f'accounts.{perm}') or self._user_has_role_permission(user, perm)
                    status = "✅" if has_perm else "❌"
                    self.stdout.write(f"  {status} {perm}: {has_perm}")
            except Exception as e:
                self.stdout.write(f"  Error testing {role_name}: {e}")

    def _user_has_role_permission(self, user, permission_name):
        """Check if user has permission through role-based system"""
        try:
            return user_has_permission(user, permission_name)
        except Exception:
            return False
