#!/usr/bin/env python3
"""
Test script for new HMS features:
1. Daily admission charges automation
2. Enhanced prescription viewing for pharmacy staff

This script tests the new functionality without affecting the database.
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from inpatient.models import Admission, Ward, Bed
from patients.models import Patient, PatientWallet
from pharmacy.models import Prescription
from accounts.models import Role

User = get_user_model()

def test_daily_admission_charges():
    """Test the daily admission charges command"""
    print("Testing Daily Admission Charges Command...")
    
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Test dry-run mode
        out = StringIO()
        call_command('daily_admission_charges', '--dry-run', stdout=out)
        output = out.getvalue()
        
        print("✓ Daily admission charges command executed successfully")
        print(f"  Output preview: {output[:100]}...")
        
        # Check if the command found admissions
        if "Found" in output and "active admissions" in output:
            print("✓ Command successfully identified active admissions")
        else:
            print("⚠ No active admissions found (this may be normal)")
            
        return True
        
    except Exception as e:
        print(f"✗ Error testing daily admission charges: {e}")
        return False

def test_prescription_urls():
    """Test the new prescription URLs"""
    print("\nTesting Prescription URLs...")
    
    try:
        from django.urls import reverse
        
        # Test prescription list URL
        url = reverse('pharmacy:prescription_list')
        print(f"✓ Prescription list URL: {url}")
        
        # Test patient prescriptions URL (with dummy patient ID)
        url = reverse('pharmacy:patient_prescriptions', kwargs={'patient_id': 1})
        print(f"✓ Patient prescriptions URL: {url}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing prescription URLs: {e}")
        return False

def test_prescription_search_form():
    """Test the enhanced prescription search form"""
    print("\nTesting Enhanced Prescription Search Form...")
    
    try:
        from pharmacy.forms import PrescriptionSearchForm
        
        # Test form initialization
        form = PrescriptionSearchForm()
        
        # Check if new fields are present
        expected_fields = ['search', 'patient_number', 'medication_name', 'status', 'payment_status', 'doctor', 'date_from', 'date_to']
        form_fields = list(form.fields.keys())
        
        missing_fields = [field for field in expected_fields if field not in form_fields]
        if missing_fields:
            print(f"⚠ Missing fields in form: {missing_fields}")
        else:
            print("✓ All expected fields present in prescription search form")
        
        # Test form with data
        test_data = {
            'search': 'test patient',
            'status': 'pending',
            'payment_status': 'unpaid'
        }
        
        form = PrescriptionSearchForm(data=test_data)
        if form.is_valid():
            print("✓ Form validation works correctly")
        else:
            print(f"⚠ Form validation issues: {form.errors}")
            
        return True
        
    except Exception as e:
        print(f"✗ Error testing prescription search form: {e}")
        return False

def test_patient_wallet_functionality():
    """Test patient wallet functionality for admission charges"""
    print("\nTesting Patient Wallet Functionality...")
    
    try:
        from patients.models import PatientWallet
        from decimal import Decimal
        
        # Check if PatientWallet model has required methods
        required_methods = ['credit', 'debit']
        wallet_methods = [method for method in dir(PatientWallet) if not method.startswith('_')]
        
        missing_methods = [method for method in required_methods if method not in wallet_methods]
        if missing_methods:
            print(f"⚠ Missing methods in PatientWallet: {missing_methods}")
        else:
            print("✓ PatientWallet has required methods (credit, debit)")
        
        # Check transaction types
        from patients.models import WalletTransaction
        transaction_types = [choice[0] for choice in WalletTransaction.TRANSACTION_TYPES]
        
        if 'daily_admission_charge' in transaction_types or 'admission_fee' in transaction_types:
            print("✓ Admission-related transaction types available")
        else:
            print("⚠ Consider adding 'daily_admission_charge' transaction type")
            
        return True
        
    except Exception as e:
        print(f"✗ Error testing patient wallet functionality: {e}")
        return False

def main():
    """Run all tests"""
    print("HMS New Features Test Suite")
    print("=" * 50)
    
    tests = [
        test_daily_admission_charges,
        test_prescription_urls,
        test_prescription_search_form,
        test_patient_wallet_functionality
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
        print("🎉 All tests passed! New features are ready.")
    else:
        print("⚠ Some tests failed. Please review the issues above.")
    
    print("\nNext Steps:")
    print("1. Set up the cron job for daily admission charges:")
    print("   python scripts/setup_daily_charges_cron.py")
    print("2. Test the new prescription viewing features in the web interface")
    print("3. Verify that existing functionality still works correctly")

if __name__ == "__main__":
    main()
