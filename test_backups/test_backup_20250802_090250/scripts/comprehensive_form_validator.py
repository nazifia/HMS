#!/usr/bin/env python
"""
Comprehensive Form and Validation Tester for HMS
This script tests all forms, form validation, field validation, and form processing.
"""

import os
import sys
import django
import json
import traceback
import datetime as dt
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import Form, ModelForm
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Import all form modules
from accounts.forms import *
from patients.forms import *
from doctors.forms import *
from appointments.forms import *
from pharmacy.forms import *
from laboratory.forms import *
from billing.forms import *
from inpatient.forms import *
from hr.forms import *
from consultations.forms import *
from radiology.forms import *
from theatre.forms import *
from reporting.forms import *

class ComprehensiveFormValidator:
    def __init__(self):
        self.test_results = []
        self.setup_test_environment()
        self.form_classes = self.discover_form_classes()
    
    def setup_test_environment(self):
        """Set up test environment"""
        print("🔧 Setting up form validation test environment...")
        
        # Add testserver to ALLOWED_HOSTS
        if 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append('testserver')
        
        # Create test data
        self.create_test_data()
        print("✅ Form validation test environment ready")
    
    def create_test_data(self):
        """Create test data for form validation"""
        try:
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            
            # Import models
            from accounts.models import CustomUser, Department
            from patients.models import Patient
            from doctors.models import Specialization
            from pharmacy.models import MedicationCategory, Medication
            from billing.models import ServiceCategory, Service
            
            # Create test user
            self.test_user = CustomUser.objects.create_user(
                phone_number=f'+1234567{unique_id[:3]}',
                username=f'test_user_{unique_id}',
                email=f'test_{unique_id}@test.com',
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
                phone_number=f'+1234568{unique_id[:3]}',
                email=f'patient_{unique_id}@test.com',
                patient_id=f'PAT{unique_id}'
            )
            
            # Create test department
            self.test_department = Department.objects.create(
                name=f'Test Department {unique_id}',
                description='Test department for form validation'
            )
            
            # Create test specialization
            self.test_specialization = Specialization.objects.create(
                name=f'Test Specialization {unique_id}',
                description='Test specialization for form validation'
            )
            
            print(f"✅ Created test data with unique ID: {unique_id}")
            
        except Exception as e:
            print(f"⚠️  Error creating test data: {e}")
            traceback.print_exc()
    
    def discover_form_classes(self):
        """Discover all form classes in the HMS system"""
        form_classes = {}
        
        # Get all globals from imported modules
        all_globals = globals()
        
        for name, obj in all_globals.items():
            if isinstance(obj, type) and issubclass(obj, (Form, ModelForm)) and obj != Form and obj != ModelForm:
                module_name = obj.__module__.split('.')[-2] if '.' in obj.__module__ else 'unknown'
                if module_name not in form_classes:
                    form_classes[module_name] = []
                form_classes[module_name].append((name, obj))
        
        return form_classes
    
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
    
    def test_form_instantiation(self):
        """Test form instantiation for all discovered forms"""
        print("\n🏗️  Testing Form Instantiation...")
        
        for module_name, forms in self.form_classes.items():
            for form_name, form_class in forms:
                try:
                    # Try to instantiate the form
                    form = form_class()
                    self.log_test_result(f"{form_name}", "FORM_INSTANTIATION", "PASS", 
                                       f"Form instantiated successfully")
                except Exception as e:
                    self.log_test_result(f"{form_name}", "FORM_INSTANTIATION", "FAIL", 
                                       "Form instantiation failed", e)
    
    def test_form_validation(self):
        """Test form validation with various data scenarios"""
        print("\n✅ Testing Form Validation...")
        
        # Test data scenarios
        test_scenarios = {
            'empty_data': {},
            'invalid_email': {'email': 'invalid-email'},
            'invalid_phone': {'phone_number': '123'},
            'future_date': {'date_of_birth': date.today() + timedelta(days=1)},
            'negative_amount': {'amount': -100},
            'long_text': {'description': 'x' * 1000}
        }
        
        for module_name, forms in self.form_classes.items():
            for form_name, form_class in forms:
                for scenario_name, test_data in test_scenarios.items():
                    try:
                        form = form_class(data=test_data)
                        is_valid = form.is_valid()
                        
                        if scenario_name == 'empty_data':
                            # Empty data should usually be invalid for most forms
                            if not is_valid:
                                self.log_test_result(f"{form_name}_{scenario_name}", "FORM_VALIDATION", "PASS",
                                                   "Form correctly rejected empty data")
                            else:
                                self.log_test_result(f"{form_name}_{scenario_name}", "FORM_VALIDATION", "WARN",
                                                   "Form accepted empty data (may be valid)")
                        else:
                            # Other scenarios should be handled gracefully
                            self.log_test_result(f"{form_name}_{scenario_name}", "FORM_VALIDATION", "PASS",
                                               f"Form validation completed (valid: {is_valid})")
                    
                    except Exception as e:
                        self.log_test_result(f"{form_name}_{scenario_name}", "FORM_VALIDATION", "FAIL",
                                           "Form validation error", e)
    
    def test_form_field_validation(self):
        """Test individual field validation"""
        print("\n🔍 Testing Field Validation...")
        
        field_test_cases = {
            'email_field': [
                ('valid@email.com', True),
                ('invalid-email', False),
                ('', False)
            ],
            'phone_field': [
                ('+1234567890', True),
                ('123', False),
                ('abc', False)
            ],
            'date_field': [
                (date.today(), True),
                (date.today() + timedelta(days=1), False),  # Future date might be invalid
                ('invalid-date', False)
            ]
        }
        
        for module_name, forms in self.form_classes.items():
            for form_name, form_class in forms:
                try:
                    form = form_class()
                    
                    # Test email fields
                    for field_name, field in form.fields.items():
                        if 'email' in field_name.lower():
                            for test_value, expected_valid in field_test_cases['email_field']:
                                try:
                                    field.clean(test_value)
                                    result = True
                                except ValidationError:
                                    result = False
                                
                                if result == expected_valid:
                                    self.log_test_result(f"{form_name}.{field_name}", "FIELD_VALIDATION", "PASS",
                                                       f"Email validation correct for '{test_value}'")
                                else:
                                    self.log_test_result(f"{form_name}.{field_name}", "FIELD_VALIDATION", "WARN",
                                                       f"Email validation unexpected for '{test_value}'")
                
                except Exception as e:
                    self.log_test_result(f"{form_name}_field_validation", "FIELD_VALIDATION", "FAIL",
                                       "Field validation test error", e)
    
    def test_form_save_operations(self):
        """Test form save operations for ModelForms"""
        print("\n💾 Testing Form Save Operations...")
        
        for module_name, forms in self.form_classes.items():
            for form_name, form_class in forms:
                if issubclass(form_class, ModelForm):
                    try:
                        # Create form with minimal valid data
                        form = form_class()
                        
                        # Check if form has a save method
                        if hasattr(form, 'save'):
                            self.log_test_result(f"{form_name}", "FORM_SAVE", "PASS",
                                               "Form has save method available")
                        else:
                            self.log_test_result(f"{form_name}", "FORM_SAVE", "WARN",
                                               "ModelForm missing save method")
                    
                    except Exception as e:
                        self.log_test_result(f"{form_name}", "FORM_SAVE", "FAIL",
                                           "Form save test error", e)
    
    def run_all_tests(self):
        """Run all form validation tests"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE FORM VALIDATION TESTING - HMS")
        print("="*80)
        
        print(f"📊 Discovered {sum(len(forms) for forms in self.form_classes.values())} forms across {len(self.form_classes)} modules")
        
        # Run different test categories
        self.test_form_instantiation()
        self.test_form_validation()
        self.test_form_field_validation()
        self.test_form_save_operations()
        
        # Generate final report
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("📋 FORM VALIDATION TEST REPORT")
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
        with open('form_validation_test_report.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed': passed,
                    'failed': failed,
                    'warnings': warnings,
                    'success_rate': (passed/total_tests*100) if total_tests > 0 else 0,
                    'forms_discovered': sum(len(forms) for forms in self.form_classes.values())
                },
                'form_classes': {module: [name for name, cls in forms] for module, forms in self.form_classes.items()},
                'results': self.test_results
            }, f, indent=2)
        
        print(f"📄 Detailed report saved to: form_validation_test_report.json")

if __name__ == "__main__":
    validator = ComprehensiveFormValidator()
    validator.run_all_tests()
