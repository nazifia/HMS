#!/usr/bin/env python
"""
Comprehensive Test Suite for Hospital Management System (HMS)
This script tests all major functionalities of the HMS Django application.
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.management import execute_from_command_line
from decimal import Decimal
import json
from datetime import datetime, date, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Import models after Django setup
from accounts.models import CustomUser, CustomUserProfile
from patients.models import Patient, PatientWallet, WalletTransaction, Vitals, MedicalHistory
from doctors.models import Doctor, Specialization
from pharmacy.models import Medication, Prescription, PrescriptionItem
from billing.models import Invoice, Payment, Service
from laboratory.models import TestRequest, Test
from appointments.models import Appointment
from core.models import AuditLog, InternalNotification
from inpatient.models import Admission, Ward, Bed
from hr.models import StaffProfile, Designation, Leave, Department
from consultations.models import Consultation
from radiology.models import RadiologyTest, RadiologyOrder
from theatre.models import Surgery, OperationTheatre
from nhia.models import NHIAPatient
from retainership.models import RetainershipPatient
from reporting.models import Dashboard

class HMSComprehensiveTest:
    def __init__(self):
        # Add testserver to ALLOWED_HOSTS for testing
        from django.conf import settings
        if 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append('testserver')
        
        self.client = Client(HTTP_HOST='testserver')
        self.test_results = []
        self.setup_test_data()
    
    def log_test(self, test_name, status, message="", response_code=None):
        """Log test results"""
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        if response_code:
            result['response_code'] = response_code
        self.test_results.append(result)
        status_symbol = "[PASS]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[WARN]"
        error_msg = f"{message} (HTTP {response_code})" if response_code and status == "FAIL" else message
        print(f"{status_symbol} {test_name}: {status} - {error_msg}")
    
    def setup_test_data(self):
        """Create test data for comprehensive testing"""
        try:
            # Clear existing test data to avoid UNIQUE constraint conflicts
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            
            # Delete existing test users
            CustomUser.objects.filter(username__startswith='test_').delete()
            Patient.objects.filter(first_name__in=['Test', 'John']).delete()
            Department.objects.filter(name__startswith='Test').delete()
            
            # Create test users with unique identifiers
            self.admin_user = CustomUser.objects.create_superuser(
                phone_number=f'+1234567{unique_id[:3]}',
                username=f'test_admin_{unique_id}',
                email=f'admin_{unique_id}@test.com',
                password='testpass123',
                first_name='Admin',
                last_name='User'
            )
            
            self.doctor_user = CustomUser.objects.create_user(
                phone_number=f'+1234568{unique_id[:3]}',
                username=f'test_doctor_{unique_id}',
                email=f'doctor_{unique_id}@test.com',
                password='testpass123',
                first_name='Dr. John',
                last_name='Smith'
            )
            
            self.nurse_user = CustomUser.objects.create_user(
                phone_number=f'+1234569{unique_id[:3]}',
                username=f'test_nurse_{unique_id}',
                email=f'nurse_{unique_id}@test.com',
                password='testpass123',
                first_name='Nurse',
                last_name='Johnson'
            )
            
            self.receptionist_user = CustomUser.objects.create_user(
                phone_number=f'+1234560{unique_id[:3]}',
                username=f'test_receptionist_{unique_id}',
                email=f'receptionist_{unique_id}@test.com',
                password='testpass123',
                first_name='Reception',
                last_name='Staff'
            )
            
            # Create test department
            self.test_department, created = Department.objects.get_or_create(
                name='Test Department',
                defaults={'description': 'Test department for testing'}
            )
            
            # Import Role model for proper role assignment
            from accounts.models import Role
            
            # Set roles and departments through profiles
            self.admin_user.profile.role = 'admin'
            self.admin_user.profile.department = self.test_department
            self.admin_user.profile.save()
            
            self.doctor_user.profile.role = 'doctor'
            self.doctor_user.profile.department = self.test_department
            self.doctor_user.profile.save()
            
            self.nurse_user.profile.role = 'nurse'
            self.nurse_user.profile.department = self.test_department
            self.nurse_user.profile.save()
            
            self.receptionist_user.profile.role = 'receptionist'
            self.receptionist_user.profile.department = self.test_department
            self.receptionist_user.profile.save()
            
            # Assign proper roles for permission-based access
            try:
                admin_role, _ = Role.objects.get_or_create(name='admin')
                doctor_role, _ = Role.objects.get_or_create(name='doctor')
                nurse_role, _ = Role.objects.get_or_create(name='nurse')
                receptionist_role, _ = Role.objects.get_or_create(name='receptionist')
                pharmacist_role, _ = Role.objects.get_or_create(name='pharmacist')
                accountant_role, _ = Role.objects.get_or_create(name='accountant')
                health_record_officer_role, _ = Role.objects.get_or_create(name='health_record_officer')
                
                # Assign roles to users
                self.admin_user.roles.add(admin_role)
                self.doctor_user.roles.add(doctor_role)
                self.nurse_user.roles.add(nurse_role)
                self.receptionist_user.roles.add(receptionist_role)
                
                # Also assign additional roles for comprehensive testing
                self.admin_user.roles.add(pharmacist_role, accountant_role, health_record_officer_role)
                
            except Exception as e:
                print(f"Warning: Could not assign roles: {e}")
            
            # Create test patient
            self.test_patient = Patient.objects.create(
                first_name='John',
                last_name='Doe',
                date_of_birth=date(1990, 1, 1),
                gender='M',
                blood_group='O+',
                email='john.doe@test.com',
                phone_number='9876543210',
                address='123 Test Street',
                city='Test City',
                state='Test State',
                patient_id='PAT001'
            )
            
            # Create specialization and doctor profile
            self.test_specialization, created = Specialization.objects.get_or_create(
                name='General Medicine',
                defaults={'description': 'General medical practice'}
            )
            
            self.test_doctor = Doctor.objects.create(
                user=self.doctor_user,
                specialization=self.test_specialization,
                department=self.test_department,
                license_number='DOC123456',
                experience='3-5',
                qualification='MBBS, MD',
                consultation_fee=500.00
            )
            
            # Create test dashboard for reporting system
            self.test_dashboard = Dashboard.objects.create(
                name='Test Dashboard',
                description='Test dashboard for comprehensive testing',
                created_by=self.admin_user,
                is_public=True,
                is_default=True
            )
            
            self.log_test("Test Data Setup", "PASS", "All test data created successfully")
            
        except Exception as e:
            self.log_test("Test Data Setup", "FAIL", f"Error: {str(e)}")
    
    def test_authentication_system(self):
        """Test user authentication and authorization"""
        try:
            # Test login with different user types using force_login for testing
            login_tests = [
                (self.admin_user, 'admin'),
                (self.doctor_user, 'doctor'),
                (self.nurse_user, 'nurse'),
                (self.receptionist_user, 'receptionist')
            ]
            
            for user, role in login_tests:
                try:
                    self.client.force_login(user)
                    self.log_test(f"Login Test - {role}", "PASS", f"User {user.phone_number} logged in successfully")
                except Exception as e:
                    self.log_test(f"Login Test - {role}", "FAIL", f"Login failed for {user.phone_number}: {str(e)}")
            
            # Test logout
            try:
                self.client.logout()
                self.log_test("Logout Test", "PASS", "User logged out successfully")
            except Exception as e:
                self.log_test("Logout Test", "FAIL", f"Logout failed: {str(e)}")
            
        except Exception as e:
            self.log_test("Authentication System", "FAIL", f"Error: {str(e)}")
    
    def test_patient_management(self):
        """Test patient registration, update, and management"""
        try:
            # Login as admin
            self.client.force_login(self.admin_user)
            
            # Test patient registration
            patient_data = {
                'first_name': 'Jane',
                'last_name': 'Smith',
                'date_of_birth': '1985-05-15',
                'gender': 'F',
                'blood_group': 'A+',
                'marital_status': 'single',
                'email': 'jane.smith@test.com',
                'phone_number': '9876543211',
                'address': '456 Test Avenue',
                'city': 'Test City',
                'state': 'Test State',
                'country': 'India',
                'is_active': True
            }
            
            response = self.client.post('/patients/register/', patient_data)
            if response.status_code in [200, 302]:
                self.log_test("Patient Registration", "PASS", "New patient registered successfully")
            else:
                self.log_test("Patient Registration", "FAIL", f"Status code: {response.status_code}")
            
            # Test patient list view
            response = self.client.get('/patients/')
            self.log_test("Patient List View", "PASS" if response.status_code == 200 else "FAIL")
            
            # Test patient detail view
            response = self.client.get(f'/patients/{self.test_patient.id}/')
            self.log_test("Patient Detail View", "PASS" if response.status_code == 200 else "FAIL")
            
            # Test patient wallet functionality
            wallet, created = PatientWallet.objects.get_or_create(patient=self.test_patient)
            wallet.credit(Decimal('100.00'), "Test credit")
            wallet.debit(Decimal('25.00'), "Test debit")
            
            if wallet.balance == Decimal('75.00'):
                self.log_test("Patient Wallet Operations", "PASS", "Wallet credit/debit working correctly")
            else:
                self.log_test("Patient Wallet Operations", "FAIL", f"Expected 75.00, got {wallet.balance}")
            
        except Exception as e:
            self.log_test("Patient Management", "FAIL", f"Error: {str(e)}")
    
    def test_doctor_management(self):
        """Test doctor profiles and management"""
        try:
            self.client.force_login(self.admin_user)
            
            # Test doctor list view
            response = self.client.get('/doctors/')
            self.log_test("Doctor List View", "PASS" if response.status_code == 200 else "FAIL")
            
            # Test doctor detail view
            response = self.client.get(f'/doctors/{self.test_doctor.id}/')
            self.log_test("Doctor Detail View", "PASS" if response.status_code == 200 else "FAIL")
            
            # Test doctor schedule
            response = self.client.get('/appointments/schedules/')
            self.log_test("Doctor Schedule View", "PASS" if response.status_code == 200 else "FAIL")
            
        except Exception as e:
            self.log_test("Doctor Management", "FAIL", f"Error: {str(e)}")
    
    def test_appointment_system(self):
        """Test appointment booking and management"""
        try:
            self.client.force_login(self.receptionist_user)
            
            # Test appointment booking
            appointment_data = {
                'patient': self.test_patient.id,
                'doctor': self.test_doctor.id,
                'appointment_date': (datetime.now() + timedelta(days=1)).date(),
                'appointment_time': '10:00',
                'reason': 'Regular checkup'
            }
            
            response = self.client.post('/appointments/create/', appointment_data)
            self.log_test("Appointment Booking", "PASS" if response.status_code in [200, 302] else "FAIL")
            
            # Test appointment list
            response = self.client.get('/appointments/')
            self.log_test("Appointment List View", "PASS" if response.status_code == 200 else "FAIL")
            
        except Exception as e:
            self.log_test("Appointment System", "FAIL", f"Error: {str(e)}")
    
    def test_pharmacy_system(self):
        """Test pharmacy and prescription management"""
        try:
            self.client.force_login(self.admin_user)
            
            # Create test medication
            medication = Medication.objects.create(
                name='Test Medication',
                generic_name='Test Generic',
                manufacturer='Test Pharma',
                dosage_form='tablet',
                strength='500mg',
                price=10.00
            )
            
            # Test pharmacy views
            response = self.client.get('/pharmacy/dashboard/')
            self.log_test("Pharmacy Dashboard", "PASS" if response.status_code == 200 else "FAIL")
            
            response = self.client.get('/pharmacy/inventory/')
            self.log_test("Medicine List View", "PASS" if response.status_code == 200 else "FAIL", 
                          message="" if response.status_code == 200 else "Failed to load medicine list", 
                          response_code=response.status_code)
            
            # Test prescription creation
            prescription_data = {
                'patient': self.test_patient.id,
                'doctor': self.doctor_user.id,
                'prescription_date': datetime.now().date(),
                'prescription_type': 'outpatient',
                'diagnosis': 'Test diagnosis',
                'instructions': 'Take as directed'
            }
            
            response = self.client.post('/pharmacy/prescriptions/create/', prescription_data)
            self.log_test("Prescription Creation", "PASS" if response.status_code in [200, 302] else "FAIL")
            
        except Exception as e:
            self.log_test("Pharmacy System", "FAIL", f"Error: {str(e)}")
    
    def test_laboratory_system(self):
        """Test laboratory test management"""
        try:
            self.client.force_login(self.doctor_user)
            
            # Test lab views
            response = self.client.get('/laboratory/tests/')
            self.log_test("Laboratory Dashboard", "PASS" if response.status_code == 200 else "FAIL")
            
            response = self.client.get('/laboratory/tests/')
            self.log_test("Lab Tests View", "PASS" if response.status_code == 200 else "FAIL")
            
        except Exception as e:
            self.log_test("Laboratory System", "FAIL", f"Error: {str(e)}")
    
    def test_billing_system(self):
        """Test billing and payment processing"""
        try:
            self.client.force_login(self.admin_user)
            
            # Test billing views
            response = self.client.get('/billing/medications/')
            self.log_test("Billing Dashboard", "PASS" if response.status_code == 200 else "FAIL",
                          message="" if response.status_code == 200 else "Failed to load billing dashboard",
                          response_code=response.status_code)
            
            response = self.client.get('/billing/')
            self.log_test("Invoice List View", "PASS" if response.status_code == 200 else "FAIL",
                          message="" if response.status_code == 200 else "Failed to load invoice list",
                          response_code=response.status_code)
            
            # Create test service and invoice
            service = Service.objects.create(
                name='Test Service',
                price=100.00
            )
            
            invoice = Invoice.objects.create(
                patient=self.test_patient,
                due_date=(datetime.now() + timedelta(days=30)).date(),
                subtotal=100.00,
                tax_amount=0.00,
                total_amount=100.00,
                status='pending'
            )
            
            # Test payment processing
            payment = Payment.objects.create(
                invoice=invoice,
                amount=100.00,
                payment_method='cash'
            )
            
            self.log_test("Invoice and Payment Creation", "PASS", "Invoice and payment created successfully")
            
        except Exception as e:
            self.log_test("Billing System", "FAIL", f"Error: {str(e)}")
    
    def test_inpatient_system(self):
        """Test inpatient management"""
        try:
            self.client.force_login(self.nurse_user)
            
            # Test inpatient views
            response = self.client.get('/inpatient/wards/')
            self.log_test("Inpatient Dashboard", "PASS" if response.status_code == 200 else "FAIL",
                          message="" if response.status_code == 200 else "Failed to load inpatient dashboard",
                          response_code=response.status_code)
            
            response = self.client.get('/inpatient/beds/')
            self.log_test("Bed Management View", "PASS" if response.status_code == 200 else "FAIL",
                          message="" if response.status_code == 200 else "Failed to load bed management",
                          response_code=response.status_code)
            
        except Exception as e:
            self.log_test("Inpatient System", "FAIL", f"Error: {str(e)}")
    
    def test_hr_system(self):
        """Test HR management"""
        try:
            self.client.force_login(self.admin_user)
            
            # Test HR views
            response = self.client.get('/hr/dashboard/')
            self.log_test("HR Dashboard", "PASS" if response.status_code == 200 else "FAIL",
                          message="" if response.status_code == 200 else "Failed to load HR dashboard",
                          response_code=response.status_code)
            
            response = self.client.get('/hr/staff/')
            self.log_test("Employee List View", "PASS" if response.status_code == 200 else "FAIL",
                          message="" if response.status_code == 200 else "Failed to load employee list",
                          response_code=response.status_code)
            
        except Exception as e:
            self.log_test("HR System", "FAIL", f"Error: {str(e)}")
    
    def test_reporting_system(self):
        """Test reporting functionality"""
        try:
            self.client.force_login(self.admin_user)
            
            # Test reporting views
            response = self.client.get('/reporting/dashboard/')
            self.log_test("Reporting Dashboard", "PASS" if response.status_code == 200 else "FAIL",
                          message="" if response.status_code == 200 else "Failed to load reporting dashboard",
                          response_code=response.status_code)
            
        except Exception as e:
            self.log_test("Reporting System", "FAIL", f"Error: {str(e)}")
    
    def test_nhia_system(self):
        """Test NHIA integration"""
        try:
            self.client.force_login(self.admin_user)
            
            # Test NHIA views
            response = self.client.get('/nhia/patients/')
            self.log_test("NHIA Dashboard", "PASS" if response.status_code == 200 else "FAIL")
            
            response = self.client.get('/nhia/register-patient/')
            self.log_test("NHIA Patient Registration", "PASS" if response.status_code == 200 else "FAIL")
            
        except Exception as e:
            self.log_test("NHIA System", "FAIL", f"Error: {str(e)}")
    
    def test_theatre_system(self):
        """Test theatre/surgery management"""
        try:
            self.client.force_login(self.doctor_user)
            
            # Test theatre views
            response = self.client.get('/theatre/')
            self.log_test("Theatre Dashboard", "PASS" if response.status_code == 200 else "FAIL")
            
        except Exception as e:
            self.log_test("Theatre System", "FAIL", f"Error: {str(e)}")
    
    def test_api_endpoints(self):
        """Test API functionality"""
        try:
            # Test API authentication
            response = self.client.get('/api/accounts/')
            self.log_test("API Endpoint Access", "PASS" if response.status_code in [200, 401, 403] else "FAIL")
            
        except Exception as e:
            self.log_test("API Endpoints", "FAIL", f"Error: {str(e)}")
    
    def test_dashboard_system(self):
        """Test dashboard functionality"""
        try:
            self.client.force_login(self.admin_user)
            
            # Test main dashboard
            response = self.client.get('/dashboard/')
            self.log_test("Main Dashboard", "PASS" if response.status_code == 200 else "FAIL")
            
        except Exception as e:
            self.log_test("Dashboard System", "FAIL", f"Error: {str(e)}")
    
    def test_core_functionality(self):
        """Test core system functionality"""
        try:
            # Test audit logging
            audit_log = AuditLog.objects.create(
                user=self.admin_user,
                action='test_action',
                details='Test audit log entry'
            )
            
            # Test notifications
            notification = InternalNotification.objects.create(
                user=self.admin_user,
                message='Test notification'
            )
            
            self.log_test("Core Functionality", "PASS", "Audit logging and notifications working")
            
        except Exception as e:
            self.log_test("Core Functionality", "FAIL", f"Error: {str(e)}")
    
    def run_all_tests(self):
        """Run all test suites"""
        print("\n" + "="*60)
        print("HOSPITAL MANAGEMENT SYSTEM - COMPREHENSIVE TEST SUITE")
        print("="*60)
        
        test_suites = [
            self.test_authentication_system,
            self.test_patient_management,
            self.test_doctor_management,
            self.test_appointment_system,
            self.test_pharmacy_system,
            self.test_laboratory_system,
            self.test_billing_system,
            self.test_inpatient_system,
            self.test_hr_system,
            self.test_reporting_system,
            self.test_nhia_system,
            self.test_theatre_system,
            self.test_api_endpoints,
            self.test_dashboard_system,
            self.test_core_functionality
        ]
        
        for test_suite in test_suites:
            try:
                test_suite()
            except Exception as e:
                self.log_test(test_suite.__name__, "FAIL", f"Test suite failed: {str(e)}")
        
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\nFAILED TESTS:")
            print("-" * 40)
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"✗ {result['test']}: {result['message']}")
        
        # Save detailed report to file
        with open('test_report.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100
                },
                'detailed_results': self.test_results
            }, f, indent=2)
        
        print(f"\nDetailed test report saved to: test_report.json")
        print("="*60)

if __name__ == '__main__':
    # Run the comprehensive test suite
    test_runner = HMSComprehensiveTest()
    test_runner.run_all_tests()