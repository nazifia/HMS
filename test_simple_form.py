#!/usr/bin/env python
"""
Create a simple test to isolate the add_class issue
"""

import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(__file__)
sys.path.insert(0, project_dir)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

import django
django.setup()

from django.test import Client
from django.http import HttpResponse
from django.template import Template, Context
from consultations.forms import ReferralForm

def test_template_rendering():
    """Test template rendering with add_class filter"""
    print("Testing template rendering with add_class filter...")
    
    try:
        # Create a simple template that uses add_class
        template_string = """
        {% load core_form_tags %}
        <form>
            {{ form.referral_type|add_class:"form-control" }}
            {{ form.reason|add_class:"form-control" }}
        </form>
        """
        
        template = Template(template_string)
        form = ReferralForm()
        context = Context({'form': form})
        
        # This should trigger the error if it exists
        result = template.render(context)
        print("✓ Template renders without error")
        print(f"Result length: {len(result)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Template rendering failed: {e}")
        return False

def test_url_access():
    """Test accessing the actual URL that's failing"""
    print("\nTesting URL access...")
    
    try:
        client = Client()
        response = client.get('/consultations/referrals/create/42/')
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ URL accessed successfully")
            return True
        elif response.status_code == 302:
            print("✓ URL redirected (likely auth required)")
            return True
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        if "'str' object has no attribute 'as_widget'" in str(e):
            print(f"✗ Found the AttributeError: {e}")
            return False
        else:
            print(f"Different error: {e}")
            return True

def main():
    """Run tests"""
    print("Testing for AttributeError source...\n")
    
    tests = [
        test_template_rendering,
        test_url_access,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
    
    print("\nTest complete!")

if __name__ == "__main__":
    main()