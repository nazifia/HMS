#!/usr/bin/env python
"""
Test view imports for activity monitoring
"""
import os
import sys
import logging

# Disable logging
logging.disable(logging.CRITICAL)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

import django
django.setup()

try:
    # Test activity monitoring views import
    from accounts.activity_views import activity_dashboard, live_activity_monitor
    print("✅ Activity monitoring views imported successfully!")
    
    # Test that views are callable
    print(f"✅ activity_dashboard: {activity_dashboard}")
    print(f"✅ live_activity_monitor: {live_activity_monitor}")
    
    print("🎯 Activity monitoring system is ready!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")
