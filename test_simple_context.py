#!/usr/bin/env python3
"""
Simple test to verify patient context clearing functionality works.
This tests the backend view directly without complex Django test setup.
"""

import os
import sys
import django
from django.conf import settings

# Add the project directory to the Python path
sys.path.insert(0, 'c:/Users/dell/Desktop/MY_PRODUCTS/HMS')

# Configure Django settings
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='test-key-for-testing-only',
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'patients',
        ],
        MIDDLEWARE=[
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ],
        USE_TZ=True,
    )

django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from patients.views import clear_patient_context

def test_clear_patient_context():
    """Test the clear_patient_context view functionality"""
    print("Testing patient context clearing functionality...")

    # Create a request factory
    factory = RequestFactory()

    # Create a POST request
    request = factory.post('/patients/clear-context/')

    # Add session middleware
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()

    # Set some patient context in the session
    request.session['current_patient_id'] = 123
    request.session['current_patient_last_accessed'] = 1234567890.0
    request.session.save()

    print(f"Session before clearing: {dict(request.session)}")

    # Call the clear_patient_context view
    response = clear_patient_context(request)

    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.content.decode()}")

    # Check if session was cleared
    print(f"Session after clearing: {dict(request.session)}")

    # Verify the results
    if response.status_code == 200:
        response_data = response.json()
        if response_data.get('success') and 'current_patient_id' not in request.session:
            print("✅ SUCCESS: Patient context cleared successfully!")
            return True
        else:
            print("❌ FAILED: Patient context was not cleared properly")
            return False
    else:
        print(f"❌ FAILED: Unexpected response status {response.status_code}")
        return False

def test_invalid_method():
    """Test that GET requests are rejected"""
    print("\nTesting invalid request method...")

    factory = RequestFactory()
    request = factory.get('/patients/clear-context/')

    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()

    response = clear_patient_context(request)

    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.content.decode()}")

    if response.status_code == 400:
        response_data = response.json()
        if not response_data.get('success') and response_data.get('error') == 'Invalid request method':
            print("✅ SUCCESS: Invalid method properly rejected!")
            return True

    print("❌ FAILED: Invalid method not properly rejected")
    return False

if __name__ == '__main__':
    print("=" * 60)
    print("PATIENT CONTEXT CLEARING FUNCTIONALITY TEST")
    print("=" * 60)

    success_count = 0
    total_tests = 2

    # Test 1: Clear patient context
    if test_clear_patient_context():
        success_count += 1

    # Test 2: Invalid method rejection
    if test_invalid_method():
        success_count += 1

    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {success_count}/{total_tests} tests passed")

    if success_count == total_tests:
        print("🎉 ALL TESTS PASSED! Patient context clearing functionality is working correctly.")
        print("\nThe fix for 'Error clearing patient context. Please try again.' has been successfully implemented.")
    else:
        print("❌ Some tests failed. Please check the implementation.")

    print("=" * 60)