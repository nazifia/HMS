#!/usr/bin/env python
"""
Test script to verify the prescription search functionality
"""
import os
import sys
import django
from django.test import RequestFactory
from django.contrib.auth.models import User

# Add the project directory to the Python path
sys.path.append('c:\\Users\\dell\\Desktop\\MY_PRODUCTS\\HMS')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.views import prescription_list
from pharmacy.forms import PrescriptionSearchForm

def test_prescription_search_view():
    """Test the prescription search view with different parameters"""
    print("Testing prescription search view...")
    
    # Create a request factory
    factory = RequestFactory()
    
    # Test 1: Basic request without parameters
    print("\nTest 1: Basic request without parameters")
    request = factory.get('/pharmacy/prescriptions/')
    request.user = User.objects.create_user('testuser', 'test@example.com', 'password')
    response = prescription_list(request)
    print(f"Response status code: {response.status_code}")
    print("Basic request test completed")
    
    # Test 2: Request with search parameters
    print("\nTest 2: Request with search parameters")
    request = factory.get('/pharmacy/prescriptions/', {
        'search': 'test',
        'status': 'pending',
        'payment_status': 'unpaid'
    })
    request.user = User.objects.create_user('testuser2', 'test2@example.com', 'password')
    response = prescription_list(request)
    print(f"Response status code: {response.status_code}")
    print("Search parameters test completed")
    
    # Test 3: Test the form directly
    print("\nTest 3: Testing PrescriptionSearchForm directly")
    form_data = {
        'search': 'patient name',
        'patient_number': 'PAT001',
        'medication_name': 'paracetamol',
        'status': 'pending',
        'payment_status': 'paid',
        'date_from': '2023-01-01',
        'date_to': '2023-12-31'
    }
    form = PrescriptionSearchForm(data=form_data)
    if form.is_valid():
        print("Form is valid")
        print(f"Cleaned data: {form.cleaned_data}")
    else:
        print("Form is invalid")
        print(f"Errors: {form.errors}")
    
    print("\nAll tests completed successfully!")

if __name__ == '__main__':
    test_prescription_search_view()