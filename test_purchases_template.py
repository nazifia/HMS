#!/usr/bin/env python
"""
Test script to verify the purchases template fixes
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import RequestFactory, TestCase
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from pharmacy.models import Purchase, Supplier
from django.core.paginator import Paginator

User = get_user_model()

def test_template_rendering():
    """Test that the template renders without errors"""
    print("Testing purchases template rendering...")
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/pharmacy/purchases/')
    
    # Get some sample purchases if they exist
    purchases = Purchase.objects.select_related('supplier', 'created_by').order_by('-purchase_date')
    
    # Create pagination
    paginator = Paginator(purchases, 10)
    page_obj = paginator.get_page(1)
    
    context = {
        'purchases': page_obj,
        'page_obj': page_obj,
        'search_query': '',
        'status': '',
        'payment_status': '',
        'title': 'Manage Purchases',
        'page_title': 'Manage Purchases',
        'active_nav': 'pharmacy',
        'request': request,
    }
    
    try:
        rendered = render_to_string('pharmacy/manage_purchases.html', context)
        print("✓ Template renders successfully")
        print(f"✓ Rendered length: {len(rendered)} characters")
        
        # Check for key elements
        if 'Manage Purchases' in rendered:
            print("✓ Title is present")
        if 'Search & Filter' in rendered:
            print("✓ Search section is present")
        if 'Purchase List' in rendered:
            print("✓ Table header is present")
        if 'pagination' in rendered.lower() or 'page-link' in rendered:
            print("✓ Pagination controls are present")
            
        return True
    except Exception as e:
        print(f"✗ Template rendering failed: {e}")
        return False

if __name__ == '__main__':
    print("Starting purchases template test...")
    success = test_template_rendering()
    print("\nTest completed:", "PASSED" if success else "FAILED")
