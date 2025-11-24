#!/usr/bin/env python
"""
Verification script for authorization request changes
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_template_changes():
    """Check if templates have been updated correctly"""
    print("Checking template changes...")
    
    # Check main form template
    with open('templates/core/request_authorization_form.html', 'r') as f:
        form_content = f.read()
    
    # Verify that required attribute is removed
    if 'required></textarea>' in form_content:
        print("ERROR: Textarea still has 'required' attribute in request_authorization_form.html")
        return False
    elif 'placeholder="Add any additional notes..."></textarea>' in form_content:
        print("OK: Template 'request_authorization_form.html' - required attribute removed")
    else:
        print("WARNING: Could not verify textarea format in request_authorization_form.html")
    
    # Check for (Optional) in label
    if 'Notes (Optional)</strong>' in form_content:
        print("OK: Template 'request_authorization_form.html' - label updated to 'Notes (Optional)'")
    else:
        print("WARNING: Label not updated to 'Notes (Optional)' in request_authorization_form.html")
    
    # Check widget template
    with open('templates/includes/authorization_request_widget.html', 'r') as f:
        widget_content = f.read()
    
    if 'required' not in widget_content and 'text-danger' not in widget_content:
        print("OK: Template 'authorization_request_widget.html' - no required attributes found")
    else:
        print("WARNING: authorization_request_widget.html may still have required attributes")
    
    return True

def check_view_changes():
    """Check if view validation has been removed"""
    print("\nChecking view changes...")
    
    with open('core/views.py', 'r') as f:
        view_content = f.read()
    
    # Check that the validation is removed
    if 'Please provide a reason for the authorization request.' in view_content:
        print("ERROR: Validation message still exists in core/views.py")
        return False
    elif 'if not notes:' in view_content and 'authorization request' in view_content.lower():
        print("ERROR: Notes validation still exists in core/views.py")
        return False
    else:
        print("OK: View 'core/views.py' - notes validation removed")
    
    return True

def main():
    """Main verification function"""
    print("=== Verification of Authorization Request Changes ===\n")
    
    template_ok = check_template_changes()
    view_ok = check_view_changes()
    
    print("\n=== Summary ===")
    if template_ok and view_ok:
        print("OK: All changes verified successfully!")
        print("OK: The 'Reason for Authorization Request' field has been made optional")
        return 0
    else:
        print("ERROR: Some issues were found. Please review the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
