#!/usr/bin/env python
"""
Direct test of purchase_detail view to check for updated_by error
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from pharmacy.models import Purchase, Supplier
from pharmacy.views import purchase_detail
from datetime import date

def test_purchase_detail_view():
    """Test the purchase_detail view directly"""
    User = get_user_model()
    
    # Get or create test user
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.create_superuser('testadmin', 'admin@test.com', 'admin123')
    
    # Get or create supplier
    supplier = Supplier.objects.first()
    if not supplier:
        supplier = Supplier.objects.create(
            name='Test Supplier',
            email='test@example.com',
            phone_number='1234567890',
            address='Test Address',
            city='Test City',
            state='Test State',
            country='Test Country'
        )
    
    # Get or create purchase
    purchase = Purchase.objects.filter(invoice_number='TEST-001').first()
    if not purchase:
        purchase = Purchase.objects.create(
            supplier=supplier,
            purchase_date=date.today(),
            invoice_number='TEST-001',
            total_amount=1000.00,
            created_by=user
        )
    
    # Create mock request
    factory = RequestFactory()
    request = factory.get(f'/pharmacy/purchases/{purchase.id}/')
    request.user = user
    request.META = {}
    
    try:
        # Call the view
        response = purchase_detail(request, purchase.id)
        print(f"✅ purchase_detail view executed successfully!")
        print(f"Response status: {response.status_code if hasattr(response, 'status_code') else 'N/A'}")
        
        # Check context
        if hasattr(response, 'context_data'):
            context = response.context_data
            if 'purchase' in context:
                purchase_obj = context['purchase']
                print(f"Purchase in context: {purchase_obj.invoice_number}")
                
                # Test if we can access the fields
                try:
                    _ = purchase_obj.created_by
                    _ = purchase_obj.current_approver
                    _ = purchase_obj.approval_updated_at
                    print("✅ All required fields are accessible")
                except AttributeError as e:
                    print(f"❌ AttributeError accessing fields: {e}")
                    return False
        
        return True
        
    except AttributeError as e:
        if "'Purchase' object has no attribute 'updated_by'" in str(e):
            print(f"❌ Found the updated_by AttributeError: {e}")
            # Find the exact line by checking the traceback
            import traceback
            tb = traceback.format_exc()
            print("\nFull traceback:")
            print(tb)
        else:
            print(f"❌ Different AttributeError: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_purchase_detail_view()
    if success:
        print("\n✅ Test passed - No updated_by AttributeError!")
    else:
        print("\n❌ Test failed - updated_by AttributeError still exists!")
    sys.exit(0 if success else 1)
