#!/usr/bin/env python3
"""
Debug script to find the source of duplicate search fields
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

def debug_duplicate_search():
    """Debug to find source of duplicate search fields"""
    print("Debugging duplicate search fields...")
    
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
        
        # Get content
        if hasattr(response, 'content'):
            content = response.content.decode('utf-8')
        else:
            try:
                response.render()
                content = response.content.decode('utf-8')
            except:
                content = str(response)
        
        # Find all search input fields and their context
        import re
        
        # Find all input elements with name="search"
        search_input_pattern = r'(<[^>]*name="search"[^>]*>)'
        search_inputs = re.findall(search_input_pattern, content)
        
        print(f"Found {len(search_inputs)} search input elements in HTML:")
        
        for i, search_input in enumerate(search_inputs):
            print(f"\nSearch Input {i+1}:")
            print(search_input)
            
            # Find the surrounding context (line before and after)
            input_pos = content.find(search_input)
            if input_pos != -1:
                # Get some context around the input
                start = max(0, input_pos - 200)
                end = min(len(content), input_pos + len(search_input) + 200)
                context = content[start:end]
                
                print("Context:")
                print("-" * 50)
                print(context)
                print("-" * 50)
        
        # Look for any duplicate forms or includes
        print(f"\nLooking for potential issues...")
        
        # Check for multiple search forms
        form_pattern = r'<form[^>]*id="[^"]*search[^"]*"[^>]*>.*?</form>'
        search_forms = re.findall(form_pattern, content, re.DOTALL)
        print(f"Found {len(search_forms)} search-related forms")
        
        # Check for any template includes that might contain search
        include_pattern = r'{% include[^%]*search[^%]*%}'
        includes = re.findall(include_pattern, content)
        if includes:
            print(f"Found search-related includes: {includes}")
        
        # Check for any x-data or Alpine.js components that might duplicate
        alpine_pattern = r'x-data="[^"]*search[^"]*"'
        alpine_components = re.findall(alpine_pattern, content)
        if alpine_components:
            print(f"Found Alpine.js search components: {alpine_components}")
        
        # Look for the specific form ID
        main_form_pattern = r'<form[^>]*id="prescription-search-form"[^>]*>.*?</form>'
        main_form = re.findall(main_form_pattern, content, re.DOTALL)
        if main_form:
            print(f"\nMain prescription search form found:")
            print("-" * 50)
            print(main_form[0][:500] + "..." if len(main_form[0]) > 500 else main_form[0])
            print("-" * 50)
            
            # Count search inputs within this form
            search_inputs_in_form = re.findall(search_input_pattern, main_form[0])
            print(f"Search inputs within main form: {len(search_inputs_in_form)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_duplicate_search()
