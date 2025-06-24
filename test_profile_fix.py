#!/usr/bin/env python3
"""
Test script to verify profile access is working correctly
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import CustomUserProfile

User = get_user_model()

def test_profile_access():
    """Test that user.profile works correctly"""
    print("Testing profile access...")
    
    try:
        # Get the first user
        user = User.objects.first()
        if not user:
            print("No users found in database")
            return False
            
        print(f"Testing with user: {user}")
        
        # Test profile access
        profile = user.profile
        print(f"Profile access successful: {profile}")
        
        # Test role access
        if hasattr(profile, 'role'):
            print(f"Profile role: {profile.role}")
        else:
            print("Profile has no role attribute")
            
        # Test department access
        if hasattr(profile, 'department'):
            print(f"Profile department: {profile.department}")
        else:
            print("Profile has no department attribute")
            
        print("✅ Profile access test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Profile access test FAILED: {e}")
        return False

def test_template_context():
    """Test template context that would be used in templates"""
    print("\nTesting template context...")
    
    try:
        user = User.objects.first()
        if not user:
            print("No users found in database")
            return False
            
        # Simulate template context access
        context = {
            'user': user
        }
        
        # Test the kind of access that templates do
        profile_role = context['user'].profile.role if context['user'].profile else None
        print(f"Template-style role access: {profile_role}")
        
        print("✅ Template context test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Template context test FAILED: {e}")
        return False

if __name__ == "__main__":
    print("Running profile access tests...\n")
    
    test1_passed = test_profile_access()
    test2_passed = test_template_context()
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests PASSED! Profile access is working correctly.")
    else:
        print("\n💥 Some tests FAILED! Profile access needs more work.")