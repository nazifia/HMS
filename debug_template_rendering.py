#!/usr/bin/env python3
"""
Debug script to check template rendering issues
"""

import os
import django
from django.test import Client
from django.contrib.auth import get_user_model

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from patients.models import Patient

User = get_user_model()

def debug_template_rendering():
    """Debug the template rendering"""
    print("="*80)
    print("DEBUGGING TEMPLATE RENDERING")
    print("="*80)
    
    # Get test data
    patient = Patient.objects.first()
    user = User.objects.filter(is_active=True).first()
    
    if not patient or not user:
        print("❌ Missing test data")
        return
    
    print(f"✅ Patient: {patient.get_full_name()} (ID: {patient.id})")
    print(f"✅ User: {user.get_full_name()}")
    
    # Create client and login
    client = Client()
    client.force_login(user)
    
    # Get the patient detail page
    url = f'/patients/{patient.id}/'
    print(f"\n🔍 Testing URL: {url}")
    
    response = client.get(url)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        
        # Save the rendered content to a file for inspection
        with open('debug_rendered_page.html', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Page content saved to 'debug_rendered_page.html'")
        
        # Check for specific content
        print("\n🔍 Checking for referral content:")
        
        # Search for key elements
        checks = {
            'Refer Patient Button': 'id="referPatientBtn"',
            'Modal div': 'id="referralModal"',
            'Modal dialog': 'modal-dialog',
            'Modal content': 'modal-content',
            'Modal header': 'modal-header',
            'Modal body': 'modal-body',
            'Modal footer': 'modal-footer',
            'Form element': 'id="referralForm"',
            'Doctor select': 'id="referred_to"',
            'Reason textarea': 'id="reason"',
            'Notes textarea': 'id="notes"',
            'Submit button': 'id="submitReferralBtn"',
            'JavaScript function': 'function loadDoctorsForReferral',
            'API call': '/accounts/api/users/?role=doctor',
            'Bootstrap modal trigger': 'data-bs-toggle="modal"',
            'Bootstrap modal target': 'data-bs-target="#referralModal"',
        }
        
        for check, pattern in checks.items():
            found = pattern in content
            status = "✅" if found else "❌"
            print(f"   {status} {check}: {pattern}")
            
        # Look for the area around the referral button
        print("\n🔍 Content around referral button:")
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'referPatientBtn' in line:
                start = max(0, i-3)
                end = min(len(lines), i+4)
                print("   Context:")
                for j in range(start, end):
                    marker = " >>> " if j == i else "     "
                    print(f"{marker}Line {j+1}: {lines[j][:100]}")
                break
                
        # Look for modal content
        print("\n🔍 Looking for modal content:")
        modal_found = False
        for i, line in enumerate(lines):
            if 'referralModal' in line:
                modal_found = True
                start = max(0, i-2)
                end = min(len(lines), i+10)
                print("   Modal context:")
                for j in range(start, end):
                    marker = " >>> " if j == i else "     "
                    print(f"{marker}Line {j+1}: {lines[j][:150]}")
                break
        
        if not modal_found:
            print("   ❌ No modal content found in rendered page")
            
            # Check if endblock is closing the template early
            print("\n🔍 Checking template blocks:")
            for i, line in enumerate(lines):
                if 'endblock' in line.lower():
                    print(f"   Line {i+1}: {line.strip()}")
    
    else:
        print(f"❌ Failed to get page content: {response.status_code}")

if __name__ == "__main__":
    debug_template_rendering()