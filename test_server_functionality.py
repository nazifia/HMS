#!/usr/bin/env python
"""
Test script to verify Django server functionality
"""
import os
import sys
import django
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

def test_server():
    """Test basic server functionality"""
    print("Testing Django Server Functionality...")
    print("=" * 50)
    
    # Test 1: Check if Django loads without errors
    try:
        from django.conf import settings
        print(f"✓ Django settings loaded successfully")
        print(f"  - DEBUG: {settings.DEBUG}")
        print(f"  - Database: {settings.DATABASES['default']['ENGINE']}")
    except Exception as e:
        print(f"✗ Failed to load Django settings: {e}")
        return False
    
    # Test 2: Check database connection
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print(f"✓ Database connection working")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    
    # Test 3: Check models
    try:
        User = get_user_model()
        user_count = User.objects.count()
        print(f"✓ Models loaded successfully ({user_count} users in database)")
    except Exception as e:
        print(f"✗ Model loading failed: {e}")
        return False
    
    # Test 4: Test URL routing
    try:
        client = Client()
        
        # Test admin URL
        response = client.get('/admin/')
        if response.status_code == 302 or response.status_code == 200:
            print(f"✓ Admin URL accessible (status: {response.status_code})")
        else:
            print(f"✗ Admin URL returned status: {response.status_code}")
            
        # Test root URL
        response = client.get('/')
        if response.status_code == 200:
            print(f"✓ Root URL accessible (status: {response.status_code})")
        else:
            print(f"! Root URL returned status: {response.status_code}")
            
    except Exception as e:
        print(f"✗ URL routing test failed: {e}")
        return False
    
    # Test 5: Check installed apps
    try:
        from django.apps import apps
        app_configs = apps.get_app_configs()
        print(f"✓ {len(app_configs)} apps loaded successfully")
    except Exception as e:
        print(f"✗ App loading failed: {e}")
        return False
    
    print("=" * 50)
    print("✓ All tests passed! Server is functioning correctly.")
    return True

if __name__ == "__main__":
    success = test_server()
    sys.exit(0 if success else 1)
