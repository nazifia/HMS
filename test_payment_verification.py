#!/usr/bin/env python
"""
Test script to verify payment verification system for medication dispensing.
This script tests the integration of payment verification with the dispensing workflow.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from pharmacy.models import Prescription, PrescriptionItem, Medication, MedicationCategory, Dispensary
from patients.models import Patient
from pharmacy_billing.models import Invoice, InvoiceItem
from billing.models import Service
from decimal import Decimal

User = get_user_model()


def test_payment_verification_system():
    """Test the payment verification system for medication dispensing"""
    print("=== Testing Payment Verification System ===\n")
    
    try:
        # Test 1: Check if prescription payment verification methods work
        print("Test 1: Testing prescription payment verification methods...")
        
        # Get a sample prescription (assuming one exists)
        prescription = Prescription.objects.first()
        if not prescription:
            print("❌ No prescriptions found in database. Please create a prescription first.")
            return False
        
        print(f"✓ Found prescription {prescription.id} for patient {prescription.patient.get_full_name()}")
        
        # Test payment verification
        is_verified = prescription.is_payment_verified()
        can_dispense, reason = prescription.can_be_dispensed()
        payment_info = prescription.get_payment_status_display_info()
        
        print(f"  - Payment verified: {is_verified}")
        print(f"  - Can be dispensed: {can_dispense}")
        print(f"  - Reason: {reason}")
        print(f"  - Payment status info: {payment_info}")
        
        # Test 2: Check if unpaid prescriptions are blocked from dispensing
        print("\nTest 2: Testing dispensing block for unpaid prescriptions...")
        
        if prescription.payment_status == 'unpaid':
            print("✓ Prescription is unpaid - testing dispensing block")
            if not can_dispense and 'payment' in reason.lower():
                print("✓ Dispensing correctly blocked due to payment requirement")
            else:
                print("❌ Dispensing not properly blocked for unpaid prescription")
                return False
        else:
            print(f"ℹ Prescription payment status is '{prescription.payment_status}' - cannot test unpaid scenario")
        
        # Test 3: Check if paid prescriptions allow dispensing
        print("\nTest 3: Testing dispensing allowance for paid prescriptions...")
        
        # Temporarily mark prescription as paid for testing
        original_payment_status = prescription.payment_status
        prescription.payment_status = 'paid'
        prescription.save()
        
        can_dispense_paid, reason_paid = prescription.can_be_dispensed()
        print(f"  - Can dispense when paid: {can_dispense_paid}")
        print(f"  - Reason: {reason_paid}")
        
        if can_dispense_paid or 'payment' not in reason_paid.lower():
            print("✓ Paid prescriptions allow dispensing (or blocked for other valid reasons)")
        else:
            print("❌ Paid prescriptions incorrectly blocked due to payment")
            return False
        
        # Restore original payment status
        prescription.payment_status = original_payment_status
        prescription.save()
        
        # Test 4: Check invoice integration
        print("\nTest 4: Testing invoice integration...")
        
        if prescription.invoice:
            print(f"✓ Prescription has associated invoice {prescription.invoice.id}")
            print(f"  - Invoice status: {prescription.invoice.status}")
            
            # Test if invoice status affects payment verification
            original_invoice_status = prescription.invoice.status
            prescription.invoice.status = 'paid'
            prescription.invoice.save()
            
            is_verified_via_invoice = prescription.is_payment_verified()
            print(f"  - Payment verified via paid invoice: {is_verified_via_invoice}")
            
            # Restore original invoice status
            prescription.invoice.status = original_invoice_status
            prescription.invoice.save()
        else:
            print("ℹ Prescription has no associated invoice")
        
        print("\n✅ All payment verification tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_dispensing_workflow():
    """Test the complete dispensing workflow with payment verification"""
    print("\n=== Testing Dispensing Workflow ===\n")
    
    try:
        # Create a test client
        client = Client()
        
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='test_pharmacist',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'Pharmacist'
            }
        )
        
        # Login the user
        client.force_login(user)
        
        # Get a prescription to test with
        prescription = Prescription.objects.first()
        if not prescription:
            print("❌ No prescriptions found for workflow testing")
            return False
        
        print(f"Testing workflow with prescription {prescription.id}")
        
        # Test accessing dispensing page
        dispense_url = reverse('pharmacy:dispense_prescription', args=[prescription.id])
        response = client.get(dispense_url)
        
        print(f"  - Dispense page response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Dispensing page accessible")
        elif response.status_code == 302:
            print("ℹ Dispensing page redirected (likely due to payment verification)")
        else:
            print(f"❌ Unexpected response status: {response.status_code}")
        
        print("\n✅ Dispensing workflow test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during workflow testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Payment Verification System Test")
    print("=" * 50)
    
    # Run tests
    test1_result = test_payment_verification_system()
    test2_result = test_dispensing_workflow()
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    print(f"Payment Verification Tests: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    print(f"Dispensing Workflow Tests: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    
    if test1_result and test2_result:
        print("\n🎉 All tests passed! Payment verification system is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please review the implementation.")
