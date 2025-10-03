#!/usr/bin/env python3
"""
Test script to verify the current state of the referral modal
"""

import os
import django
import requests
from django.test import Client
from django.contrib.auth import get_user_model

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from patients.models import Patient

User = get_user_model()

def test_referral_modal_integration():
    """Test the referral modal integration on patient detail page"""
    print("="*80)
    print("TESTING REFERRAL MODAL INTEGRATION")
    print("="*80)
    
    # Get a test patient
    try:
        patient = Patient.objects.first()
        if not patient:
            print("❌ No patients found in database")
            return False
        
        print(f"✅ Test patient: {patient.get_full_name()} (ID: {patient.id})")
        
        # Get a test user
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ No active users found")
            return False
        
        print(f"✅ Test user: {user.get_full_name()}")
        
        # Create client and login
        client = Client()
        client.force_login(user)
        
        # Test patient detail page
        url = f'/patients/{patient.id}/'
        print(f"\n🔍 Testing URL: {url}")
        
        response = client.get(url)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            
            # Check for referral modal components
            checks = {
                'Refer Patient Button': 'id="referPatientBtn"' in content,
                'Referral Modal': 'id="referralModal"' in content,
                'Modal Form': 'id="referralForm"' in content,
                'Doctor Select': 'id="referred_to"' in content,
                'Reason Textarea': 'id="reason"' in content,
                'Notes Textarea': 'id="notes"' in content,
                'Submit Button': 'id="submitReferralBtn"' in content,
                'LoadDoctors Function': 'function loadDoctorsForReferral' in content,
                'API Call': '/accounts/api/users/?role=doctor' in content,
                'Bootstrap Modal': 'data-bs-toggle="modal"' in content,
                'CSRF Token': '{% csrf_token %}' in content or 'csrfmiddlewaretoken' in content,
            }
            
            print("\n📋 Modal Component Checks:")
            all_passed = True
            for check, result in checks.items():
                status = "✅" if result else "❌"
                print(f"   {status} {check}")
                if not result:
                    all_passed = False
            
            # Test API endpoint
            print("\n🔍 Testing API Endpoint:")
            api_response = client.get('/accounts/api/users/?role=doctor')
            print(f"   Status: {api_response.status_code}")
            
            if api_response.status_code == 200:
                try:
                    doctors = api_response.json()
                    print(f"   ✅ Doctors found: {len(doctors)}")
                    if doctors:
                        print(f"   📋 Sample doctor: {doctors[0].get('first_name', '')} {doctors[0].get('last_name', '')}")
                except:
                    print("   ❌ Failed to parse JSON response")
            else:
                print(f"   ❌ API endpoint failed with status {api_response.status_code}")
            
            return all_passed
        else:
            print(f"❌ Patient detail page failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        return False

def test_referral_form_submission():
    """Test actual referral form submission"""
    print("\n" + "="*80)
    print("TESTING REFERRAL FORM SUBMISSION")
    print("="*80)
    
    try:
        # Get test data
        patient = Patient.objects.first()
        user = User.objects.filter(is_active=True).first() 
        doctor = User.objects.filter(is_active=True).exclude(id=user.id).first()
        
        if not all([patient, user, doctor]):
            print("❌ Missing test data (patient, user, or doctor)")
            return False
        
        print(f"✅ Patient: {patient.get_full_name()}")
        print(f"✅ User: {user.get_full_name()}")
        print(f"✅ Target Doctor: {doctor.get_full_name()}")
        
        # Create client and login
        client = Client()
        client.force_login(user)
        
        # Test form submission
        url = f'/consultations/referrals/create/{patient.id}/'
        form_data = {
            'patient': patient.id,
            'referred_to': doctor.id,
            'reason': 'Test referral submission',
            'notes': 'This is a test referral',
        }
        
        print(f"\n🔍 Testing form submission to: {url}")
        print(f"   Form data: {form_data}")
        
        response = client.post(url, data=form_data)
        print(f"   Response status: {response.status_code}")
        
        if response.status_code in [200, 302]:  # Success or redirect
            print("✅ Form submission successful")
            
            # Check if referral was created
            from consultations.models import Referral
            referral = Referral.objects.filter(
                patient=patient,
                referring_doctor=user,
                referred_to=doctor
            ).first()
            
            if referral:
                print(f"✅ Referral created: {referral}")
                return True
            else:
                print("❌ Referral not found in database")
                return False
        else:
            print(f"❌ Form submission failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error during form submission test: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Referral Modal Test Suite")
    
    # Test 1: Modal Integration
    modal_test = test_referral_modal_integration()
    
    # Test 2: Form Submission
    form_test = test_referral_form_submission()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Modal Integration: {'✅ PASSED' if modal_test else '❌ FAILED'}")
    print(f"Form Submission:  {'✅ PASSED' if form_test else '❌ FAILED'}")
    
    if modal_test and form_test:
        print("\n🎉 ALL TESTS PASSED - Referral modal is working correctly!")
    else:
        print("\n⚠️  SOME TESTS FAILED - Please check the output above for details")
    
    print("="*80)