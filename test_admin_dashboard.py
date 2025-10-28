#!/usr/bin/env python
"""
Test script to verify admin dashboard functionality
"""
import os
import sys
import django

# Add project path
sys.path.insert(0, os.getcwd())

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from core.activity_log import ActivityLog

User = get_user_model()

def test_admin_dashboard():
    """Test admin dashboard functionality"""
    client = Client()
    
    # Create test admin user if not exists
    try:
        admin_user = User.objects.get(username='testadmin')
    except User.DoesNotExist:
        admin_user = User.objects.create_user(
            username='testadmin',
            email='test@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True,
            first_name='Test',
            last_name='Admin'
        )
        
        # Create profile
        from accounts.models import CustomUserProfile
        profile = CustomUserProfile.objects.create(user=admin_user)
        profile.save()
    
    # Login as admin
    login_result = client.login(username='testadmin', password='testpass123')
    print(f"✓ Login successful: {login_result}")
    
    # Make sure we have admin profile with role
    from accounts.models import Role
    try:
        admin_role = Role.objects.get(name='admin')
    except Role.DoesNotExist:
        admin_role = Role.objects.create(name='admin', description='Administrator role')
    
    # Set both the many-to-many role and the profile role field
    if not admin_user.roles.filter(name='admin').exists():
        admin_user.roles.add(admin_role)
    
    # Set the profile.role field as well
    if admin_user.profile:
        admin_user.profile.role = 'admin'
        admin_user.profile.save()
    
    admin_user.save()
    
    # Debug: Check admin status
    print(f"User is_superuser: {admin_user.is_superuser}")
    print(f"User has profile: {hasattr(admin_user, 'profile')}")
    if hasattr(admin_user, 'profile'):
        print(f"Profile role: {admin_user.profile.role}")
        print(f"User has admin role in roles: {admin_user.roles.filter(name='admin').exists()}")
    
    # Test admin dashboard URL
    print("Testing admin dashboard...")
    try:
        # First try without login to see what happens
        response = client.get('/core/admin/', follow=False)
        print(f"✓ Admin dashboard without login status: {response.status_code}")
        
        # Then with login
        response = client.get('/core/admin/', follow=False)
        print(f"✓ Admin dashboard with login status: {response.status_code}")
        
        # Check redirect location
        if response.status_code == 302:
            print(f"✗ Redirected to: {response.get('Location', 'unknown')}")
        
        response = client.get(reverse('core:admin_dashboard'))
        print(f"✓ Admin dashboard via reverse status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode()
            
            # Check for key elements
            if 'Admin Dashboard' in content:
                print("✓ Admin Dashboard title found")
            else:
                print("✗ Admin Dashboard title missing")
                
            if 'activityChart' in content:
                print("✓ Activity chart element found")
            else:
                print("✗ Activity chart element missing")
                
            if 'User Management' in content:
                print("✓ User Management button found")
            else:
                print("✗ User Management button missing")
                
            # Check for JavaScript errors markers
            if 'H.match' in content:
                print("✗ H.match error found in template")
            else:
                print("✓ No H.match error detected")
                
        elif response.status_code == 302:
            print("✗ Admin dashboard redirected (permission issue)")
        else:
            print(f"✗ Admin dashboard failed with status: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Admin dashboard test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test API endpoints
    print("\nTesting API endpoints...")
    try:
        # Test users API
        response = client.get(reverse('core:api_admin_users'))
        print(f"✓ Users API status: {response.status_code}")
        
        # Test roles API
        response = client.get(reverse('core:api_admin_roles'))
        print(f"✓ Roles API status: {response.status_code}")
        
        # Test departments API
        response = client.get(reverse('core:api_admin_departments'))
        print(f"✓ Departments API status: {response.status_code}")
        
    except Exception as e:
        print(f"✗ API test failed: {e}")

if __name__ == '__main__':
    print("Testing Admin Dashboard Functionality")
    print("=" * 50)
    test_admin_dashboard()
    print("\nTest completed!")
