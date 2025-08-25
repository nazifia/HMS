#!/usr/bin/env python
"""
Test script to verify the revenue service functionality
"""

import os
import sys
import django
from datetime import date

# Add the project directory to the Python path
sys.path.append('c:\\Users\\dell\\Desktop\\MY_PRODUCTS\\HMS')

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

# Setup Django
django.setup()

from pharmacy.revenue_service import RevenueAggregationService, MonthFilterHelper

def test_revenue_service():
    """Test the revenue service functionality"""
    print("Testing Revenue Service...")
    
    # Get current month date range
    start_date, end_date = MonthFilterHelper.get_current_month()
    print(f"Date range: {start_date} to {end_date}")
    
    # Initialize revenue aggregation service
    revenue_service = RevenueAggregationService(start_date, end_date)
    
    # Test comprehensive revenue data
    print("\nFetching comprehensive revenue data...")
    comprehensive_data = revenue_service.get_comprehensive_revenue()
    
    print(f"Total Revenue: ₦{comprehensive_data['total_revenue']}")
    print(f"Pharmacy Revenue: ₦{comprehensive_data['pharmacy_revenue']['total_revenue']}")
    print(f"Laboratory Revenue: ₦{comprehensive_data['laboratory_revenue']['total_revenue']}")
    print(f"Consultation Revenue: ₦{comprehensive_data['consultation_revenue']['total_revenue']}")
    print(f"Theatre Revenue: ₦{comprehensive_data['theatre_revenue']['total_revenue']}")
    print(f"Admission Revenue: ₦{comprehensive_data['admission_revenue']['total_revenue']}")
    print(f"General Revenue: ₦{comprehensive_data['general_revenue']['total_revenue']}")
    print(f"Wallet Revenue: ₦{comprehensive_data['wallet_revenue']['total_revenue']}")
    
    # Test monthly trends
    print("\nFetching monthly trends...")
    monthly_trends = revenue_service.get_monthly_trends(3)  # Last 3 months
    
    for trend in monthly_trends:
        print(f"{trend['month']}: ₦{trend['total_revenue']}")

if __name__ == "__main__":
    test_revenue_service()