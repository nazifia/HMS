#!/usr/bin/env python
"""
Comprehensive View and URL Tester for HMS
This script tests all views, URL patterns, and HTTP responses in the HMS system.
"""

import os
import sys
import django
import json
import traceback
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse, resolve, NoReverseMatch
from django.core.management import execute_from_command_line
from django.db import transaction
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Import all models
from accounts.models import CustomUser, CustomUserProfile, Role, Department
from patients.models import Patient, PatientWallet, WalletTransaction
from doctors.models import Doctor, Specialization
from pharmacy.models import Medication, Prescription, PrescriptionItem, MedicationCategory
from billing.models import Invoice, Payment, Service, ServiceCategory
from laboratory.models import TestRequest, Test, TestCategory
from appointments.models import Appointment
from inpatient.models import Admission, Ward, Bed
from hr.models import StaffProfile, Designation, Leave, Department as HRDepartment
from consultations.models import Consultation, ConsultingRoom
from radiology.models import RadiologyTest, RadiologyOrder, RadiologyCategory
from theatre.models import Surgery, OperationTheatre, SurgeryType
from nhia.models import NHIAPatient
from retainership.models import RetainershipPatient

class ViewURLTester:
    def __init__(self):
        self.client = Client()
        self.test_results = []
        self.setup_test_environment()
        
        # Common URLs to test
        self.common_urls = [
            '/',
            '/accounts/login/',
            '/dashboard/',
            '/patients/',
            '/doctors/',
            '/appointments/',
            '/pharmacy/',
            '/laboratory/',
            '/billing/',
            '/inpatient/',
            '/hr/',
            '/reporting/',
            '/consultations/',
            '/radiology/',
            '/theatre/',
            '/nhia/',
            '/retainership/',
        ]
    
    def setup_test_environment(self):
        """Set up test data and environment"""
        print("🔧 Setting up test environment for view testing...")
        
        # Add testserver to ALLOWED_HOSTS
        if 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append('testserver')
        
        # Create test users
        self.create_test_users()
        print("✅ Test environment ready for view testing")
    
    def create_test_users(self):
        """Create test users for different roles"""
        try:
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            
            # Create admin user
            self.admin_user = CustomUser.objects.create_superuser(
                phone_number=f'+1234567{unique_id[:3]}',
                username=f'test_admin_{unique_id}',
                email=f'admin_{unique_id}@test.com',
                password='testpass123',
                first_name='Test',
                last_name='Admin'
            )
            
            # Create regular user
            self.regular_user = CustomUser.objects.create_user(
                phone_number=f'+1234568{unique_id[:3]}',
                username=f'test_user_{unique_id}',
                email=f'user_{unique_id}@test.com',
                password='testpass123',
                first_name='Test',
                last_name='User'
            )
            
            print(f"✅ Created test users with unique ID: {unique_id}")
            
        except Exception as e:
            print(f"⚠️  Error creating test users: {e}")
            traceback.print_exc()
    
    def log_test_result(self, test_name, test_type, status, message="", error=None, response_code=None):
        """Log test results"""
        result = {
            'test': test_name,
            'test_type': test_type,
            'status': status,
            'message': message,
            'error': str(error) if error else None,
            'response_code': response_code,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        code_info = f" (HTTP {response_code})" if response_code else ""
        print(f"{status_symbol} {test_name} ({test_type}): {status}{code_info}")
        if message:
            print(f"   📝 {message}")
        if error:
            print(f"   🔥 Error: {error}")
    
    def test_common_urls(self):
        """Test common URLs without authentication"""
        print("\n🌐 Testing Common URLs (No Auth)...")
        
        for url in self.common_urls:
            try:
                response = self.client.get(url)
                
                if response.status_code == 200:
                    self.log_test_result(url, "URL_NO_AUTH", "PASS", "Accessible without auth", response_code=response.status_code)
                elif response.status_code == 302:
                    self.log_test_result(url, "URL_NO_AUTH", "PASS", "Redirects (likely to login)", response_code=response.status_code)
                elif response.status_code == 403:
                    self.log_test_result(url, "URL_NO_AUTH", "PASS", "Forbidden (expected)", response_code=response.status_code)
                elif response.status_code == 404:
                    self.log_test_result(url, "URL_NO_AUTH", "WARN", "Not found", response_code=response.status_code)
                else:
                    self.log_test_result(url, "URL_NO_AUTH", "WARN", f"Unexpected status", response_code=response.status_code)
                    
            except Exception as e:
                self.log_test_result(url, "URL_NO_AUTH", "FAIL", "Request failed", e)
    
    def test_authenticated_urls(self):
        """Test URLs with authenticated user"""
        print("\n🔐 Testing URLs with Authentication...")
        
        # Login as admin user
        login_success = self.client.login(username=self.admin_user.username, password='testpass123')
        if not login_success:
            print("❌ Failed to login admin user")
            return
        
        for url in self.common_urls:
            try:
                response = self.client.get(url)
                
                if response.status_code == 200:
                    self.log_test_result(url, "URL_AUTH", "PASS", "Accessible with auth", response_code=response.status_code)
                elif response.status_code == 302:
                    self.log_test_result(url, "URL_AUTH", "WARN", "Redirects even with auth", response_code=response.status_code)
                elif response.status_code == 403:
                    self.log_test_result(url, "URL_AUTH", "WARN", "Forbidden even with auth", response_code=response.status_code)
                elif response.status_code == 404:
                    self.log_test_result(url, "URL_AUTH", "WARN", "Not found", response_code=response.status_code)
                else:
                    self.log_test_result(url, "URL_AUTH", "WARN", f"Unexpected status", response_code=response.status_code)
                    
            except Exception as e:
                self.log_test_result(url, "URL_AUTH", "FAIL", "Request failed", e)
        
        # Logout
        self.client.logout()
    
    def test_specific_view_urls(self):
        """Test specific view URLs that we know exist"""
        print("\n🎯 Testing Specific View URLs...")
        
        # Login as admin
        self.client.login(username=self.admin_user.username, password='testpass123')
        
        specific_urls = [
            '/patients/register/',
            '/doctors/list/',
            '/appointments/create/',
            '/pharmacy/medications/',
            '/laboratory/tests/',
            '/billing/invoices/',
            '/inpatient/wards/',
            '/hr/departments/',
            '/reporting/dashboard/',
            '/consultations/rooms/',
        ]
        
        for url in specific_urls:
            try:
                response = self.client.get(url)
                
                if response.status_code == 200:
                    self.log_test_result(url, "SPECIFIC_URL", "PASS", "View accessible", response_code=response.status_code)
                elif response.status_code == 302:
                    self.log_test_result(url, "SPECIFIC_URL", "WARN", "Redirects", response_code=response.status_code)
                elif response.status_code == 404:
                    self.log_test_result(url, "SPECIFIC_URL", "WARN", "Not found", response_code=response.status_code)
                else:
                    self.log_test_result(url, "SPECIFIC_URL", "WARN", f"Status {response.status_code}", response_code=response.status_code)
                    
            except Exception as e:
                self.log_test_result(url, "SPECIFIC_URL", "FAIL", "Request failed", e)
        
        self.client.logout()
    
    def test_admin_urls(self):
        """Test Django admin URLs"""
        print("\n👑 Testing Admin URLs...")
        
        admin_urls = [
            '/admin/',
            '/admin/login/',
            '/admin/accounts/',
            '/admin/patients/',
            '/admin/pharmacy/',
        ]
        
        for url in admin_urls:
            try:
                response = self.client.get(url)
                
                if response.status_code in [200, 302]:
                    self.log_test_result(url, "ADMIN_URL", "PASS", "Admin URL accessible", response_code=response.status_code)
                else:
                    self.log_test_result(url, "ADMIN_URL", "WARN", f"Status {response.status_code}", response_code=response.status_code)
                    
            except Exception as e:
                self.log_test_result(url, "ADMIN_URL", "FAIL", "Request failed", e)
    
    def run_all_tests(self):
        """Run all view and URL tests"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE VIEW & URL TESTING - HMS")
        print("="*80)
        
        # Run different test categories
        self.test_common_urls()
        self.test_authenticated_urls()
        self.test_specific_view_urls()
        self.test_admin_urls()
        
        # Generate final report
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("📋 VIEW & URL TEST REPORT")
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
        with open('view_url_test_report.json', 'w') as f:
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
        
        print(f"📄 Detailed report saved to: view_url_test_report.json")

if __name__ == "__main__":
    tester = ViewURLTester()
    tester.run_all_tests()
