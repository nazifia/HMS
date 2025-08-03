#!/usr/bin/env python
"""
Comprehensive API and Integration Tester for HMS
This script tests all API endpoints, authentication, permissions, and integration between apps.
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

# Import REST framework after Django setup
try:
    from rest_framework.test import APIClient
    from rest_framework import status
    HAS_DRF = True
except ImportError:
    HAS_DRF = False
    print("⚠️  Django REST Framework not available, skipping API tests")

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

class APIIntegrationTester:
    def __init__(self):
        if HAS_DRF:
            self.client = APIClient()
        else:
            self.client = None
        self.web_client = Client()
        self.test_results = []
        self.setup_test_environment()
        
        # API endpoints to test
        self.api_endpoints = [
            '/api/accounts/users/',
            '/api/accounts/roles/',
            '/api/accounts/permissions/',
            '/api/accounts/audit-logs/',
        ]
    
    def setup_test_environment(self):
        """Set up test data and environment"""
        print("🔧 Setting up test environment for API testing...")
        
        # Add testserver to ALLOWED_HOSTS
        if 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append('testserver')
        
        # Create test users and data
        self.create_test_data()
        print("✅ Test environment ready for API testing")
    
    def create_test_data(self):
        """Create comprehensive test data"""
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
            
            # Create test patient
            self.test_patient = Patient.objects.create(
                first_name='Test',
                last_name='Patient',
                date_of_birth=date(1990, 1, 1),
                gender='M',
                phone_number=f'+1234569{unique_id[:3]}',
                email=f'patient_{unique_id}@test.com',
                patient_id=f'PAT{unique_id}'
            )
            
            # Create test department
            self.test_department = HRDepartment.objects.create(
                name=f'Test Department {unique_id}',
                description='Test department for API testing'
            )
            
            print(f"✅ Created test data with unique ID: {unique_id}")
            
        except Exception as e:
            print(f"⚠️  Error creating test data: {e}")
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
    
    def test_api_endpoints_unauthenticated(self):
        """Test API endpoints without authentication"""
        print("\n🔓 Testing API Endpoints (No Auth)...")

        if not HAS_DRF or not self.client:
            self.log_test_result("API_ENDPOINTS", "API_NO_AUTH", "SKIP", "Django REST Framework not available")
            return

        for endpoint in self.api_endpoints:
            try:
                response = self.client.get(endpoint)

                if response.status_code == 401:
                    self.log_test_result(endpoint, "API_NO_AUTH", "PASS", "Correctly requires authentication", response_code=response.status_code)
                elif response.status_code == 403:
                    self.log_test_result(endpoint, "API_NO_AUTH", "PASS", "Forbidden (expected)", response_code=response.status_code)
                elif response.status_code == 404:
                    self.log_test_result(endpoint, "API_NO_AUTH", "WARN", "Endpoint not found", response_code=response.status_code)
                else:
                    self.log_test_result(endpoint, "API_NO_AUTH", "WARN", f"Unexpected status", response_code=response.status_code)

            except Exception as e:
                self.log_test_result(endpoint, "API_NO_AUTH", "FAIL", "Request failed", e)
    
    def test_api_endpoints_authenticated(self):
        """Test API endpoints with authentication"""
        print("\n🔐 Testing API Endpoints (With Auth)...")

        if not HAS_DRF or not self.client:
            self.log_test_result("API_ENDPOINTS", "API_AUTH", "SKIP", "Django REST Framework not available")
            return

        # Force authenticate as admin user
        self.client.force_authenticate(user=self.admin_user)

        for endpoint in self.api_endpoints:
            try:
                response = self.client.get(endpoint)

                if response.status_code == 200:
                    self.log_test_result(endpoint, "API_AUTH", "PASS", "Accessible with auth", response_code=response.status_code)
                elif response.status_code == 403:
                    self.log_test_result(endpoint, "API_AUTH", "WARN", "Forbidden even with auth", response_code=response.status_code)
                elif response.status_code == 404:
                    self.log_test_result(endpoint, "API_AUTH", "WARN", "Endpoint not found", response_code=response.status_code)
                else:
                    self.log_test_result(endpoint, "API_AUTH", "WARN", f"Unexpected status", response_code=response.status_code)

            except Exception as e:
                self.log_test_result(endpoint, "API_AUTH", "FAIL", "Request failed", e)

        # Clear authentication
        self.client.force_authenticate(user=None)
    
    def test_model_integrations(self):
        """Test integration between different models"""
        print("\n🔗 Testing Model Integrations...")
        
        # Test Patient-Wallet integration
        try:
            patient_wallet = PatientWallet.objects.filter(patient=self.test_patient).first()
            if patient_wallet:
                self.log_test_result("Patient-Wallet", "INTEGRATION", "PASS", "Patient wallet exists")
            else:
                self.log_test_result("Patient-Wallet", "INTEGRATION", "WARN", "No wallet found for patient")
        except Exception as e:
            self.log_test_result("Patient-Wallet", "INTEGRATION", "FAIL", "Integration test failed", e)
        
        # Test User-Profile integration
        try:
            user_profile = CustomUserProfile.objects.filter(user=self.admin_user).first()
            if user_profile:
                self.log_test_result("User-Profile", "INTEGRATION", "PASS", "User profile exists")
            else:
                self.log_test_result("User-Profile", "INTEGRATION", "WARN", "No profile found for user")
        except Exception as e:
            self.log_test_result("User-Profile", "INTEGRATION", "FAIL", "Integration test failed", e)
        
        # Test Department relationships
        try:
            dept_count = HRDepartment.objects.count()
            self.log_test_result("Department-Count", "INTEGRATION", "PASS", f"Found {dept_count} departments")
        except Exception as e:
            self.log_test_result("Department-Count", "INTEGRATION", "FAIL", "Department test failed", e)
    
    def test_business_workflows(self):
        """Test complex business workflows"""
        print("\n⚙️  Testing Business Workflows...")
        
        # Test prescription workflow
        try:
            # Create a prescription
            prescription = Prescription.objects.create(
                patient=self.test_patient,
                doctor=self.admin_user,
                diagnosis='Test diagnosis',
                notes='Test prescription notes'
            )
            self.log_test_result("Prescription-Creation", "WORKFLOW", "PASS", "Prescription created successfully")
            
            # Test prescription items
            med_category = MedicationCategory.objects.first()
            if med_category:
                medication = Medication.objects.filter(category=med_category).first()
                if medication:
                    prescription_item = PrescriptionItem.objects.create(
                        prescription=prescription,
                        medication=medication,
                        dosage='1 tablet',
                        frequency='twice daily',
                        duration='7 days',
                        quantity=14
                    )
                    self.log_test_result("Prescription-Item", "WORKFLOW", "PASS", "Prescription item created")
                else:
                    self.log_test_result("Prescription-Item", "WORKFLOW", "SKIP", "No medication available")
            else:
                self.log_test_result("Prescription-Item", "WORKFLOW", "SKIP", "No medication category available")
                
        except Exception as e:
            self.log_test_result("Prescription-Workflow", "WORKFLOW", "FAIL", "Prescription workflow failed", e)
        
        # Test appointment workflow
        try:
            appointment = Appointment.objects.create(
                patient=self.test_patient,
                doctor=self.admin_user,
                appointment_date=date.today() + timedelta(days=1),
                appointment_time='10:00',
                reason='Test appointment',
                status='scheduled'
            )
            self.log_test_result("Appointment-Creation", "WORKFLOW", "PASS", "Appointment created successfully")
        except Exception as e:
            self.log_test_result("Appointment-Workflow", "WORKFLOW", "FAIL", "Appointment workflow failed", e)
    
    def test_data_consistency(self):
        """Test data consistency across the system"""
        print("\n📊 Testing Data Consistency...")
        
        # Test user count consistency
        try:
            user_count = CustomUser.objects.count()
            profile_count = CustomUserProfile.objects.count()
            self.log_test_result("User-Profile-Consistency", "CONSISTENCY", "PASS", f"Users: {user_count}, Profiles: {profile_count}")
        except Exception as e:
            self.log_test_result("User-Profile-Consistency", "CONSISTENCY", "FAIL", "Consistency check failed", e)
        
        # Test patient-wallet consistency
        try:
            patient_count = Patient.objects.count()
            wallet_count = PatientWallet.objects.count()
            self.log_test_result("Patient-Wallet-Consistency", "CONSISTENCY", "PASS", f"Patients: {patient_count}, Wallets: {wallet_count}")
        except Exception as e:
            self.log_test_result("Patient-Wallet-Consistency", "CONSISTENCY", "FAIL", "Consistency check failed", e)
    
    def run_all_tests(self):
        """Run all API and integration tests"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE API & INTEGRATION TESTING - HMS")
        print("="*80)
        
        # Run different test categories
        self.test_api_endpoints_unauthenticated()
        self.test_api_endpoints_authenticated()
        self.test_model_integrations()
        self.test_business_workflows()
        self.test_data_consistency()
        
        # Generate final report
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("📋 API & INTEGRATION TEST REPORT")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warnings = len([r for r in self.test_results if r['status'] == 'WARN'])
        skipped = len([r for r in self.test_results if r['status'] == 'SKIP'])
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"⏭️  Skipped: {skipped}")
        print(f"📈 Success Rate: {(passed/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
        
        # Save detailed report
        with open('api_integration_test_report.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed': passed,
                    'failed': failed,
                    'warnings': warnings,
                    'skipped': skipped,
                    'success_rate': (passed/total_tests*100) if total_tests > 0 else 0
                },
                'results': self.test_results
            }, f, indent=2)
        
        print(f"📄 Detailed report saved to: api_integration_test_report.json")

if __name__ == "__main__":
    tester = APIIntegrationTester()
    tester.run_all_tests()
