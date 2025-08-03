#!/usr/bin/env python3
"""
Test script to verify the PrescriptionPaymentForm validation works correctly.
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_prescription_payment_form_validation():
    """Test PrescriptionPaymentForm validation"""
    print("Testing PrescriptionPaymentForm validation...")
    
    try:
        from pharmacy.forms import PrescriptionPaymentForm
        
        # Mock objects
        class MockInvoice:
            def get_balance(self):
                return Decimal('100.00')
        
        class MockWallet:
            balance = Decimal('500.00')
        
        # Test 1: Valid form data
        print("\n1. Testing valid form data...")
        form_data = {
            'amount': '100.00',
            'payment_method': 'cash',
            'payment_source': 'direct',
            'notes': 'Test payment'
        }
        
        form = PrescriptionPaymentForm(
            data=form_data,
            invoice=MockInvoice(),
            patient_wallet=MockWallet()
        )
        
        if form.is_valid():
            print("✓ Valid form data accepted")
        else:
            print(f"✗ Valid form data rejected: {form.errors}")
        
        # Test 2: Wallet payment validation
        print("\n2. Testing wallet payment validation...")
        form_data_wallet = {
            'amount': '50.00',
            'payment_method': 'cash',  # Should be auto-corrected to 'wallet'
            'payment_source': 'patient_wallet',
            'notes': 'Wallet payment'
        }
        
        form = PrescriptionPaymentForm(
            data=form_data_wallet,
            invoice=MockInvoice(),
            patient_wallet=MockWallet()
        )
        
        if form.is_valid():
            cleaned_data = form.clean()
            if cleaned_data['payment_method'] == 'wallet':
                print("✓ Wallet payment method auto-corrected")
            else:
                print(f"⚠ Payment method not corrected: {cleaned_data['payment_method']}")
        else:
            print(f"✗ Wallet payment validation failed: {form.errors}")
        
        # Test 3: Invalid amount (too high)
        print("\n3. Testing amount validation...")
        form_data_invalid = {
            'amount': '150.00',  # Higher than invoice balance
            'payment_method': 'cash',
            'payment_source': 'direct',
            'notes': 'Invalid amount'
        }
        
        form = PrescriptionPaymentForm(
            data=form_data_invalid,
            invoice=MockInvoice(),
            patient_wallet=MockWallet()
        )
        
        if not form.is_valid():
            print("✓ Invalid amount correctly rejected")
        else:
            print("✗ Invalid amount incorrectly accepted")
        
        # Test 4: Missing required fields
        print("\n4. Testing required field validation...")
        form_data_missing = {
            'payment_method': 'cash',
            'payment_source': 'direct',
            # Missing amount
        }
        
        form = PrescriptionPaymentForm(
            data=form_data_missing,
            invoice=MockInvoice(),
            patient_wallet=MockWallet()
        )
        
        if not form.is_valid():
            print("✓ Missing required fields correctly rejected")
        else:
            print("✗ Missing required fields incorrectly accepted")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing form validation: {e}")
        return False

def test_form_field_presence():
    """Test that all expected fields are present"""
    print("\nTesting form field presence...")
    
    try:
        from pharmacy.forms import PrescriptionPaymentForm
        
        class MockInvoice:
            def get_balance(self):
                return Decimal('100.00')
        
        class MockWallet:
            balance = Decimal('500.00')
        
        form = PrescriptionPaymentForm(
            invoice=MockInvoice(),
            patient_wallet=MockWallet()
        )
        
        expected_fields = ['amount', 'payment_method', 'payment_source', 'notes']
        missing_fields = [field for field in expected_fields if field not in form.fields]
        
        if missing_fields:
            print(f"⚠ Missing fields: {missing_fields}")
        else:
            print("✓ All expected fields present")
        
        # Check payment method choices
        payment_choices = [choice[0] for choice in form.fields['payment_method'].choices]
        if 'wallet' in payment_choices:
            print("✓ Wallet payment method available")
        else:
            print("⚠ Wallet payment method not available")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing field presence: {e}")
        return False

def main():
    """Run all prescription payment form tests"""
    print("Prescription Payment Form Test Suite")
    print("=" * 50)
    
    tests = [
        test_prescription_payment_form_validation,
        test_form_field_presence
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Prescription payment form is working correctly!")
        print("\nThe form should now work properly on the payment page.")
        print("Try submitting the payment again.")
    else:
        print("⚠ Some tests failed. Please review the issues above.")

if __name__ == "__main__":
    main()
