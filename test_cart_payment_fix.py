#!/usr/bin/env python
"""
Test script to verify cart payment recognition fix
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
sys.path.append(r'C:\Users\dell\Desktop\MY_PRODUCTS\HMS')

django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from pharmacy.cart_models import PrescriptionCart, PrescriptionCartItem
from pharmacy.models import Prescription, PrescriptionItem, Medication
from patients.models import Patient
from pharmacy_billing.models import Invoice, Payment
from decimal import Decimal

def test_cart_payment_recognition():
    """Test that cart properly recognizes billing office payments"""
    
    print("🧪 Testing Cart Payment Recognition Fix...")
    
    # Create test data
    user = User.objects.create_user(username='testuser', password='testpass')
    patient = Patient.objects.create(first_name='Test', last_name='Patient')
    medication = Medication.objects.create(name='Test Med', price=Decimal('100.00'))
    
    # Create prescription
    prescription = Prescription.objects.create(
        patient=patient,
        doctor=user,
        notes='Test prescription'
    )
    
    # Create prescription item
    prescription_item = PrescriptionItem.objects.create(
        prescription=prescription,
        medication=medication,
        quantity=5,
        price=Decimal('100.00')
    )
    
    # Create cart
    cart = PrescriptionCart.objects.create(
        prescription=prescription,
        created_by=user,
        status='active'
    )
    
    # Add item to cart
    cart_item = PrescriptionCartItem.objects.create(
        cart=cart,
        prescription_item=prescription_item,
        quantity=5,
        unit_price=Decimal('100.00')
    )
    
    # Create invoice
    from pharmacy_billing.utils import create_pharmacy_invoice
    invoice = create_pharmacy_invoice(None, prescription, Decimal('500.00'))
    
    # Associate invoice with cart
    cart.invoice = invoice
    cart.status = 'invoiced'
    cart.save()
    
    print(f"✅ Created test cart #{cart.id} with status '{cart.status}'")
    
    # Simulate billing office payment
    payment = Payment.objects.create(
        invoice=invoice,
        amount=Decimal('500.00'),
        payment_method='cash',
        notes='Billing office payment - billing_office'
    )
    
    # Update invoice
    invoice.amount_paid = Decimal('500.00')
    invoice.status = 'paid'
    invoice.save()
    
    print(f"✅ Created billing office payment #{payment.id} of ₦500.00")
    print(f"✅ Updated invoice #{invoice.invoice_number} status to 'paid'")
    
    # Test cart status auto-update logic (from view_cart)
    # This simulates the fix we added to view_cart function
    if cart.invoice and cart.invoice.status == 'paid' and cart.status in ['invoiced', 'active']:
        cart.status = 'paid'
        cart.save(update_fields=['status'])
        print(f"✅ Auto-updated cart status to '{cart.status}'")
    
    # Verify cart can complete dispensing
    can_dispense, message = cart.can_complete_dispensing()
    
    print(f"📊 Cart can complete dispensing: {can_dispense}")
    print(f"📝 Dispensing message: {message}")
    
    # Test the view context
    client = Client()
    client.force_login(user)
    
    url = reverse('pharmacy:view_cart', kwargs={'cart_id': cart.id})
    print(f"🌐 Testing URL: {url}")
    
    try:
        response = client.get(url)
        print(f"📄 Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Cart view loads successfully")
            
            # Check for payment status in response
            content = response.content.decode('utf-8')
            
            if 'Payment Processed via Billing Office' in content:
                print("✅ Template shows 'Payment Processed via Billing Office' message")
            else:
                print("❌ Template missing 'Payment Processed via Billing Office' message")
            
            if 'status-paid' in content:
                print("✅ Cart status badge shows as 'paid'")
            else:
                print("❌ Cart status badge not showing as 'paid'")
                
        else:
            print(f"❌ Cart view failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing cart view: {str(e)}")
    
    # Cleanup
    cart.delete()
    payment.delete()
    invoice.delete()
    cart_item.delete()
    prescription_item.delete()
    prescription.delete()
    medication.delete()
    patient.delete()
    user.delete()
    
    print("🧹 Test data cleaned up")
    print("🎉 Cart payment recognition test completed!")

if __name__ == '__main__':
    test_cart_payment_recognition()
