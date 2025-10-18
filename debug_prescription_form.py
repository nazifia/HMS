#!/usr/bin/env python3
"""
Debug script to check what's being rendered on the prescription page
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from pharmacy.views import prescription_list
from pharmacy.forms import PrescriptionSearchForm

User = get_user_model()

def debug_prescription_form():
    """Debug the prescription form rendering"""
    print("Debugging prescription form...")
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/pharmacy/prescriptions/')
    
    # Get an existing user
    user = User.objects.filter().first()
    if not user:
        print("No users found in database.")
        return
    
    request.user = user
    
    try:
        # Get the view response
        response = prescription_list(request)
        print(f"View executed successfully, status: {response.status_code}")
        
        # Get content
        if hasattr(response, 'content'):
            content = response.content.decode('utf-8')
        else:
            try:
                response.render()
                content = response.content.decode('utf-8')
            except:
                content = str(response)
        
        # Count search input fields
        search_inputs = content.count('name="search"')
        print(f"Found {search_inputs} input fields with name='search'")
        
        # Count search forms
        search_forms = content.count('id="prescription-search-form"')
        print(f"Found {search_forms} forms with id='prescription-search-form'")
        
        # Look for any other form elements that might have search fields
        import re
        all_forms = re.findall(r'<form[^>]*>(.*?)</form>', content, re.DOTALL)
        print(f"Found {len(all_forms)} total forms on page")
        
        for i, form_content in enumerate(all_forms):
            if 'name="search"' in form_content:
                print(f"Form {i+1} contains search field:")
                # Extract form id if present
                form_id_match = re.search(r'id="([^"]*)"', form_content.split('>')[0])
                form_id = form_id_match.group(1) if form_id_match else "no-id"
                print(f"  Form ID: {form_id}")
                
        # Look for all forms and their contents
        print(f"\nAnalyzing all {len(all_forms)} forms:")
        for i, form_content in enumerate(all_forms):
            print(f"\nForm {i+1}:")
            # Extract form attributes
            form_start = form_content.split('>')[0] if '>' in form_content else form_content
            print(f"  Attributes: {form_start}")
            
            # Check if it has search field
            if 'name="search"' in form_content:
                print("  Contains search field: YES")
            else:
                print("  Contains search field: NO")
            
            # Check for other input fields
            inputs = re.findall(r'<input[^>]*name="([^"]*)"[^>]*>', form_content)
            if inputs:
                print(f"  Other input fields: {inputs}")
        
        # Look for any duplicated elements
        if search_inputs > 1:
            print("\nPotential duplicate search fields found!")
            # Find all search input elements with their context
            search_input_matches = re.finditer(r'(<[^>]*name="search"[^>]*>)', content)
            for i, match in enumerate(search_input_matches):
                print(f"Search input {i+1}: {match.group(1)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_prescription_form()
