#!/usr/bin/env python
"""
Test script to verify URL resolution for the pharmacy app.
This script tests if the URL patterns are correctly defined and can be resolved.
"""

import os
import sys
import django
from django.conf import settings
from django.urls import reverse, NoReverseMatch

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_url_resolution():
    """Test URL resolution for pharmacy app URLs"""
    print("Testing URL resolution for pharmacy app...")
    
    # Test URLs that should exist
    test_urls = [
        'pharmacy:dashboard',
        'pharmacy:procurement_dashboard',
        'pharmacy:simple_revenue_statistics',
        'pharmacy:inventory',
        'pharmacy:supplier_list',
    ]
    
    resolved_urls = []
    failed_urls = []
    
    for url_name in test_urls:
        try:
            url = reverse(url_name)
            resolved_urls.append((url_name, url))
            print(f"✓ {url_name} -> {url}")
        except NoReverseMatch as e:
            failed_urls.append((url_name, str(e)))
            print(f"✗ {url_name} -> FAILED: {e}")
    
    print("\n" + "="*50)
    print(f"Successfully resolved: {len(resolved_urls)}")
    print(f"Failed to resolve: {len(failed_urls)}")
    
    if failed_urls:
        print("\nFailed URLs:")
        for url_name, error in failed_urls:
            print(f"  - {url_name}: {error}")
        return False
    else:
        print("\nAll URLs resolved successfully!")
        return True

if __name__ == "__main__":
    success = test_url_resolution()
    sys.exit(0 if success else 1)