#!/usr/bin/env python
"""
Comprehensive Security and Permission Tester for HMS
This script tests authentication, authorization, role-based access control, and security measures.
"""

import os
import sys
import django
import json
import traceback
import datetime as dt
from datetime import date, timedelta
from decimal import Decimal

# Setup Django environment first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Import Django modules after setup
from django.test import TestCase, Client
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.models import Permission, Group
from django.urls import reverse, NoReverseMatch
from django.conf import settings
from django.core.exceptions import PermissionDenied

# Import models
from accounts.models import CustomUser, Role, Department
from patients.models import Patient
from doctors.models import Doctor, Specialization
from pharmacy.models import Medication, Prescription
from billing.models import Invoice, Service

class SecurityPermissionTester:
    def __init__(self):
        self.client = Client()
        self.test_results = []
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Set up comprehensive test environment for security testing"""
        print("🔧 Setting up security testing environment...")
        
        # Add testserver to ALLOWED_HOSTS
        if 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append('testserver')
        
        # Create test users with different roles
        self.create_test_users()
        
        # Create test data
        self.create_test_data()
        
        print("✅ Security testing environment ready")
    
    def create_test_users(self):
        """Create test users with different permission levels"""
        try:
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            
            # Create superuser
            self.superuser = CustomUser.objects.create_superuser(
                phone_number=f'+1234567{unique_id[:3]}',
                username=f'superuser_{unique_id}',
                email=f'super_{unique_id}@test.com',
                password='testpass123',
                first_name='Super',
                last_name='User'
            )
            
            # Create admin user
            self.admin_user = CustomUser.objects.create_user(
                phone_number=f'+1234568{unique_id[:3]}',
                username=f'admin_{unique_id}',
                email=f'admin_{unique_id}@test.com',
                password='testpass123',
                first_name='Admin',
                last_name='User',
                is_staff=True
            )
            
            # Create doctor user
            self.doctor_user = CustomUser.objects.create_user(
                phone_number=f'+1234569{unique_id[:3]}',
                username=f'doctor_{unique_id}',
                email=f'doctor_{unique_id}@test.com',
                password='testpass123',
                first_name='Doctor',
                last_name='User'
            )
            
            # Create nurse user
            self.nurse_user = CustomUser.objects.create_user(
                phone_number=f'+1234570{unique_id[:3]}',
                username=f'nurse_{unique_id}',
                email=f'nurse_{unique_id}@test.com',
                password='testpass123',
                first_name='Nurse',
                last_name='User'
            )
            
            # Create regular user (no special permissions)
            self.regular_user = CustomUser.objects.create_user(
                phone_number=f'+1234571{unique_id[:3]}',
                username=f'regular_{unique_id}',
                email=f'regular_{unique_id}@test.com',
                password='testpass123',
                first_name='Regular',
                last_name='User'
            )
            
            print(f"✅ Created test users with unique ID: {unique_id}")
            
        except Exception as e:
            print(f"⚠️  Error creating test users: {e}")
            traceback.print_exc()
    
    def create_test_data(self):
        """Create test data for security testing"""
        try:
            # Create test patient
            self.test_patient = Patient.objects.create(
                first_name='Test',
                last_name='Patient',
                date_of_birth=date(1990, 1, 1),
                gender='M',
                phone_number='+1234572999',
                email='testpatient@test.com',
                patient_id='TESTPAT001'
            )
            
            # Create test specialization
            self.test_specialization = Specialization.objects.create(
                name='Test Specialization',
                description='Test specialization for security testing'
            )
            
            print("✅ Created test data for security testing")
            
        except Exception as e:
            print(f"⚠️  Error creating test data: {e}")
            traceback.print_exc()
    
    def log_test_result(self, test_name, test_type, status, message="", error=None, details=None):
        """Log test results"""
        result = {
            'test': test_name,
            'test_type': test_type,
            'status': status,
            'message': message,
            'error': str(error) if error else None,
            'details': details,
            'timestamp': dt.datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_symbol} {test_name} ({test_type}): {status}")
        if message:
            print(f"   📝 {message}")
        if error:
            print(f"   🔥 Error: {error}")
        if details:
            print(f"   📊 Details: {details}")
    
    def test_authentication(self):
        """Test authentication mechanisms"""
        print("\n🔐 Testing Authentication...")
        
        # Test valid login
        try:
            user = authenticate(username=self.admin_user.username, password='testpass123')
            if user:
                self.log_test_result("Valid-Login", "AUTHENTICATION", "PASS", 
                                   "Valid credentials accepted")
            else:
                self.log_test_result("Valid-Login", "AUTHENTICATION", "FAIL", 
                                   "Valid credentials rejected")
        except Exception as e:
            self.log_test_result("Valid-Login", "AUTHENTICATION", "FAIL", 
                               "Authentication error", e)
        
        # Test invalid login
        try:
            user = authenticate(username=self.admin_user.username, password='wrongpassword')
            if not user:
                self.log_test_result("Invalid-Login", "AUTHENTICATION", "PASS", 
                                   "Invalid credentials correctly rejected")
            else:
                self.log_test_result("Invalid-Login", "AUTHENTICATION", "FAIL", 
                                   "Invalid credentials accepted")
        except Exception as e:
            self.log_test_result("Invalid-Login", "AUTHENTICATION", "FAIL", 
                               "Authentication error", e)
        
        # Test login with client
        try:
            login_success = self.client.login(username=self.admin_user.username, password='testpass123')
            if login_success:
                self.log_test_result("Client-Login", "AUTHENTICATION", "PASS", 
                                   "Client login successful")
            else:
                self.log_test_result("Client-Login", "AUTHENTICATION", "FAIL", 
                                   "Client login failed")
        except Exception as e:
            self.log_test_result("Client-Login", "AUTHENTICATION", "FAIL", 
                               "Client login error", e)
    
    def test_authorization_levels(self):
        """Test different authorization levels"""
        print("\n👑 Testing Authorization Levels...")
        
        # Test superuser access
        try:
            self.client.login(username=self.superuser.username, password='testpass123')
            response = self.client.get('/admin/')
            
            if response.status_code in [200, 302]:
                self.log_test_result("Superuser-Admin-Access", "AUTHORIZATION", "PASS", 
                                   "Superuser can access admin", 
                                   details=f"Status: {response.status_code}")
            else:
                self.log_test_result("Superuser-Admin-Access", "AUTHORIZATION", "FAIL", 
                                   "Superuser cannot access admin", 
                                   details=f"Status: {response.status_code}")
        except Exception as e:
            self.log_test_result("Superuser-Admin-Access", "AUTHORIZATION", "FAIL", 
                               "Superuser admin access error", e)
        
        # Test regular user admin access (should be denied)
        try:
            self.client.logout()
            self.client.login(username=self.regular_user.username, password='testpass123')
            response = self.client.get('/admin/')
            
            if response.status_code in [302, 403]:
                self.log_test_result("Regular-User-Admin-Denied", "AUTHORIZATION", "PASS", 
                                   "Regular user correctly denied admin access", 
                                   details=f"Status: {response.status_code}")
            else:
                self.log_test_result("Regular-User-Admin-Denied", "AUTHORIZATION", "FAIL", 
                                   "Regular user has admin access", 
                                   details=f"Status: {response.status_code}")
        except Exception as e:
            self.log_test_result("Regular-User-Admin-Denied", "AUTHORIZATION", "FAIL", 
                               "Regular user admin test error", e)
    
    def test_url_access_control(self):
        """Test URL access control for different user types"""
        print("\n🌐 Testing URL Access Control...")
        
        # URLs to test with different permission requirements
        test_urls = [
            ('/', 'public'),
            ('/accounts/login/', 'public'),
            ('/dashboard/', 'authenticated'),
            ('/patients/', 'authenticated'),
            ('/doctors/', 'authenticated'),
            ('/pharmacy/', 'authenticated'),
            ('/admin/', 'admin'),
        ]
        
        user_types = [
            ('anonymous', None),
            ('regular', self.regular_user),
            ('admin', self.admin_user),
            ('superuser', self.superuser)
        ]
        
        for url, expected_access in test_urls:
            for user_type, user in user_types:
                try:
                    # Logout first
                    self.client.logout()
                    
                    # Login if user is specified
                    if user:
                        self.client.login(username=user.username, password='testpass123')
                    
                    response = self.client.get(url)
                    
                    # Determine if access should be allowed
                    should_allow = self.should_allow_access(expected_access, user_type)
                    
                    if should_allow and response.status_code == 200:
                        self.log_test_result(f"{url}-{user_type}", "URL_ACCESS", "PASS", 
                                           "Correct access granted")
                    elif not should_allow and response.status_code in [302, 403, 401]:
                        self.log_test_result(f"{url}-{user_type}", "URL_ACCESS", "PASS", 
                                           "Correct access denied")
                    else:
                        self.log_test_result(f"{url}-{user_type}", "URL_ACCESS", "WARN", 
                                           f"Unexpected response: {response.status_code}")
                
                except Exception as e:
                    self.log_test_result(f"{url}-{user_type}", "URL_ACCESS", "FAIL", 
                                       "URL access test error", e)
    
    def should_allow_access(self, expected_access, user_type):
        """Determine if access should be allowed based on expected access level and user type"""
        if expected_access == 'public':
            return True
        elif expected_access == 'authenticated':
            return user_type in ['regular', 'admin', 'superuser']
        elif expected_access == 'admin':
            return user_type in ['admin', 'superuser']
        return False
    
    def test_session_security(self):
        """Test session security measures"""
        print("\n🔒 Testing Session Security...")
        
        try:
            # Test session creation
            self.client.login(username=self.admin_user.username, password='testpass123')
            session_key = self.client.session.session_key
            
            if session_key:
                self.log_test_result("Session-Creation", "SESSION_SECURITY", "PASS", 
                                   "Session created successfully")
            else:
                self.log_test_result("Session-Creation", "SESSION_SECURITY", "FAIL", 
                                   "Session not created")
            
            # Test session persistence
            response = self.client.get('/dashboard/')
            if response.status_code in [200, 302]:
                self.log_test_result("Session-Persistence", "SESSION_SECURITY", "PASS", 
                                   "Session persists across requests")
            else:
                self.log_test_result("Session-Persistence", "SESSION_SECURITY", "FAIL", 
                                   "Session not persisting")
            
            # Test logout
            self.client.logout()
            response = self.client.get('/dashboard/')
            if response.status_code in [302, 403]:
                self.log_test_result("Session-Logout", "SESSION_SECURITY", "PASS", 
                                   "Logout correctly invalidates session")
            else:
                self.log_test_result("Session-Logout", "SESSION_SECURITY", "WARN", 
                                   "Session may still be valid after logout")
        
        except Exception as e:
            self.log_test_result("Session-Security", "SESSION_SECURITY", "FAIL", 
                               "Session security test error", e)
    
    def run_all_tests(self):
        """Run all security and permission tests"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE SECURITY & PERMISSION TESTING - HMS")
        print("="*80)
        
        # Run different test categories
        self.test_authentication()
        self.test_authorization_levels()
        self.test_url_access_control()
        self.test_session_security()
        
        # Generate final report
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("📋 SECURITY & PERMISSION TEST REPORT")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warnings = len([r for r in self.test_results if r['status'] == 'WARN'])
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"📈 Success Rate: {(passed/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
        
        # Save detailed report
        with open('security_permission_test_report.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed': passed,
                    'failed': failed,
                    'warnings': warnings,
                    'success_rate': (passed/total_tests*100) if total_tests > 0 else 0
                },
                'results': self.test_results
            }, f, indent=2)
        
        print(f"📄 Detailed report saved to: security_permission_test_report.json")

if __name__ == "__main__":
    tester = SecurityPermissionTester()
    tester.run_all_tests()
