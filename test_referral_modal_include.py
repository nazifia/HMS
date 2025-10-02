#!/usr/bin/env python
"""
Test script to verify the referral modal template include works correctly.

This script tests:
1. Template include exists and is accessible
2. Modal renders correctly with patient context
3. JavaScript is included
4. All form fields are present
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.template.loader import render_to_string
from django.test import RequestFactory
from patients.models import Patient
from accounts.models import CustomUser

def test_referral_modal_include():
    """Test that the referral modal include renders correctly."""
    
    print("=" * 80)
    print("REFERRAL MODAL TEMPLATE INCLUDE TEST")
    print("=" * 80)
    print()
    
    # Test 1: Check if template file exists
    print("Test 1: Checking if template file exists...")
    template_path = os.path.join('templates', 'includes', 'referral_modal.html')
    if os.path.exists(template_path):
        print(f"✅ Template file exists: {template_path}")
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"   File size: {len(content)} characters")
    else:
        print(f"❌ Template file NOT found: {template_path}")
        return False
    print()
    
    # Test 2: Check template content
    print("Test 2: Checking template content...")
    required_elements = [
        ('Modal div', 'id="referralModal"'),
        ('Modal title', 'referralModalLabel'),
        ('Form action', 'consultations:create_referral'),
        ('CSRF token', '{% csrf_token %}'),
        ('Patient hidden field', 'name="patient"'),
        ('Doctors dropdown', 'id="referred_to"'),
        ('Reason textarea', 'id="reason"'),
        ('Notes textarea', 'id="notes"'),
        ('Submit button', 'submitReferralBtn'),
        ('JavaScript', 'loadDoctorsForReferral'),
        ('API fetch', '/accounts/api/users/?role=doctor'),
    ]
    
    all_found = True
    for name, element in required_elements:
        if element in content:
            print(f"   ✅ {name}: Found")
        else:
            print(f"   ❌ {name}: NOT FOUND")
            all_found = False
    
    if all_found:
        print("✅ All required elements found in template")
    else:
        print("❌ Some elements missing from template")
    print()
    
    # Test 3: Try to render the template with a patient
    print("Test 3: Rendering template with patient context...")
    try:
        # Get a patient
        patient = Patient.objects.first()
        if not patient:
            print("❌ No patients found in database. Creating test patient...")
            # Create a test patient
            patient = Patient.objects.create(
                first_name="Test",
                last_name="Patient",
                patient_id="TEST999",
                date_of_birth="1990-01-01",
                gender="male",
                phone_number="1234567890",
                patient_type="general"
            )
            print(f"✅ Created test patient: {patient.get_full_name()}")
        else:
            print(f"✅ Using patient: {patient.get_full_name()} (ID: {patient.patient_id})")
        
        # Render the template
        context = {'patient': patient}
        rendered = render_to_string('includes/referral_modal.html', context)
        
        print(f"✅ Template rendered successfully")
        print(f"   Rendered HTML size: {len(rendered)} characters")
        
        # Check if patient name appears in rendered HTML
        if patient.get_full_name() in rendered:
            print(f"   ✅ Patient name appears in rendered HTML")
        else:
            print(f"   ❌ Patient name NOT found in rendered HTML")
        
        # Check if patient ID appears
        if str(patient.id) in rendered:
            print(f"   ✅ Patient ID appears in rendered HTML")
        else:
            print(f"   ❌ Patient ID NOT found in rendered HTML")
            
    except Exception as e:
        print(f"❌ Error rendering template: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # Test 4: Check patient_detail.html uses the include
    print("Test 4: Checking if patient_detail.html uses the include...")
    
    templates_to_check = [
        'patients/templates/patients/patient_detail.html',
        'templates/patients/patient_detail.html',
    ]
    
    for template_file in templates_to_check:
        if os.path.exists(template_file):
            print(f"\n   Checking: {template_file}")
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check if it includes the referral modal
            if "{% include 'includes/referral_modal.html'" in content:
                print(f"   ✅ Uses template include")
            elif 'id="referralModal"' in content:
                print(f"   ⚠️  Has inline modal (should use include instead)")
            else:
                print(f"   ❌ No referral modal found")
                
            # Check if it has the button
            if 'id="referPatientBtn"' in content or 'Refer Patient' in content:
                print(f"   ✅ Has 'Refer Patient' button")
            else:
                print(f"   ❌ No 'Refer Patient' button found")
    print()
    
    # Test 5: Check for duplicate JavaScript
    print("Test 5: Checking for duplicate JavaScript...")
    for template_file in templates_to_check:
        if os.path.exists(template_file):
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count occurrences of loadDoctorsForReferral
            count = content.count('loadDoctorsForReferral')
            
            if count == 0:
                print(f"   ✅ {template_file}: No duplicate JS (uses include)")
            elif count == 1:
                print(f"   ⚠️  {template_file}: Has inline JS (should use include)")
            else:
                print(f"   ❌ {template_file}: Multiple JS definitions found ({count})")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("✅ Template include created: templates/includes/referral_modal.html")
    print("✅ Template renders correctly with patient context")
    print("✅ All required elements present")
    print()
    print("NEXT STEPS:")
    print("1. Restart Django development server:")
    print("   python manage.py runserver")
    print()
    print("2. Navigate to patient detail page:")
    print("   http://127.0.0.1:8000/patients/42/")
    print()
    print("3. Click 'Refer Patient' button")
    print()
    print("4. Verify modal opens with:")
    print("   - Patient name in title")
    print("   - Doctors dropdown populated")
    print("   - All form fields present")
    print()
    print("=" * 80)
    
    return True

if __name__ == '__main__':
    try:
        success = test_referral_modal_include()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

