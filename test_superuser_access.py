#!/usr/bin/env python
"""
Test script to verify superuser access to all system modules
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test.utils import setup_test_environment
from django.conf import settings

User = get_user_model()

def test_superuser_access():
    """
    Test that superuser can access all major views in the system
    """
    print("Testing superuser access to HMS modules...")
    
    # Create or get superuser
    try:
        superuser = User.objects.get(username='admin')
        print(f"Using existing superuser: {superuser.username}")
    except User.DoesNotExist:
        print("Creating superuser for testing...")
        superuser = User.objects.create_superuser(
            username='admin',
            phone_number='08012345678',
            password='admin123',
            email='admin@test.com'
        )
        print(f"Created superuser: {superuser.username}")
    
    # Create test client and login
    client = Client()
    client.login(username='admin', password='admin123')
    
    # List of URLs to test
    test_urls = [
        # Core URLs
        ('dashboard:dashboard', '/'),
        
        # Consultation URLs
        ('consultations:unified_dashboard', '/consultations/unified-dashboard/'),
        ('consultations:consultation_list', '/consultations/doctor/consultations/'),
        ('consultations:patient_list', '/consultations/doctor/patients/'),
        ('consultations:waiting_list', '/consultations/waiting-list/'),
        ('consultations:referral_list', '/consultations/doctor/referrals/'),
        
        # Patient URLs  
        ('patients:patient_list', '/patients/'),
        
        # Pharmacy URLs
        ('pharmacy:dashboard', '/pharmacy/dashboard/'),
        ('pharmacy:prescription_list', '/pharmacy/prescriptions/'),
        ('pharmacy:inventory', '/pharmacy/inventory/'),
        
        # Laboratory URLs
        ('laboratory:dashboard', '/laboratory/dashboard/'),
        
        # Billing URLs
        ('billing:dashboard', '/billing/dashboard/'),
        
        # Inpatient URLs
        ('inpatient:admission_list', '/inpatient/'),
        
        # Appointment URLs
        ('appointments:dashboard', '/appointments/dashboard/'),
        
        # HR URLs
        ('hr:dashboard', '/hr/dashboard/'),
        
        # Reporting URLs
        ('reporting:dashboard', '/reporting/dashboard/'),
    ]
    
    # Test each URL
    success_count = 0
    total_count = len(test_urls)
    
    for url_name, url_path in test_urls:
        try:
            response = client.get(url_path)
            status_code = response.status_code
            
            if status_code == 200:
                print(f"✓ {url_name} - {url_path} - Status: {status_code}")
                success_count += 1
            elif status_code == 302:
                print(f"→ {url_name} - {url_path} - Redirect: {status_code}")
                success_count += 1  # Redirects are often expected
            elif status_code == 404:
                print(f"⚠ {url_name} - {url_path} - Not Found: {status_code}")
            else:
                print(f"✗ {url_name} - {url_path} - Status: {status_code}")
                
        except Exception as e:
            print(f"✗ {url_name} - {url_path} - Error: {str(e)}")
    
    # Summary
    print(f"\nSuperuser Access Test Summary:")
    print(f"Successful: {success_count}/{total_count}")
    print(f"Success Rate: {(success_count/total_count)*100:.1f}%")
    
    if success_count == total_count:
        print("✓ Superuser has full access to all tested modules!")
        return True
    else:
        print("⚠ Some modules may have access restrictions for superusers.")
        return False

def test_permission_system():
    """
    Test the permission system for superusers
    """
    print("\nTesting permission system...")
    
    try:
        superuser = User.objects.get(username='admin')
        
        # Test core permissions checker
        from core.permissions import RolePermissionChecker
        
        checker = RolePermissionChecker(superuser)
        
        # Test various permissions
        test_permissions = [
            'create_patient',
            'edit_patient', 
            'delete_patient',
            'view_patients',
            'create_invoice',
            'edit_invoice',
            'manage_inventory',
            'dispense_medication',
            'create_test_request',
            'view_reports',
            'system_configuration'
        ]
        
        all_passed = True
        for permission in test_permissions:
            has_perm = checker.has_permission(permission)
            if has_perm:
                print(f"✓ Superuser has permission: {permission}")
            else:
                print(f"✗ Superuser missing permission: {permission}")
                all_passed = False
        
        if all_passed:
            print("✓ Superuser has all tested permissions!")
        else:
            print("⚠ Superuser is missing some permissions.")
            
        return all_passed
        
    except Exception as e:
        print(f"Error testing permission system: {e}")
        return False

if __name__ == '__main__':
    print("HMS Superuser Access Test")
    print("=" * 50)
    
    # Run tests
    access_test_passed = test_superuser_access()
    permission_test_passed = test_permission_system()
    
    print("\n" + "=" * 50)
    print("OVERALL TEST RESULTS:")
    
    if access_test_passed and permission_test_passed:
        print("✓ ALL TESTS PASSED - Superuser has full system access!")
    else:
        print("⚠ SOME TESTS FAILED - Check superuser configuration.")
    
    print("=" * 50)
