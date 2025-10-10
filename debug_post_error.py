#!/usr/bin/env python
"""
Debug script to investigate the OSError [Errno 22] Invalid argument on POST requests
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from accounts.models import CustomUser

User = get_user_model()

def test_post_request():
    """Test POST request to login page"""
    print("=== Testing POST Request to Login Page ===")
    
    try:
        client = Client()
        
        # Test POST request with empty data first
        print("Testing POST with empty data...")
        response = client.post('/accounts/login/', {})
        print(f"+ POST with empty data - Status: {response.status_code}")
        
        # Test POST request with form data
        print("Testing POST with form data...")
        form_data = {
            'username': 'invalid_phone',
            'password': 'invalid_pass',
        }
        response = client.post('/accounts/login/', form_data)
        print(f"+ POST with form data - Status: {response.status_code}")
        
        # Try to find or create a test user to test valid login
        try:
            test_user = User.objects.get(phone_number='1234567890')
            print(f"Found existing test user: {test_user.username}")
        except User.DoesNotExist:
            print("Test user not found, creating one...")
            try:
                test_user = User.objects.create_user(
                    phone_number='1234567890',
                    username='testuser',
                    password='testpass123',
                    email='test@example.com'
                )
                print(f"+ Test user created: {test_user.username}")
            except Exception as e:
                print(f"- Failed to create test user: {e}")
                return False
        
        # Test with valid credentials
        print("Testing POST with valid credentials...")
        valid_data = {
            'username': '1234567890',
            'password': 'testpass123',
        }
        response = client.post('/accounts/login/', valid_data)
        print(f"+ POST with valid data - Status: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"- Exception during POST test: {e}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def test_authentication_backends_post():
    """Test authentication backends with POST-like scenarios"""
    print("\n=== Testing Authentication Backends ===")
    
    from accounts.backends import PhoneNumberBackend, AdminBackend
    
    try:
        phone_backend = PhoneNumberBackend()
        admin_backend = AdminBackend()
        
        print("+ Backend instances created successfully")
        
        # Test phone backend with various inputs
        test_cases = [
            ('1234567890', 'testpass'),
            ('', ''),
            ('invalid', 'invalid'),
        ]
        
        for username, password in test_cases:
            try:
                print(f"Testing phone backend with: {username}/{password}")
                result = phone_backend.authenticate(None, username, password)
                print(f"  Result: {result}")
            except Exception as e:
                print(f"  Exception: {e}")
                import traceback
                traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"- Exception testing backends: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_form_processing():
    """Test form processing that might cause the error"""
    print("\n=== Testing Form Processing ===")
    
    try:
        from accounts.forms import CustomLoginForm
        
        # Test form creation with various data
        test_data_sets = [
            {},
            {'username': '', 'password': ''},
            {'username': '1234567890', 'password': 'testpass'},
            {'username': 'invalid_phone_#$%^&*', 'password': 'test'},
        ]
        
        for data in test_data_sets:
            try:
                form = CustomLoginForm(data=data)
                print(f"Form with data {data} - is_valid: {form.is_valid()}")
                
                if form.is_bound:
                    try:
                        cleaned = form.clean()
                        print(f"  Cleaned data: {cleaned}")
                    except Exception as e:
                        print(f"  Form clean exception: {e}")
                        
            except Exception as e:
                print(f"Form creation exception with data {data}: {e}")
                import traceback
                traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"- Exception in form processing: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main diagnostic function"""
    print("=== POST Request Error Diagnostic ===")
    
    tests = [
        test_form_processing,
        test_authentication_backends_post,
        test_post_request,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("\n=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("+ All tests passed - POST requests should work!")
    else:
        print("- Some tests failed - POST requests have issues")

if __name__ == "__main__":
    main()
