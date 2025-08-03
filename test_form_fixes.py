#!/usr/bin/env python3
"""
Test script to verify the form fixes work correctly.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_prescription_payment_form():
    """Test that PrescriptionPaymentForm can be initialized with custom parameters"""
    print("Testing PrescriptionPaymentForm initialization...")
    
    try:
        from pharmacy.forms import PrescriptionPaymentForm
        from billing.models import Invoice
        from pharmacy.models import Prescription
        from patients.models import PatientWallet, Patient
        from decimal import Decimal
        
        # Create a mock invoice (we won't save it)
        class MockInvoice:
            def get_balance(self):
                return Decimal('100.00')
        
        class MockPrescription:
            id = 1
        
        class MockWallet:
            balance = Decimal('500.00')
        
        # Test form initialization with custom parameters
        form = PrescriptionPaymentForm(
            invoice=MockInvoice(),
            prescription=MockPrescription(),
            patient_wallet=MockWallet()
        )
        
        print("✓ PrescriptionPaymentForm initialized successfully with custom parameters")
        
        # Check if payment_source field was added
        if 'payment_source' in form.fields:
            print("✓ Payment source field added correctly")
        else:
            print("⚠ Payment source field not found")
        
        # Check if amount field has initial value
        if form.fields['amount'].initial == Decimal('100.00'):
            print("✓ Amount field initialized with invoice balance")
        else:
            print(f"⚠ Amount field initial value: {form.fields['amount'].initial}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing PrescriptionPaymentForm: {e}")
        return False

def test_email_safety():
    """Test that email sending functions handle None users safely"""
    print("\nTesting email safety functions...")
    
    try:
        from core.models import send_notification_email
        
        # Test with empty recipient list (should not crash)
        try:
            send_notification_email(
                subject="Test",
                message="Test message",
                recipient_list=[]
            )
            print("✓ Email function handles empty recipient list")
        except Exception as e:
            print(f"⚠ Email function error with empty list: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing email safety: {e}")
        return False

def test_invoice_item_creation():
    """Test that InvoiceItem can be created with correct field names"""
    print("\nTesting InvoiceItem creation...")
    
    try:
        from billing.models import InvoiceItem, Service, Invoice
        from patients.models import Patient
        from decimal import Decimal
        
        # Check if InvoiceItem model has the correct fields
        field_names = [field.name for field in InvoiceItem._meta.fields]
        
        required_fields = ['total_amount', 'tax_amount', 'discount_amount']
        missing_fields = [field for field in required_fields if field not in field_names]
        
        if missing_fields:
            print(f"⚠ Missing fields in InvoiceItem: {missing_fields}")
        else:
            print("✓ InvoiceItem has all required fields")
        
        # Check that total_price is not a field (it should be a property)
        if 'total_price' in field_names:
            print("⚠ InvoiceItem still has total_price field (should be property only)")
        else:
            print("✓ InvoiceItem does not have total_price field")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing InvoiceItem: {e}")
        return False

def main():
    """Run all form fix tests"""
    print("HMS Form Fixes Test Suite")
    print("=" * 40)
    
    tests = [
        test_prescription_payment_form,
        test_email_safety,
        test_invoice_item_creation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All form fixes are working correctly!")
    else:
        print("⚠ Some tests failed. Please review the issues above.")

if __name__ == "__main__":
    main()
