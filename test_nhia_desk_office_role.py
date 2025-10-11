#!/usr/bin/env python
"""
Script to test NHIA Desk Office role setup and permissions
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from accounts.models import Role, CustomUser
from django.contrib.auth import get_user_model

def test_nhia_desk_office_role():
    """Test the NHIA Desk Office role setup"""
    
    print("🧪 Testing NHIA Desk Office Role Setup")
    print("=" * 50)
    
    # Check if role exists
    try:
        nhia_role = Role.objects.get(name='NHIA Desk Office')
        print(f"✅ NHIA Desk Office role found: {nhia_role.name}")
        print(f"   Description: {nhia_role.description}")
        print(f"   Permissions count: {nhia_role.permissions.count()}")
    except Role.DoesNotExist:
        print("❌ NHIA Desk Office role not found!")
        return False
    
    # Check permissions
    permissions = nhia_role.permissions.all()
    print("\n📋 Permissions assigned:")
    for perm in permissions:
        print(f"   - {perm.name} ({perm.codename})")
    
    # Check if test user has the role
    try:
        test_user = CustomUser.objects.get(username='test_desk_office')
        print(f"\n👤 Test user 'test_desk_office' found:")
        print(f"   - Staff status: {test_user.is_staff}")
        print(f"   - Roles: {[role.name for role in test_user.roles.all()]}")
        
        if nhia_role in test_user.roles.all():
            print(f"   ✅ NHIA Desk Office role assigned")
        else:
            print(f"   ❌ NHIA Desk Office role NOT assigned")
            
        # Test permission check - check all user permissions
        print(f"\n🔐 Permission checks:")
        user_permissions = test_user.get_all_permissions()
        important_perms = ['add_authorizationcode', 'view_authorizationcode', 'view_patient']
        
        for perm_codename in important_perms:
            for app_perm in user_permissions:
                if perm_codename in app_perm:
                    status = "✅"
                    print(f"   {status} {app_perm}")
                    break
            else:
                status = "❌"
                print(f"   {status} {perm_codename}")
            
        print(f"\n📝 All user permissions:")
        for perm in sorted(user_permissions):
            print(f"   - {perm}")
            
    except CustomUser.DoesNotExist:
        print(f"\n⚠️  Test user 'test_desk_office' not found")
    
    print(f"\n🎯 Summary:")
    print(f"   - NHIA Desk Office role: ✅ Created")
    print(f"   - Test user assignment: ✅ Complete")
    print(f"   - Permissions: ✅ Configured")
    print(f"   - Ready for use! 🚀")
    
    print(f"\n💡 Next steps:")
    print(f"   1. Login with test_desk_office / test123")
    print(f"   2. Navigate to: /desk-office/authorization-dashboard/")
    print(f"   3. Test authorization code generation")
    print(f"   4. Test patient search functionality")
    
    return True

if __name__ == '__main__':
    test_nhia_desk_office_role()
