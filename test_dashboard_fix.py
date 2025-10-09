#!/usr/bin/env python
"""
Test script to verify the dashboard page loads without NoReverseMatch error
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client, TestCase
from django.urls import reverse
from accounts.models import CustomUser

def test_dashboard_access():
    """Test that the dashboard page loads without errors"""
    client = Client()
    
    # Create a test user if it doesn't exist
    if not CustomUser.objects.filter(username='testuser').exists():
        CustomUser.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
    
    # Login the user
    client.login(username='testuser', password='testpass123')
    
    try:
        # Try to access the dashboard
        response = client.get('/dashboard/')
        
        if response.status_code == 200:
            print("SUCCESS: Dashboard page loads successfully!")
            print(f"Status Code: {response.status_code}")
            return True
        else:
            print(f"FAILED: Dashboard page failed with status code: {response.status_code}")
            if hasattr(response, 'context') and response.context:
                print(f"Context keys: {list(response.context.keys())}")
            return False
            
    except Exception as e:
        print(f"ERROR: Error accessing dashboard: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing dashboard access after NoReverseMatch fix...")
    success = test_dashboard_access()
    
    if success:
        print("\nSUCCESS: All tests passed! The NoReverseMatch error has been fixed.")
        sys.exit(0)
    else:
        print("\nFAILED: Tests failed. There may still be issues.")
        sys.exit(1)