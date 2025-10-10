#!/usr/bin/env python
"""
Test script to verify the login OSError fix.
This script tests that the authentication system works without OSError [Errno 22].
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.contrib.auth import authenticate
from accounts.models import CustomUser
import logging

# Get logger
logger = logging.getLogger(__name__)

def test_authentication():
    """Test authentication without OSError"""
    print("=" * 60)
    print("Testing Authentication Fix for OSError [Errno 22]")
    print("=" * 60)
    
    try:
        # Test 1: Check if logging is configured correctly
        print("\n1. Testing logging configuration...")
        logger.info("Test log message with Unicode: ✓ ✗ ★ ♥")
        print("   ✓ Logging works correctly")
        
        # Test 2: Check if users exist
        print("\n2. Checking for test users...")
        user_count = CustomUser.objects.count()
        print(f"   Found {user_count} users in database")
        
        if user_count == 0:
            print("   ⚠ No users found. Please create a user first.")
            return False
        
        # Test 3: Try authentication with a dummy request
        print("\n3. Testing authentication backend...")
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/accounts/login/')
        
        # Get first user for testing
        test_user = CustomUser.objects.first()
        print(f"   Testing with user: {test_user.phone_number}")
        
        # Try to authenticate (will fail with wrong password, but shouldn't cause OSError)
        result = authenticate(request, username=test_user.phone_number, password='wrong_password')
        print(f"   Authentication result (expected None): {result}")
        
        if result is None:
            print("   ✓ Authentication backend works without OSError")
        
        # Test 4: Check log file creation on Windows
        print("\n4. Checking log file...")
        from django.conf import settings
        if hasattr(settings, 'LOG_FILE') and settings.LOG_FILE:
            if os.path.exists(settings.LOG_FILE):
                print(f"   ✓ Log file created: {settings.LOG_FILE}")
                # Read last few lines
                with open(settings.LOG_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        print(f"   Last log entry: {lines[-1].strip()}")
            else:
                print(f"   ⚠ Log file not found: {settings.LOG_FILE}")
        else:
            print("   ℹ Log file not configured")
        
        print("\n" + "=" * 60)
        print("✓ All tests passed! The OSError fix is working.")
        print("=" * 60)
        return True
        
    except OSError as e:
        print(f"\n✗ OSError occurred: {e}")
        print("The fix did not work. Please check the configuration.")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_authentication()
    sys.exit(0 if success else 1)

