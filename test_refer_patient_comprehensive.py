"""
Comprehensive test script for the Refer Patient functionality
Tests all components: API, Form, View, Modal, and JavaScript integration
"""

import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from patients.models import Patient
from consultations.models import Referral
from consultations.forms import ReferralForm
from accounts.models import Role, Department
import json

User = get_user_model()

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def test_api_endpoint():
    """Test 1: Verify the API endpoint for loading doctors"""
    print_section("TEST 1: API Endpoint for Loading Doctors")
    
    client = Client()
    
    # Create a test user and log in
    try:
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ No active users found in database")
            return False
        
        client.force_login(user)
        print(f"✅ Logged in as: {user.get_full_name()} ({user.username})")
        
        # Test the API endpoint
        response = client.get('/accounts/api/users/?role=doctor')
        
        print(f"\nAPI Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API endpoint working")
            print(f"   - Doctors found: {len(data)}")
            
            if len(data) > 0:
                print(f"\n   Sample doctors:")
                for i, doctor in enumerate(data[:3], 1):
                    print(f"   {i}. {doctor.get('full_name', 'N/A')} - Dept: {doctor.get('department', 'N/A')}")
                return True
            else:
                print("⚠️  No doctors found in database")
                print("   Checking user roles...")
                
                # Check if any users have doctor role
                doctor_role = Role.objects.filter(name__iexact='doctor').first()
                if doctor_role:
                    doctors_with_role = User.objects.filter(roles=doctor_role, is_active=True)
                    print(f"   - Users with 'doctor' role: {doctors_with_role.count()}")
                    for doc in doctors_with_role[:3]:
                        print(f"     • {doc.get_full_name()}")
                else:
                    print("   - No 'doctor' role found in database")
                
                return False
        else:
            print(f"❌ API endpoint failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing API endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_referral_form():
    """Test 2: Verify the ReferralForm"""
    print_section("TEST 2: Referral Form Validation")
    
    try:
        # Get a patient and doctors
        patient = Patient.objects.first()
        if not patient:
            print("❌ No patients found in database")
            return False
        
        print(f"✅ Test patient: {patient.get_full_name()}")
        
        # Get doctors
        doctor_role = Role.objects.filter(name__iexact='doctor').first()
        if doctor_role:
            doctors = User.objects.filter(roles=doctor_role, is_active=True)
        else:
            doctors = User.objects.filter(is_active=True, is_staff=True)
        
        if doctors.count() < 2:
            print("⚠️  Need at least 2 doctors for testing")
            return False
        
        referring_doctor = doctors[0]
        referred_to = doctors[1]
        
        print(f"✅ Referring doctor: {referring_doctor.get_full_name()}")
        print(f"✅ Referred to: {referred_to.get_full_name()}")
        
        # Test form with valid data
        form_data = {
            'patient': patient.id,
            'referred_to': referred_to.id,
            'reason': 'Test referral reason',
            'notes': 'Test notes'
        }
        
        form = ReferralForm(data=form_data)
        
        if form.is_valid():
            print("✅ Form validation passed")
            print(f"   - Patient queryset count: {form.fields['patient'].queryset.count()}")
            print(f"   - Referred_to queryset count: {form.fields['referred_to'].queryset.count()}")
            return True
        else:
            print("❌ Form validation failed")
            print(f"   Errors: {form.errors}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing form: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_referral_creation():
    """Test 3: Test creating a referral through the view"""
    print_section("TEST 3: Referral Creation via View")
    
    client = Client()
    
    try:
        # Get test data
        patient = Patient.objects.first()
        if not patient:
            print("❌ No patients found")
            return False
        
        doctor_role = Role.objects.filter(name__iexact='doctor').first()
        if doctor_role:
            doctors = User.objects.filter(roles=doctor_role, is_active=True)
        else:
            doctors = User.objects.filter(is_active=True, is_staff=True)
        
        if doctors.count() < 2:
            print("❌ Need at least 2 doctors")
            return False
        
        referring_doctor = doctors[0]
        referred_to = doctors[1]
        
        # Log in as referring doctor
        client.force_login(referring_doctor)
        print(f"✅ Logged in as: {referring_doctor.get_full_name()}")
        
        # Get initial referral count
        initial_count = Referral.objects.count()
        
        # Submit referral form
        url = reverse('consultations:create_referral', kwargs={'patient_id': patient.id})
        data = {
            'patient': patient.id,
            'referred_to': referred_to.id,
            'reason': 'Test referral for comprehensive testing',
            'notes': 'This is a test referral created by automated test'
        }
        
        response = client.post(url, data, follow=True)
        
        print(f"\nResponse Status: {response.status_code}")
        
        # Check if referral was created
        final_count = Referral.objects.count()
        
        if final_count > initial_count:
            print(f"✅ Referral created successfully")
            
            # Get the created referral
            referral = Referral.objects.latest('created_at')
            print(f"\n   Referral Details:")
            print(f"   - Patient: {referral.patient.get_full_name()}")
            print(f"   - From: Dr. {referral.referring_doctor.get_full_name()}")
            print(f"   - To: Dr. {referral.referred_to.get_full_name()}")
            print(f"   - Reason: {referral.reason}")
            print(f"   - Status: {referral.status}")
            print(f"   - Requires Authorization: {referral.requires_authorization}")
            print(f"   - Authorization Status: {referral.authorization_status}")
            
            return True
        else:
            print(f"❌ Referral was not created")
            print(f"   Initial count: {initial_count}, Final count: {final_count}")
            
            # Check for error messages
            if hasattr(response, 'context') and response.context:
                messages = list(response.context.get('messages', []))
                if messages:
                    print(f"\n   Messages:")
                    for msg in messages:
                        print(f"   - {msg}")
            
            return False
            
    except Exception as e:
        print(f"❌ Error testing referral creation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_modal_template():
    """Test 4: Verify the modal template exists and has correct structure"""
    print_section("TEST 4: Modal Template Structure")
    
    try:
        template_path = 'templates/patients/patient_detail.html'
        
        if not os.path.exists(template_path):
            print(f"❌ Template not found at: {template_path}")
            return False
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for modal elements
        checks = {
            'Modal div': 'id="referralModal"' in content,
            'Modal form': 'action="{% url \'consultations:create_referral\' patient.id %}"' in content,
            'CSRF token': '{% csrf_token %}' in content,
            'Referred_to select': 'id="referred_to"' in content,
            'Reason textarea': 'id="reason"' in content,
            'Notes textarea': 'id="notes"' in content,
            'Submit button': 'type="submit"' in content,
            'JavaScript function': 'loadDoctorsForReferral' in content,
            'API call': '/accounts/api/users/?role=doctor' in content,
        }
        
        print("\nModal Template Checks:")
        all_passed = True
        for check_name, result in checks.items():
            status = "✅" if result else "❌"
            print(f"   {status} {check_name}")
            if not result:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Error checking template: {str(e)}")
        return False

def test_url_configuration():
    """Test 5: Verify URL configuration"""
    print_section("TEST 5: URL Configuration")
    
    try:
        # Test API URL
        try:
            api_url = reverse('accounts:api_users')
            print(f"✅ API URL configured: {api_url}")
        except Exception as e:
            print(f"❌ API URL not configured: {str(e)}")
            return False
        
        # Test referral creation URL
        try:
            referral_url = reverse('consultations:create_referral')
            print(f"✅ Referral URL (no patient): {referral_url}")
        except Exception as e:
            print(f"⚠️  Referral URL (no patient) not configured: {str(e)}")
        
        # Test referral creation URL with patient
        try:
            referral_url_with_patient = reverse('consultations:create_referral', kwargs={'patient_id': 1})
            print(f"✅ Referral URL (with patient): {referral_url_with_patient}")
        except Exception as e:
            print(f"❌ Referral URL (with patient) not configured: {str(e)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking URLs: {str(e)}")
        return False

def run_all_tests():
    """Run all tests and provide summary"""
    print("\n" + "="*80)
    print("  COMPREHENSIVE REFER PATIENT FUNCTIONALITY TEST")
    print("="*80)
    
    tests = [
        ("URL Configuration", test_url_configuration),
        ("API Endpoint", test_api_endpoint),
        ("Referral Form", test_referral_form),
        ("Modal Template", test_modal_template),
        ("Referral Creation", test_referral_creation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {str(e)}")
            results[test_name] = False
    
    # Print summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {status}: {test_name}")
    
    print(f"\n   Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n   🎉 All tests passed! Refer patient functionality is working correctly.")
    else:
        print("\n   ⚠️  Some tests failed. Please review the output above for details.")
    
    return passed == total

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

