#!/usr/bin/env python
"""
Test script to verify purchase detail view fixes
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import RequestFactory
from accounts.models import CustomUser
from pharmacy.models import Purchase, Supplier, Medication, PurchaseItem, Dispensary
from pharmacy.views import purchase_detail
from datetime import date, timedelta

def test_purchase_detail():
    print("Testing purchase detail view...")
    
    # Create test data
    user = CustomUser.objects.first()
    if not user:
        user = CustomUser.objects.create_user(username='testuser', password='testpass', email='test@example.com')
    
    supplier, created = Supplier.objects.get_or_create(
        name='Test Supplier',
        defaults={
            'email': 'test@example.com',
            'phone_number': '1234567890',
            'is_active': True
        }
    )
    
    dispensary, created = Dispensary.objects.get_or_create(
        name='Test Dispensary',
        defaults={
            'is_active': True
        }
    )
    
    # Create test purchase
    purchase, created = Purchase.objects.get_or_create(
        invoice_number='TEST-001',
        defaults={
            'supplier': supplier,
            'purchase_date': date.today(),
            'total_amount': 1000.00,
            'approval_status': 'approved',
            'payment_status': 'paid',
            'dispensary': dispensary,
            'created_by': user,
            'current_approver': user,
            'approval_updated_at': date.today(),
            'notes': 'Test purchase'
        }
    )
    
    medication, created = Medication.objects.get_or_create(
        name='Test Medication',
        defaults={
            'generic_name': 'Test Generic',
            'description': 'Test description',
            'is_active': True
        }
    )
    
    # Create purchase item
    item, created = PurchaseItem.objects.get_or_create(
        purchase=purchase,
        medication=medication,
        defaults={
            'quantity': 10,
            'unit_price': 100.00,
            'total_price': 1000.00,
            'batch_number': 'BATCH001',
            'expiry_date': date.today() + timedelta(days=365)
        }
    )
    
    # Create mock request
    factory = RequestFactory()
    request = factory.get(f'/pharmacy/purchases/{purchase.id}/')
    request.user = user
    
    # Test the view
    try:
        response = purchase_detail(request, purchase.id)
        context = response.context_data
        
        print(f"✓ Purchase: {context['purchase'].invoice_number}")
        print(f"✓ Purchase items: {len(context['purchase_items'])}")
        print(f"✓ Approval history: {len(context['purchase'].approval_status_history)} entries")
        print(f"✓ Payment history: {len(context['purchase'].payment_history)} entries")
        print(f"✓ Total paid: ₦{context['purchase'].total_paid}")
        print(f"✓ Amount due: ₦{context['purchase'].amount_due}")
        
        # Print approval history
        print("\n--- Approval History ---")
        for i, history in enumerate(context['purchase'].approval_status_history, 1):
            print(f"{i}. {history['changed_at']}: {history['old_status']} → {history['new_status']} by {history['changed_by'] if history['changed_by'] else 'System'}")
        
        # Print payment history
        print("\n--- Payment History ---")
        for i, payment in enumerate(context['purchase'].payment_history, 1):
            print(f"{i}. {payment['payment_date']}: ₦{payment['amount']} via {payment['payment_method']} by {payment['processed_by'] if payment['processed_by'] else 'Pending'}")
        
        print("\n✓ Purchase detail view test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Error testing purchase detail view: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_purchase_detail()
    sys.exit(0 if success else 1)
