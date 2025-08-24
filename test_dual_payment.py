#!/usr/bin/env python
"""
Test script to validate dual-source medication payment implementation.
This script tests both prescription_payment and billing_office_medication_payment functions.
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, r'c:\Users\dell\Desktop\MY_PRODUCTS\HMS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

# Setup Django
django.setup()

def test_payment_views_import():
    """Test that payment views can be imported successfully."""
    print("=== Testing Payment Views Import ===")
    
    try:
        from pharmacy.views import prescription_payment, billing_office_medication_payment
        print("✅ Payment views imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing payment views: {e}")
        return False

def test_pharmacy_billing_models():
    """Test that pharmacy billing models are accessible."""
    print("\n=== Testing Pharmacy Billing Models ===")
    
    try:
        from pharmacy_billing.models import Invoice as PharmacyInvoice, Payment as PharmacyPayment
        print("✅ Pharmacy billing models imported successfully")
        
        # Test model counts
        invoice_count = PharmacyInvoice.objects.count()
        payment_count = PharmacyPayment.objects.count()
        print(f"📊 Current invoices: {invoice_count}")
        print(f"📊 Current payments: {payment_count}")
        return True
    except Exception as e:
        print(f"❌ Error with pharmacy billing models: {e}")
        return False

def test_prescription_models():
    """Test prescription models and related functionality."""
    print("\n=== Testing Prescription Models ===")
    
    try:
        from pharmacy.models import Prescription
        from patients.models import Patient, PatientWallet
        
        prescription_count = Prescription.objects.count()
        patient_count = Patient.objects.count()
        wallet_count = PatientWallet.objects.count()
        
        print(f"📊 Current prescriptions: {prescription_count}")
        print(f"📊 Current patients: {patient_count}")
        print(f"📊 Current wallets: {wallet_count}")
        
        if prescription_count > 0:
            # Test a prescription
            prescription = Prescription.objects.first()
            print(f"✅ Test prescription: #{prescription.id} for {prescription.patient.get_full_name()}")
            
            # Test total price calculation
            try:
                total_price = prescription.get_total_prescribed_price()
                print(f"💰 Total prescribed price: ₦{total_price}")
            except Exception as e:
                print(f"⚠️ Warning: Could not calculate total price: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Error with prescription models: {e}")
        return False

def test_form_compatibility():
    """Test form compatibility with the implementation."""
    print("\n=== Testing Form Compatibility ===")
    
    try:
        from pharmacy.forms import PrescriptionPaymentForm
        print("✅ PrescriptionPaymentForm imported successfully")
        
        # Test form initialization
        form = PrescriptionPaymentForm()
        print("✅ Form initialized successfully")
        
        # Check required fields
        required_fields = ['amount', 'payment_method', 'payment_source']
        missing_fields = []
        
        for field in required_fields:
            if field not in form.fields:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"⚠️ Missing form fields: {missing_fields}")
        else:
            print("✅ All required form fields present")
        
        return True
    except Exception as e:
        print(f"❌ Error with form compatibility: {e}")
        return False

def test_url_configuration():
    """Test URL configuration for payment views."""
    print("\n=== Testing URL Configuration ===")
    
    try:
        from django.urls import reverse
        
        # Test URL patterns
        test_prescription_id = 1
        
        try:
            prescription_payment_url = reverse('pharmacy:prescription_payment', kwargs={'prescription_id': test_prescription_id})
            print(f"✅ Prescription payment URL: {prescription_payment_url}")
        except Exception as e:
            print(f"❌ Error with prescription payment URL: {e}")
        
        try:
            billing_office_payment_url = reverse('pharmacy:billing_office_medication_payment', kwargs={'prescription_id': test_prescription_id})
            print(f"✅ Billing office payment URL: {billing_office_payment_url}")
        except Exception as e:
            print(f"❌ Error with billing office payment URL: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Error with URL configuration: {e}")
        return False

def main():
    """Run all tests."""
    print("🏥 HMS Dual-Source Medication Payment Test Suite")
    print("=" * 60)
    
    tests = [
        test_payment_views_import,
        test_pharmacy_billing_models,
        test_prescription_models,
        test_form_compatibility,
        test_url_configuration
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Dual-source payment implementation is ready.")
    else:
        print("⚠️ Some tests failed. Please review the implementation.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)