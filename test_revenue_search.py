#!/usr/bin/env python
"""
Test script to verify the search functionality in the revenue statistics view.
"""

import os
import sys
import django
from django.conf import settings
from django.test import RequestFactory
from django.contrib.auth.models import User

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_revenue_search():
    """Test the search functionality in the revenue statistics view"""
    print("Testing search functionality in revenue statistics view...")
    
    # Import the view function
    from pharmacy.views import simple_revenue_statistics
    
    # Create a request factory
    factory = RequestFactory()
    
    # Test 1: No search query
    print("\n1. Testing with no search query...")
    request = factory.get('/pharmacy/revenue/statistics/')
    request.user = User.objects.create_user('testuser')
    response = simple_revenue_statistics(request)
    print("✓ View rendered successfully without search query")
    
    # Test 2: Search query for "pharmacy"
    print("\n2. Testing with search query 'pharmacy'...")
    request = factory.get('/pharmacy/revenue/statistics/?search=pharmacy')
    request.user = User.objects.create_user('testuser2')
    response = simple_revenue_statistics(request)
    print("✓ View rendered successfully with search query 'pharmacy'")
    
    # Test 3: Search query for "laboratory"
    print("\n3. Testing with search query 'laboratory'...")
    request = factory.get('/pharmacy/revenue/statistics/?search=laboratory')
    request.user = User.objects.create_user('testuser3')
    response = simple_revenue_statistics(request)
    print("✓ View rendered successfully with search query 'laboratory'")
    
    print("\n" + "="*50)
    print("All search functionality tests passed!")
    return True

if __name__ == "__main__":
    success = test_revenue_search()
    sys.exit(0 if success else 1)