#!/usr/bin/env python
"""
Test URL reverse for activity monitoring
"""
import os
import sys

# Simple test without Django logging
import logging
logging.disable(logging.CRITICAL)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

import django

try:
    from django.urls import reverse
    django.setup()
    
    # Test URL reverse
    url = reverse('accounts:live_monitor')
    print(f"✅ URL reverse successful: {url}")
    
    # Test activity monitor view import
    from accounts import activity_views
    print(f"✅ activity_views imported successfully")
    
    print("🎯 Activity monitoring URLs are working correctly!")
    
except Exception as e:
    print(f"❌ Error testing URLs: {e}")
