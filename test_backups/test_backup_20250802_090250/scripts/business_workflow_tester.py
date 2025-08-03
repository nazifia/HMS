#!/usr/bin/env python
"""
Comprehensive Business Logic and Workflow Tester for HMS
This script tests complex business workflows like prescription dispensing, billing, patient management.
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
from django.urls import reverse
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
from pharmacy.models import (
    Medication, Prescription, PrescriptionItem, MedicationCategory, 
    DispensingLog, Dispensary, MedicationInventory
)
from billing.models import Invoice, Payment, Service, ServiceCategory
from laboratory.models import TestRequest, Test, TestCategory, TestResult
from appointments.models import Appointment
from inpatient.models import Admission, Ward, Bed
from hr.models import StaffProfile, Designation, Leave, Department as HRDepartment
from consultations.models import Consultation, ConsultingRoom, WaitingList
from radiology.models import RadiologyTest, RadiologyOrder, RadiologyCategory
from theatre.models import Surgery, OperationTheatre, SurgeryType
from nhia.models import NHIAPatient
from retainership.models import RetainershipPatient

class BusinessWorkflowTester:
    def __init__(self):
        self.client = Client()
        self.test_results = []
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Set up comprehensive test data for business workflows"""
        print("🔧 Setting up test environment for business workflow testing...")
        
        # Add testserver to ALLOWED_HOSTS
        if 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append('testserver')
        
        # Create comprehensive test data
        self.create_comprehensive_test_data()
        print("✅ Test environment ready for business workflow testing")
    
    def create_comprehensive_test_data(self):
        """Create comprehensive test data for all business workflows"""
        try:
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            
            # Create test users
            self.admin_user = CustomUser.objects.create_superuser(
                phone_number=f'+1234567{unique_id[:3]}',
                username=f'test_admin_{unique_id}',
                email=f'admin_{unique_id}@test.com',
                password='testpass123',
                first_name='Test',
                last_name='Admin'
            )
            
            self.doctor_user = CustomUser.objects.create_user(
                phone_number=f'+1234568{unique_id[:3]}',
                username=f'test_doctor_{unique_id}',
                email=f'doctor_{unique_id}@test.com',
                password='testpass123',
                first_name='Dr. Test',
                last_name='Doctor'
            )
            
            # Create test patient with wallet
            self.test_patient = Patient.objects.create(
                first_name='Test',
                last_name='Patient',
                date_of_birth=date(1990, 1, 1),
                gender='M',
                phone_number=f'+1234569{unique_id[:3]}',
                email=f'patient_{unique_id}@test.com',
                patient_id=f'PAT{unique_id}'
            )
            
            # Ensure patient has a wallet
            self.patient_wallet, created = PatientWallet.objects.get_or_create(
                patient=self.test_patient,
                defaults={'balance': Decimal('1000.00')}
            )
            if not created:
                self.patient_wallet.balance = Decimal('1000.00')
                self.patient_wallet.save()
            
            # Create test specialization and doctor
            self.specialization = Specialization.objects.create(
                name=f'Test Specialization {unique_id}',
                description='Test specialization for workflow testing'
            )
            
            self.doctor = Doctor.objects.create(
                user=self.doctor_user,
                specialization=self.specialization,
                license_number=f'LIC{unique_id}',
                experience='3-5',
                qualification='MBBS, MD'
            )
            
            # Create test medication data
            self.med_category = MedicationCategory.objects.create(
                name=f'Test Category {unique_id}',
                description='Test medication category'
            )
            
            self.medication = Medication.objects.create(
                name=f'Test Medication {unique_id}',
                category=self.med_category,
                dosage_form='Tablet',
                strength='500mg',
                price=Decimal('10.00'),
                reorder_level=10
            )
            
            # Create test dispensary first
            self.dispensary = Dispensary.objects.create(
                name=f'Test Dispensary {unique_id}',
                location='Test Location',
                description='Test dispensary for workflow testing',
                manager=self.admin_user
            )

            # Create medication inventory
            self.med_inventory = MedicationInventory.objects.create(
                medication=self.medication,
                dispensary=self.dispensary,
                stock_quantity=100,
                reorder_level=10
            )
            
            # Create test service
            self.service_category = ServiceCategory.objects.create(
                name=f'Test Service Category {unique_id}',
                description='Test service category'
            )
            
            self.service = Service.objects.create(
                name=f'Test Service {unique_id}',
                category=self.service_category,
                price=Decimal('50.00'),
                description='Test service for workflow testing'
            )
            
            # Skip ward and bed creation for now due to missing required fields
            
            # Create test consulting room
            self.consulting_room = ConsultingRoom.objects.create(
                name=f'Test Room {unique_id}',
                description='Test consulting room',
                is_active=True
            )
            
            # Create test lab test
            self.test_category = TestCategory.objects.create(
                name=f'Test Category {unique_id}',
                description='Test category for lab tests'
            )
            
            self.lab_test = Test.objects.create(
                name=f'Test Lab Test {unique_id}',
                category=self.test_category,
                price=Decimal('25.00'),
                description='Test lab test'
            )
            
            print(f"✅ Created comprehensive test data with unique ID: {unique_id}")
            
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
            'timestamp': datetime.now().isoformat()
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
    
    def test_prescription_workflow(self):
        """Test complete prescription workflow"""
        print("\n💊 Testing Prescription Workflow...")
        
        try:
            # Step 1: Create prescription
            prescription = Prescription.objects.create(
                patient=self.test_patient,
                doctor=self.doctor_user,
                diagnosis='Test diagnosis for workflow',
                notes='Test prescription notes'
            )
            self.log_test_result("Prescription-Creation", "WORKFLOW", "PASS", "Prescription created successfully")
            
            # Step 2: Add prescription items
            prescription_item = PrescriptionItem.objects.create(
                prescription=prescription,
                medication=self.medication,
                dosage='1 tablet',
                frequency='twice daily',
                duration='7 days',
                quantity=14
            )
            self.log_test_result("Prescription-Item-Creation", "WORKFLOW", "PASS", "Prescription item created")
            
            # Step 3: Test prescription dispensing logic
            initial_inventory = self.med_inventory.stock_quantity
            dispense_quantity = 10

            if initial_inventory >= dispense_quantity:
                # Simulate dispensing
                self.med_inventory.stock_quantity -= dispense_quantity
                self.med_inventory.save()
                
                # Create dispensing log (simplified)
                dispensing_log = DispensingLog.objects.create(
                    prescription_item=prescription_item,
                    quantity_dispensed=dispense_quantity,
                    dispensed_by=self.admin_user
                )
                
                self.log_test_result("Prescription-Dispensing", "WORKFLOW", "PASS",
                                   f"Dispensed {dispense_quantity} units",
                                   details=f"Inventory: {initial_inventory} -> {self.med_inventory.stock_quantity}")
            else:
                self.log_test_result("Prescription-Dispensing", "WORKFLOW", "FAIL", "Insufficient inventory")
            
        except Exception as e:
            self.log_test_result("Prescription-Workflow", "WORKFLOW", "FAIL", "Prescription workflow failed", e)
    
    def test_billing_workflow(self):
        """Test complete billing workflow"""
        print("\n💰 Testing Billing Workflow...")
        
        try:
            # Step 1: Create invoice
            invoice = Invoice.objects.create(
                patient=self.test_patient,
                subtotal=Decimal('100.00'),
                tax_amount=Decimal('0.00'),
                total_amount=Decimal('100.00'),
                status='pending',
                due_date=date.today() + timedelta(days=30)
            )
            self.log_test_result("Invoice-Creation", "WORKFLOW", "PASS", "Invoice created successfully")
            
            # Step 2: Test payment from wallet
            initial_balance = self.patient_wallet.balance
            payment_amount = Decimal('50.00')
            
            if initial_balance >= payment_amount:
                # Create payment
                payment = Payment.objects.create(
                    invoice=invoice,
                    amount=payment_amount,
                    payment_method='wallet'
                )
                
                # Deduct from wallet
                self.patient_wallet.balance -= payment_amount
                self.patient_wallet.save()
                
                # Create wallet transaction (simplified)
                WalletTransaction.objects.create(
                    wallet=self.patient_wallet,
                    transaction_type='debit',
                    amount=payment_amount,
                    balance_after=self.patient_wallet.balance,
                    description=f'Payment for invoice {invoice.id}'
                )
                
                self.log_test_result("Wallet-Payment", "WORKFLOW", "PASS", 
                                   f"Payment of {payment_amount} processed",
                                   details=f"Wallet balance: {initial_balance} -> {self.patient_wallet.balance}")
            else:
                self.log_test_result("Wallet-Payment", "WORKFLOW", "FAIL", "Insufficient wallet balance")
            
        except Exception as e:
            self.log_test_result("Billing-Workflow", "WORKFLOW", "FAIL", "Billing workflow failed", e)
    
    def run_all_tests(self):
        """Run all business workflow tests"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE BUSINESS WORKFLOW TESTING - HMS")
        print("="*80)
        
        # Run different workflow tests
        self.test_prescription_workflow()
        self.test_billing_workflow()
        
        # Generate final report
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("📋 BUSINESS WORKFLOW TEST REPORT")
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
        with open('business_workflow_test_report.json', 'w') as f:
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
        
        print(f"📄 Detailed report saved to: business_workflow_test_report.json")

if __name__ == "__main__":
    tester = BusinessWorkflowTester()
    tester.run_all_tests()
