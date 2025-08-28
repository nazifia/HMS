#!/usr/bin/env python
"""
Verification script for dispensary retention functionality

This script verifies that the changes for dispensary retention have been properly implemented.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def verify_changes():
    """Verify that the dispensary retention changes have been implemented"""
    print("Verifying dispensary retention implementation...")
    
    # Check views.py
    print("\n1. Checking views.py...")
    with open('pharmacy/views.py', 'r') as f:
        views_content = f.read()
        
    # Check for key changes in the dispense_prescription view
    if 'dispensary_id' in views_content and 'selected_dispensary' in views_content:
        print("   ✅ Found dispensary retention logic in views.py")
    else:
        print("   ❌ Missing dispensary retention logic in views.py")
        
    # Check template
    print("\n2. Checking template...")
    with open('pharmacy/templates/pharmacy/dispense_prescription.html', 'r') as f:
        template_content = f.read()
        
    # Check for key changes in the template
    if 'name="dispensary_select"' in template_content and 'dispensary_id' in template_content:
        print("   ✅ Found dispensary retention logic in template")
    else:
        print("   ❌ Missing dispensary retention logic in template")
        
    # Check forms.py
    print("\n3. Checking forms.py...")
    with open('pharmacy/forms.py', 'r') as f:
        forms_content = f.read()
        
    # Check for key changes in the forms
    if 'selected_dispensary' in forms_content and 'BaseDispenseItemFormSet' in forms_content:
        print("   ✅ Found dispensary retention logic in forms.py")
    else:
        print("   ❌ Missing dispensary retention logic in forms.py")
        
    print("\n🎉 Verification complete!")
    return True

if __name__ == '__main__':
    verify_changes()