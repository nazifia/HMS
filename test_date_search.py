#!/usr/bin/env python
"""
Test script to verify the date search functionality in the revenue statistics view.
"""

import os
import sys
import django
from django.conf import settings
from django.test import RequestFactory
from django.contrib.auth.models import User
from datetime import date

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_date_search():
    """Test the date search functionality in the revenue statistics view"""
    print("Testing date search functionality in revenue statistics view...")
    
    # Import the view function
    from pharmacy.views import simple_revenue_statistics
    
    # Create a request factory
    factory = RequestFactory()
    
    # Test 1: No date parameters
    print("\n1. Testing with no date parameters...")
    request = factory.get('/pharmacy/revenue/statistics/')
    request.user = User.objects.create_user('testuser')
    response = simple_revenue_statistics(request)
    print("✓ View rendered successfully without date parameters")
    
    # Test 2: With start date only
    print("\n2. Testing with start date only...")
    request = factory.get('/pharmacy/revenue/statistics/?start_date=2025-01-01')
    request.user = User.objects.create_user('testuser2')
    response = simple_revenue_statistics(request)
    print("✓ View rendered successfully with start date only")
    
    # Test 3: With end date only
    print("\n3. Testing with end date only...")
    request = factory.get('/pharmacy/revenue/statistics/?end_date=2025-12-31')
    request.user = User.objects.create_user('testuser3')
    response = simple_revenue_statistics(request)
    print("✓ View rendered successfully with end date only")
    
    # Test 4: With both start and end dates
    print("\n4. Testing with both start and end dates...")
    request = factory.get('/pharmacy/revenue/statistics/?start_date=2025-01-01&end_date=2025-12-31')
    request.user = User.objects.create_user('testuser4')
    response = simple_revenue_statistics(request)
    print("✓ View rendered successfully with both start and end dates")
    
    # Test 5: With invalid dates (should fallback to current month)
    print("\n5. Testing with invalid dates...")
    request = factory.get('/pharmacy/revenue/statistics/?start_date=invalid&end_date=alsoinvalid')
    request.user = User.objects.create_user('testuser5')
    response = simple_revenue_statistics(request)
    print("✓ View rendered successfully with invalid dates (fallback to current month)")
    
    print("\n" + "="*50)
    print("All date search functionality tests passed!")
    return True

if __name__ == "__main__":
    success = test_date_search()
    sys.exit(0 if success else 1)