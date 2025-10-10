#!/usr/bin/env python
"""
Debug script to investigate OSError [Errno 22] on POST login requests
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()

def test_database_operations():
    """Test database operations during authentication"""
    print("=== Testing Database Operations ===")
    
    try:
        # Test user lookup
        user_count = User.objects.count()
        print(f"+ Found {user_count} users in database")
        
        # Test user lookup by phone number
        if user_count > 0:
            first_user = User.objects.first()
            print(f"+ First user: {first_user.username} ({first_user.phone_number})")
            
            # Test checking password
            if first_user.check_password('test'):
                print("+ Password check works")
            else:
                print("- Password check failed (expected for unknown password)")
        
        return True
        
    except Exception as e:
        print(f"- Database operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_authentication_backends_directly():
    """Test authentication backends directly"""
    print("\n=== Testing Authentication Backends Directly ===")
    
    from django.conf import settings
    from django.contrib.auth import authenticate
    
    # Test with dummy data
    print("Testing authentication with dummy data...")
    
    try:
        # Test each backend individually
        for backend_path in settings.AUTHENTICATION_BACKENDS:
            print(f"Testing backend: {backend_path}")
            
            try:
                module_path, class_name = backend_path.rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])
                backend_class = getattr(module, class_name)
                backend = backend_class()
                
                # Test authenticate method with dummy data
                result = backend.authenticate(username='test123456789', password='test123')
                print(f"  + Backend authenticate method returned: {result}")
                
            except Exception as e:
                print(f"  - Backend authentication failed: {e}")
                # Don't return False immediately, continue testing other backends
        
        return True
        
    except Exception as e:
        print(f"- Backend testing failed: {e}")
        return False

def test_post_request_simulation():
    """Test POST request to login page"""
    print("\n=== Testing POST Request Simulation ===")
    
    try:
        client = Client()
        
        # Test POST request with dummy data
        print("Testing POST with dummy login data...")
        
        from accounts.forms import CustomLoginForm
        
        # Create form data
        post_data = {
            'username': 'test123456789',  # dummy phone number
            'password': 'test123'
        }
        
        response = client.post('/accounts/login/', data=post_data)
        print(f"POST response status: {response.status_code}")
        
        if response.status_code == 200:
            print("+ POST request completed without error")
            # Check if form has errors
            if 'form' in response.context:
                form = response.context['form']
                if form.errors:
                    print(f"Form errors: {form.errors}")
        else:
            print(f"- POST request failed with status: {response.status_code}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"- POST request failed with exception: {e}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def test_file_operations():
    """Test if there are any file operation issues"""
    print("\n=== Testing File Operations ===")
    
    try:
        # Test temporary file operations
        import tempfile
        import os
        
        # Create a temp file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b'test')
            temp_path = tmp.name
        
        # Try to read it
        with open(temp_path, 'rb') as f:
            data = f.read()
        
        # Clean up
        os.unlink(temp_path)
        
        print("+ File operations work properly")
        return True
        
    except Exception as e:
        print(f"- File operation failed: {e}")
        return False

def main():
    """Main diagnostic function"""
    print("=== Debugging OSError [Errno 22] on POST Login Requests ===")
    
    tests = [
        test_file_operations,
        test_database_operations,
        test_authentication_backends_directly,
        test_post_request_simulation,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    print("=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("+ All tests passed - issue may be browser-specific")
    else:
        print("- Some tests failed - identified potential causes")

if __name__ == "__main__":
    main()
