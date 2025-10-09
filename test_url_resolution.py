#!/usr/bin/env python
"""
Test script to verify the admission_net_impact URL resolution issue is fixed
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.urls import reverse, resolve
from django.test import SimpleTestCase

def test_url_resolution():
    """Test that URLs resolve correctly"""
    print("Testing URL resolution after NoReverseMatch fix...")
    
    # Test 1: Check if the admission_net_impact URL pattern exists
    try:
        # This should fail because it needs a pk parameter
        url = reverse('inpatient:admission_net_impact')
        print("FAILED: URL reverse should have failed without pk parameter")
        return False
    except Exception as e:
        print(f"SUCCESS: URL reverse correctly failed without pk parameter: {str(e)}")
    
    # Test 2: Check if the admission_net_impact URL pattern works with pk
    try:
        url = reverse('inpatient:admission_net_impact', kwargs={'pk': 1})
        print(f"SUCCESS: URL reverse works with pk parameter: {url}")
    except Exception as e:
        print(f"FAILED: URL reverse failed with pk parameter: {str(e)}")
        return False
    
    # Test 3: Check if the dashboard URL resolves
    try:
        url = reverse('dashboard:dashboard')
        print(f"SUCCESS: Dashboard URL resolves: {url}")
    except Exception as e:
        print(f"FAILED: Dashboard URL resolution failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_url_resolution()
    
    if success:
        print("\nSUCCESS: All URL resolution tests passed! The NoReverseMatch error has been fixed.")
        sys.exit(0)
    else:
        print("\nFAILED: URL resolution tests failed.")
        sys.exit(1)