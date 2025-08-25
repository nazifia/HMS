#!/usr/bin/env python
"""
Test script to verify the defensive URL helper functions.
This script tests if the safe_reverse functions work correctly.
"""

import os
import sys
import django
from django.conf import settings

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from core.utils import safe_reverse, safe_reverse_or_default

def test_defensive_url_helpers():
    """Test the defensive URL helper functions"""
    print("Testing defensive URL helper functions...")
    
    # Test 1: safe_reverse with a valid URL
    print("\n1. Testing safe_reverse with valid URL...")
    result = safe_reverse('pharmacy:simple_revenue_statistics')
    if result:
        print(f"✓ safe_reverse('pharmacy:simple_revenue_statistics') -> {result}")
    else:
        print("✗ safe_reverse failed for valid URL")
        return False
    
    # Test 2: safe_reverse with an invalid URL
    print("\n2. Testing safe_reverse with invalid URL...")
    result = safe_reverse('pharmacy:nonexistent_url')
    if result is None:
        print("✓ safe_reverse correctly returned None for invalid URL")
    else:
        print(f"✗ safe_reverse should have returned None, but got: {result}")
        return False
    
    # Test 3: safe_reverse_or_default with a valid URL
    print("\n3. Testing safe_reverse_or_default with valid URL...")
    result = safe_reverse_or_default('pharmacy:simple_revenue_statistics', '#')
    if result and result != '#':
        print(f"✓ safe_reverse_or_default('pharmacy:simple_revenue_statistics', '#') -> {result}")
    else:
        print("✗ safe_reverse_or_default failed for valid URL")
        return False
    
    # Test 4: safe_reverse_or_default with an invalid URL
    print("\n4. Testing safe_reverse_or_default with invalid URL...")
    result = safe_reverse_or_default('pharmacy:nonexistent_url', '#')
    if result == '#':
        print("✓ safe_reverse_or_default correctly returned default for invalid URL")
    else:
        print(f"✗ safe_reverse_or_default should have returned '#', but got: {result}")
        return False
    
    print("\n" + "="*50)
    print("All defensive URL helper tests passed!")
    return True

if __name__ == "__main__":
    success = test_defensive_url_helpers()
    sys.exit(0 if success else 1)