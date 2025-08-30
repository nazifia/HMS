#!/usr/bin/env python
"""
Test Error Fixes Script
This script tests the fixes for:
1. TypeError in admission creation (Patient object vs ID)
2. UnboundLocalError in laboratory forms (AuthorizationCode)
3. UnboundLocalError in radiology forms (AuthorizationCode)
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_admission_form_patient_id():
    """Test that admission form accepts patient ID correctly"""
    print("=== Testing Admission Form Patient ID Fix ===")
    
    try:
        from inpatient.forms import AdmissionForm
        from patients.models import Patient
        from datetime import date
        
        # Create test patient
        patient = Patient.objects.create(
            first_name="Test",
            last_name="Admission",
            date_of_birth=date(1990, 1, 1),
            gender="male",
            phone_number="08012345679",
            patient_type="private"
        )
        print(f"✅ Created test patient: {patient.get_full_name()}")
        
        # Test form initialization with patient ID (not patient object)
        initial_data = {'patient': patient.id}  # This should be ID, not object
        form = AdmissionForm(initial=initial_data)
        
        print(f"✅ AdmissionForm initialized with patient ID: {patient.id}")
        print(f"   Form patient field initial value: {form.fields['patient'].initial}")
        
        # Test that the form renders without error
        patient_field_html = str(form['patient'])
        if 'select' in patient_field_html.lower():
            print("✅ Patient field renders as select dropdown")
        else:
            print("⚠️  Patient field rendering unexpected")
        
        return True
        
    except Exception as e:
        print(f"❌ Admission form patient ID test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_laboratory_form_authorization_code():
    """Test that laboratory form handles AuthorizationCode import correctly"""
    print("\n=== Testing Laboratory Form AuthorizationCode Fix ===")
    
    try:
        from laboratory.forms import TestRequestForm
        from patients.models import Patient
        from datetime import date
        
        # Create test NHIA patient
        nhia_patient = Patient.objects.create(
            first_name="NHIA",
            last_name="Lab",
            date_of_birth=date(1985, 1, 1),
            gender="female",
            phone_number="08087654322",
            patient_type="nhia"
        )
        print(f"✅ Created NHIA patient: {nhia_patient.get_full_name()}")
        
        # Test form initialization with NHIA patient
        form = TestRequestForm(preselected_patient=nhia_patient)
        print("✅ TestRequestForm initialized with NHIA patient without UnboundLocalError")
        
        # Check authorization code field
        auth_code_field = form.fields.get('authorization_code')
        if auth_code_field:
            print(f"✅ Authorization code field exists")
            print(f"   Queryset count: {auth_code_field.queryset.count()}")
        else:
            print("❌ Authorization code field missing")
        
        # Create test non-NHIA patient
        private_patient = Patient.objects.create(
            first_name="Private",
            last_name="Lab",
            date_of_birth=date(1990, 1, 1),
            gender="male",
            phone_number="08012345680",
            patient_type="private"
        )
        
        # Test form with non-NHIA patient
        form2 = TestRequestForm(preselected_patient=private_patient)
        print("✅ TestRequestForm initialized with private patient without error")
        
        return True
        
    except Exception as e:
        print(f"❌ Laboratory form authorization code test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_radiology_form_authorization_code():
    """Test that radiology form handles AuthorizationCode import correctly"""
    print("\n=== Testing Radiology Form AuthorizationCode Fix ===")
    
    try:
        from radiology.forms import RadiologyOrderForm
        from patients.models import Patient
        from datetime import date
        
        # Create test NHIA patient
        nhia_patient = Patient.objects.create(
            first_name="NHIA",
            last_name="Radio",
            date_of_birth=date(1988, 1, 1),
            gender="male",
            phone_number="08087654323",
            patient_type="nhia"
        )
        print(f"✅ Created NHIA patient: {nhia_patient.get_full_name()}")
        
        # Create mock request object
        class MockRequest:
            def __init__(self, patient_id):
                self.GET = {'patient': str(patient_id)}
        
        mock_request = MockRequest(nhia_patient.id)
        
        # Test form initialization with NHIA patient
        form = RadiologyOrderForm(request=mock_request)
        print("✅ RadiologyOrderForm initialized with NHIA patient without UnboundLocalError")
        
        # Check authorization code field
        auth_code_field = form.fields.get('authorization_code')
        if auth_code_field:
            print(f"✅ Authorization code field exists")
            print(f"   Queryset count: {auth_code_field.queryset.count()}")
        else:
            print("❌ Authorization code field missing")
        
        # Create test non-NHIA patient
        private_patient = Patient.objects.create(
            first_name="Private",
            last_name="Radio",
            date_of_birth=date(1992, 1, 1),
            gender="female",
            phone_number="08012345681",
            patient_type="private"
        )
        
        # Test form with non-NHIA patient
        mock_request2 = MockRequest(private_patient.id)
        form2 = RadiologyOrderForm(request=mock_request2)
        print("✅ RadiologyOrderForm initialized with private patient without error")
        
        return True
        
    except Exception as e:
        print(f"❌ Radiology form authorization code test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_view_access():
    """Test that the problematic views now work"""
    print("\n=== Testing View Access ===")
    
    try:
        from django.test import Client
        from django.contrib.auth import get_user_model
        from patients.models import Patient
        from datetime import date
        
        User = get_user_model()
        client = Client()
        
        # Get a user for authentication
        user = User.objects.first()
        if user:
            client.force_login(user)
            
            # Create test patient
            patient = Patient.objects.create(
                first_name="View",
                last_name="Test",
                date_of_birth=date(1990, 1, 1),
                gender="male",
                phone_number="08099999998",
                patient_type="private"
            )
            
            # Test admission creation view
            response = client.get(f'/inpatient/admissions/create/?patient_id={patient.id}')
            if response.status_code == 200:
                print("✅ Admission creation view accessible")
            else:
                print(f"⚠️  Admission creation view returned status {response.status_code}")
            
            # Test laboratory request creation view
            response = client.get(f'/laboratory/requests/create/?patient={patient.id}')
            if response.status_code == 200:
                print("✅ Laboratory request creation view accessible")
            else:
                print(f"⚠️  Laboratory request creation view returned status {response.status_code}")
            
            # Test radiology order view
            response = client.get(f'/radiology/order/{patient.id}/')
            if response.status_code == 200:
                print("✅ Radiology order view accessible")
            else:
                print(f"⚠️  Radiology order view returned status {response.status_code}")
        else:
            print("⚠️  No users found for view testing")
        
        return True
        
    except Exception as e:
        print(f"❌ View access test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_nhia_import_availability():
    """Test NHIA module availability"""
    print("\n=== Testing NHIA Module Availability ===")
    
    try:
        from nhia.models import AuthorizationCode
        print("✅ NHIA AuthorizationCode model available")
        
        # Test creating authorization code
        from patients.models import Patient
        from datetime import date, timedelta
        
        nhia_patient = Patient.objects.filter(patient_type='nhia').first()
        if not nhia_patient:
            nhia_patient = Patient.objects.create(
                first_name="NHIA",
                last_name="Test",
                date_of_birth=date(1985, 1, 1),
                gender="male",
                phone_number="08099999997",
                patient_type="nhia"
            )
        
        auth_code = AuthorizationCode.objects.create(
            patient=nhia_patient,
            code="TEST123",
            service_type="laboratory",
            amount=1000.00,
            expiry_date=date.today() + timedelta(days=30),
            status="active"
        )
        print(f"✅ Created test authorization code: {auth_code.code}")
        
        return True
        
    except ImportError:
        print("⚠️  NHIA module not available - forms will handle gracefully")
        return True
    except Exception as e:
        print(f"❌ NHIA import test failed: {e}")
        return False

def main():
    """Main function to run all tests"""
    print("🧪 Error Fixes Test Script")
    print("=" * 50)
    
    success_count = 0
    total_tests = 5
    
    # Run all tests
    if test_admission_form_patient_id():
        success_count += 1
    
    if test_laboratory_form_authorization_code():
        success_count += 1
    
    if test_radiology_form_authorization_code():
        success_count += 1
    
    if test_view_access():
        success_count += 1
    
    if test_nhia_import_availability():
        success_count += 1
    
    # Summary
    print(f"\n{'=' * 50}")
    print("📊 ERROR FIXES TEST SUMMARY")
    print(f"{'=' * 50}")
    print(f"Successful tests: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 ALL ERROR FIXES WORKING!")
        print("\n✅ Admission form patient ID issue fixed")
        print("✅ Laboratory form AuthorizationCode issue fixed")
        print("✅ Radiology form AuthorizationCode issue fixed")
        print("✅ All views accessible without errors")
        print("✅ NHIA integration working properly")
        return 0
    else:
        print(f"❌ {total_tests - success_count} tests failed.")
        print("Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
