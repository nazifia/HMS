#!/usr/bin/env python
"""
Simple test to verify purchase detail view
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Purchase
from django.test import Client
from django.contrib.auth import login
from accounts.models import CustomUser

def test_purchase_detail():
    print("Testing purchase detail view...")
    
    # Get existing purchase
    purchase = Purchase.objects.first()
    if not purchase:
        print("No purchase found in database")
        return False
    
    # Get user
    user = CustomUser.objects.first()
    if not user:
        print("No user found in database")
        return False
    
    # Create test client and login
    client = Client()
    client.force_login(user)
    
    # Import and test view
    try:
        # Call view via client
        response = client.get(f'/pharmacy/purchases/{purchase.id}/')
        
        # Check if response is successful
        if response.status_code != 200:
            print(f"✗ HTTP {response.status_code}: {response.reason_phrase}")
            return False
            
        context = response.context
        
        # Verify context has required attributes
        purchase_obj = context['purchase']
        print(f"✓ Purchase: {purchase_obj.invoice_number}")
        
        # Check if history data is attached
        if hasattr(purchase_obj, 'approval_status_history'):
            print(f"✓ Approval history: {len(purchase_obj.approval_status_history)} entries")
            for i, hist in enumerate(purchase_obj.approval_status_history, 1):
                print(f"  {i}. {hist.get('old_status', 'Created')} → {hist.get('new_status')} at {hist.get('changed_at')}")
        
        if hasattr(purchase_obj, 'payment_history'):
            print(f"✓ Payment history: {len(purchase_obj.payment_history)} entries")
            for i, payment in enumerate(purchase_obj.payment_history, 1):
                print(f"  {i}. ₦{payment.get('amount')} via {payment.get('payment_method')} at {payment.get('payment_date')}")
        
        print(f"✓ Total paid: ₦{purchase_obj.total_paid}")
        print(f"✓ Amount due: ₦{purchase_obj.amount_due}")
        
        print("\n✓ Purchase detail view test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_purchase_detail()
    sys.exit(0 if success else 1)
