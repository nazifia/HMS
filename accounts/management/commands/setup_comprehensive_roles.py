"""
Management command to set up comprehensive role-based permissions for all roles
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, ContentType
from accounts.models import Role
from accounts.permissions import ROLE_PERMISSIONS
from core.permissions import ROLE_TO_CORE_PERMISSION_MAPPING
from django.contrib.contenttypes.models import ContentType as CT

class Command(BaseCommand):
    help = 'Set up comprehensive role-based permissions for all roles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate all permissions even if they exist',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS('Setting up comprehensive role-based permissions...'))
        
        # Use a content type for HMS permissions
        try:
            content_type = CT.objects.get(app_label='accounts', model='role')
        except CT.DoesNotExist:
            try:
                content_type = CT.objects.filter(app_label='accounts').first()
                if not content_type:
                    content_type = CT.objects.get_for_model(Permission)
            except:
                content_type = CT.objects.get_for_model(Permission)
        
        total_permissions_created = 0
        roles_processed = []
        
        # Process each role
        for role_name, role_data in ROLE_PERMISSIONS.items():
            self.stdout.write(f'\nProcessing role: {role_name}')
            
            # Get or create the role
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={'description': role_data['description']}
            )
            
            if not created:
                role.description = role_data['description']
                role.save()
            
            role_permissions_created = 0
            
            # Process each permission for this role
            for permission_name in role_data['permissions']:
                # Convert role permission to Django codename
                codename = permission_name.replace('.', '_')
                
                # Create permission name
                permission_name_display = permission_name.replace('_', ' ').replace('.', ' ').title()
                
                try:
                    if force:
                        # Delete existing permission first
                        Permission.objects.filter(codename=codename, content_type=content_type).delete()
                    
                    # Create or get the permission
                    permission, perm_created = Permission.objects.get_or_create(
                        codename=codename,
                        content_type=content_type,
                        defaults={
                            'name': f"Can {permission_name_display} for {role_name}"
                        }
                    )
                    
                    # Add permission to role
                    role.permissions.add(permission)
                    
                    if perm_created:
                        role_permissions_created += 1
                        self.stdout.write(f"  Created permission: {codename}")
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  Error creating permission {codename}: {e}")
                    )
            
            # Also create core permissions that might not exist
            self._create_core_permissions(role, content_type)
            
            self.stdout.write(
                self.style.SUCCESS(f"  Role {role_name}: {role_permissions_created} permissions created")
            )
            total_permissions_created += role_permissions_created
            roles_processed.append(role_name)
        
        # Create missing core permissions
        self._create_missing_core_permissions(content_type)
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal permissions created: {total_permissions_created}')
        )
        
        # Display summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('ROLE PERMISSION SUMMARY'))
        self.stdout.write('='*60)
        
        for role_name in roles_processed:
            role = Role.objects.get(name=role_name)
            permissions = role.permissions.all()
            self.stdout.write(f'\n{role_name.upper()}:')
            self.stdout.write(f'  Description: {role.description}')
            self.stdout.write(f'  Permissions: {permissions.count()}')
            
            # Show some sample permissions
            sample_permissions = permissions[:5]
            if sample_permissions:
                self.stdout.write('  Sample permissions:')
                for perm in sample_permissions:
                    self.stdout.write(f'    - {perm.codename}')
                if permissions.count() > 5:
                    self.stdout.write(f'    ... and {permissions.count() - 5} more')
        
        # Test a few roles
        self._test_role_permissions()
        
        self.stdout.write(
            self.style.SUCCESS('\nComprehensive role-based permission setup completed!')
        )
    
    def _create_core_permissions(self, role, content_type):
        """Create core permissions that this role should have based on ROLE_TO_CORE_PERMISSION_MAPPING"""
        
        # Get role permissions
        role_data = ROLE_PERMISSIONS.get(role.name, {})
        role_permissions = role_data.get('permissions', [])
        
        # Find mapped core permissions
        core_permissions_needed = set()
        for role_perm in role_permissions:
            if role_perm in ROLE_TO_CORE_PERMISSION_MAPPING:
                core_perm = ROLE_TO_CORE_PERMISSION_MAPPING[role_perm]
                core_permissions_needed.add(core_perm)
        
        # Create missing core permissions
        for core_perm in core_permissions_needed:
            try:
                Permission.objects.get_or_create(
                    codename=core_perm,
                    content_type=content_type,
                    defaults={
                        'name': f"Core permission: {core_perm.replace('_', ' ').title()}"
                    }
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Warning creating core permission {core_perm}: {e}")
                )
    
    def _create_missing_core_permissions(self, content_type):
        """Create any missing core permissions from the mapping"""
        
        self.stdout.write('\nCreating missing core permissions...')
        
        # Get all core permissions from mapping
        core_permissions = set(ROLE_TO_CORE_PERMISSION_MAPPING.values())
        
        created_count = 0
        for core_perm in core_permissions:
            try:
                permission, created = Permission.objects.get_or_create(
                    codename=core_perm,
                    content_type=content_type,
                    defaults={
                        'name': f"Core permission: {core_perm.replace('_', ' ').title()}"
                    }
                )
                if created:
                    created_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Warning creating core permission {core_perm}: {e}")
                )
        
        if created_count > 0:
            self.stdout.write(f"Created {created_count} core permissions")
    
    def _test_role_permissions(self):
        """Test permissions for each role"""
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('TESTING ROLE PERMISSIONS'))
        self.stdout.write('='*60)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Test sidebar-relevant permissions
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
                # Get a user with this role
                user = User.objects.filter(roles__name=role_name).first()
                if not user:
                    continue
                
                self.stdout.write(f'\n{role_name.upper()} role permissions:')
                
                # Test each permission
                for perm in test_permissions:
                    has_perm = user.has_perm(f'accounts.{perm}') or self._user_has_role_permission(user, perm)
                    status = "✅" if has_perm else "❌"
                    self.stdout.write(f"  {status} {perm}: {has_perm}")
                    
            except Exception as e:
                self.stdout.write(f"  Error testing {role_name}: {e}")
    
    def _user_has_role_permission(self, user, permission_name):
        """Check if user has permission through role-based system"""
        
        from core.permissions import RolePermissionChecker
        
        try:
            checker = RolePermissionChecker(user)
            return checker.has_permission(permission_name)
        except:
            return False
