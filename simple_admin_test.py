#!/usr/bin/env python
"""
Simple test to verify admin dashboard functionality
"""
import os
import sys
import django

# Add project path
sys.path.insert(0, os.getcwd())

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

def test_admin_dashboard():
    """Test admin dashboard functionality"""
    client = Client()
    
    # Create test admin user
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
        profile = CustomUserProfile.objects.create(user=admin_user, role='admin')
        profile.save()
        
        # Create admin role in Role model
        from accounts.models import Role
        admin_role, created = Role.objects.get_or_create(
            name='admin', 
            defaults={'description': 'Administrator role'}
        )
        admin_user.roles.add(admin_role)
    
    # Login as admin
    client.login(username='testadmin', password='testpass123')
    
    # Test admin dashboard URL directly without decorators
    from core import admin_views
    from django.http import HttpRequest
    
    request = HttpRequest()
    request.user = admin_user
    request.method = 'GET'
    
    # Test the view function directly
    try:
        response = admin_views.admin_dashboard(request)
        print(f"✓ Direct view call successful: {response.status_code if hasattr(response, 'status_code') else 'Response object'}")
    except Exception as e:
        print(f"✗ Direct view call failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test via client
    try:
        response = client.get('/core/admin/', follow=True)  # follow redirects
        print(f"✓ Client request status: {response.status_code}")
        if response.status_code == 200:
            content = response.content.decode()
            print(f"Content length: {len(content)}")
            print(f"First 500 chars:\n{content[:500]}")
            if 'Admin Dashboard' in content:
                print("✓ Admin Dashboard loaded successfully!")
            else:
                print("✗ Admin Dashboard content missing")
                # Check what's actually in the content
                if '<!DOCTYPE' in content:
                    print("✓ Looks like HTML content")
                elif 'redirect' in content.lower():
                    print("✗ Content contains redirect")
                else:
                    print("✗ Unexpected content format")
        else:
            print(f"✗ Failed to load admin dashboard: {response.status_code}")
    except Exception as e:
        print(f"✗ Client request failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("Simple Admin Dashboard Test")
    print("=" * 40)
    test_admin_dashboard()
