#!/usr/bin/env python
"""
Script to create NHIA Desk Office role with appropriate permissions
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import Role, CustomUser
from desk_office.models import AuthorizationCode
from patients.models import Patient
from consultations.models import Consultation


def create_nhia_desk_office_role():
    """Create NHIA Desk Office role with appropriate permissions"""
    try:
        # Check if role already exists
        if Role.objects.filter(name='NHIA Desk Office').exists():
            print("NHIA Desk Office role already exists. Updating permissions...")
            role = Role.objects.get(name='NHIA Desk Office')
        else:
            print("Creating NHIA Desk Office role...")
            role = Role.objects.create(
                name='NHIA Desk Office',
                description='Staff responsible for handling NHIA patient authorizations, codes, and related administrative tasks'
            )

        # Get relevant content types
        permissions_needed = []
        
        # 1. Desk Office permissions
        try:
            ct_auth_code = ContentType.objects.get(app_label='desk_office', model='authorizationcode')
            
            # Full permissions for AuthorizationCode model
            permissions_needed.extend([
                Permission.objects.get_or_create(
                    codename=f'add_authorizationcode',
                    content_type=ct_auth_code,
                    defaults={'name': 'Can add authorization code'}
                )[0],
                Permission.objects.get_or_create(
                    codename=f'change_authorizationcode', 
                    content_type=ct_auth_code,
                    defaults={'name': 'Can change authorization code'}
                )[0],
                Permission.objects.get_or_create(
                    codename=f'delete_authorizationcode',
                    content_type=ct_auth_code,
                    defaults={'name': 'Can delete authorization code'}
                )[0],
                Permission.objects.get_or_create(
                    codename=f'view_authorizationcode',
                    content_type=ct_auth_code,
                    defaults={'name': 'Can view authorization code'}
                )[0],
            ])
        except ContentType.DoesNotExist:
            print("Warning: AuthorizationCode model not found")
        
        # 2. Patient permissions (read-only for NHIA patients)
        try:
            ct_patient = ContentType.objects.get(app_label='patients', model='patient')
            
            permissions_needed.extend([
                Permission.objects.get_or_create(
                    codename='view_patient',
                    content_type=ct_patient,
                    defaults={'name': 'Can view patient'}
                )[0],
            ])
        except ContentType.DoesNotExist:
            print("Warning: Patient model not found")
        
        # 3. Consultation permissions (view and authorize)
        try:
            ct_consultation = ContentType.objects.get(app_label='consultations', model='consultation')
            
            permissions_needed.extend([
                Permission.objects.get_or_create(
                    codename='view_consultation',
                    content_type=ct_consultation,
                    defaults={'name': 'Can view consultation'}
                )[0],
                Permission.objects.get_or_create(
                    codename='change_consultation',
                    content_type=ct_consultation,
                    defaults={'name': 'Can change consultation'}
                )[0],
            ])
        except ContentType.DoesNotExist:
            print("Warning: Consultation model not found")
        
        # 4. Note: Referral module doesn't exist, skipping referral permissions
        
        # 5. General system permissions
        try:
            # User management (view only)
            ct_user = ContentType.objects.get(app_label='accounts', model='customuser')
            
            permissions_needed.extend([
                Permission.objects.get_or_create(
                    codename='view_customuser',
                    content_type=ct_user,
                    defaults={'name': 'Can view user'}
                )[0],
            ])
        except ContentType.DoesNotExist:
            print("Warning: CustomUser model not found")
        
        # 6. Dashboard access permissions
        dashboard_permissions = [
            'add_auditlog',
            'view_auditlog',
        ]
        
        try:
            ct_audit = ContentType.objects.get(app_label='accounts', model='auditlog')
            for perm_name in dashboard_permissions:
                permissions_needed.append(
                    Permission.objects.get_or_create(
                        codename=perm_name,
                        content_type=ct_audit,
                        defaults={'name': f'Can {perm_name.replace("_", " ")}'}
                    )[0]
                )
        except ContentType.DoesNotExist:
            print("Warning: AuditLog model not found")
        
        # Assign all permissions to role
        role.permissions.set(permissions_needed)
        role.save()
        
        print(f"✅ NHIA Desk Office role created/updated successfully!")
        print(f"   Role name: {role.name}")
        print(f"   Description: {role.description}")
        print(f"   Permissions assigned: {len(permissions_needed)}")
        
        # List the permissions
        print("\n📋 Permissions assigned:")
        for perm in permissions_needed:
            print(f"   - {perm.name} ({perm.codename})")
        
        # Automatically assign this role to test_desk_office user
            try:
                test_user = CustomUser.objects.get(username='test_desk_office')
                test_user.roles.add(role)
                test_user.save()
                print(f"✅ Role assigned to 'test_desk_office' user")
                
                # Also give staff status for dashboard access
                test_user.is_staff = True
                test_user.save()
                print(f"✅ Staff status granted to 'test_desk_office' user")
                
            except CustomUser.DoesNotExist:
                print("⚠️  test_desk_office user not found. You'll need to assign the role manually.")
        
        print(f"\n🎉 NHIA Desk Office role setup complete!")
        print(f"💡 Users with this role can now:")
        print(f"   - Generate and manage NHIA authorization codes")
        print(f"   - Search and view NHIA patient information")
        print(f"   - Authorize consultations")
        print(f"   - Access the NHIA desk office dashboard")
        print(f"   - View audit logs")
        
        return role
        
    except Exception as e:
        print(f"❌ Error creating NHIA Desk Office role: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    create_nhia_desk_office_role()
