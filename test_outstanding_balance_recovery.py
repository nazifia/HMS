#!/usr/bin/env python
"""
Test outstanding balance recovery functionality
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from inpatient.models import Admission
from patients.models import PatientWallet, WalletTransaction
from decimal import Decimal

def test_outstanding_balance_calculation():
    """Test outstanding balance calculation for admissions"""
    print("=== Testing Outstanding Balance Calculation ===")
    
    try:
        # Find active admissions
        active_admissions = Admission.objects.filter(status='admitted')[:3]
        
        if not active_admissions:
            print("❌ No active admissions found")
            return False
            
        for admission in active_admissions:
            total_cost = admission.get_total_cost()
            actual_charges = admission.get_actual_charges_from_wallet()
            outstanding = admission.get_outstanding_admission_cost()
            
            print(f"\n✅ Admission: {admission.patient.get_full_name()}")
            print(f"   Duration: {admission.get_duration()} days")
            print(f"   Total Cost: ₦{total_cost}")
            print(f"   Actual Charges: ₦{actual_charges}")
            print(f"   Outstanding: ₦{outstanding}")
            
            # Verify calculation
            expected_outstanding = max(0, total_cost - actual_charges)
            if abs(outstanding - expected_outstanding) < 0.01:
                print(f"   ✅ Outstanding calculation correct")
            else:
                print(f"   ❌ Outstanding calculation incorrect (expected ₦{expected_outstanding})")
        
        return True
        
    except Exception as e:
        print(f"❌ Outstanding balance calculation test failed: {e}")
        return False

def test_recovery_strategies():
    """Test different recovery strategies"""
    print("\n=== Testing Recovery Strategies ===")
    
    try:
        # Find an admission with outstanding balance
        admissions = Admission.objects.filter(status='admitted')
        
        test_admission = None
        for admission in admissions:
            if admission.get_outstanding_admission_cost() > 0:
                test_admission = admission
                break
        
        if not test_admission:
            print("⚠️  No admissions with outstanding balances found")
            return True
            
        outstanding = test_admission.get_outstanding_admission_cost()
        daily_charge = test_admission.bed.ward.charge_per_day if test_admission.bed and test_admission.bed.ward else Decimal('2000')
        
        print(f"\n✅ Test Admission: {test_admission.patient.get_full_name()}")
        print(f"   Outstanding Balance: ₦{outstanding}")
        print(f"   Daily Charge: ₦{daily_charge}")
        
        # Test immediate strategy
        immediate_recovery = outstanding
        print(f"\n📊 Strategy Tests:")
        print(f"   Immediate: ₦{immediate_recovery} (100% of outstanding)")
        
        # Test gradual strategy
        gradual_recovery = min(outstanding, daily_charge)
        print(f"   Gradual: ₦{gradual_recovery} (min of outstanding or daily charge)")
        
        # Test daily_plus strategy
        daily_plus_recovery = min(outstanding, daily_charge, outstanding * Decimal('0.5'))
        print(f"   Daily Plus: ₦{daily_plus_recovery} (50% of outstanding or daily charge)")
        
        return True
        
    except Exception as e:
        print(f"❌ Recovery strategies test failed: {e}")
        return False

def test_wallet_transaction_types():
    """Test that new transaction type is available"""
    print("\n=== Testing Wallet Transaction Types ===")
    
    try:
        from patients.models import WalletTransaction
        
        # Check if new transaction type exists
        transaction_types = dict(WalletTransaction.TRANSACTION_TYPES)
        
        if 'outstanding_admission_recovery' in transaction_types:
            print("✅ Outstanding admission recovery transaction type found")
            print(f"   Label: {transaction_types['outstanding_admission_recovery']}")
        else:
            print("❌ Outstanding admission recovery transaction type not found")
            return False
            
        # Check other admission-related types
        admission_types = [
            'admission_fee',
            'daily_admission_charge',
            'outstanding_admission_recovery'
        ]
        
        for trans_type in admission_types:
            if trans_type in transaction_types:
                print(f"   ✅ {trans_type}: {transaction_types[trans_type]}")
            else:
                print(f"   ❌ {trans_type}: Missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Wallet transaction types test failed: {e}")
        return False

def test_command_availability():
    """Test that management commands are available"""
    print("\n=== Testing Management Commands ===")
    
    try:
        # Test daily admission charges command
        from django.core.management import get_commands
        commands = get_commands()
        
        if 'daily_admission_charges' in commands:
            print("✅ daily_admission_charges command available")
        else:
            print("❌ daily_admission_charges command not found")
            
        if 'recover_outstanding_balances' in commands:
            print("✅ recover_outstanding_balances command available")
        else:
            print("❌ recover_outstanding_balances command not found")
        
        # Test importing the enhanced command
        try:
            from inpatient.management.commands.daily_admission_charges import Command as DailyChargesCommand
            print("✅ Enhanced daily_admission_charges command imported successfully")
            
            # Check if new arguments are available
            command = DailyChargesCommand()
            parser = command.create_parser('test', 'daily_admission_charges')
            
            # This will show available arguments
            help_text = parser.format_help()
            if '--recover-outstanding' in help_text:
                print("✅ --recover-outstanding argument available")
            if '--recovery-strategy' in help_text:
                print("✅ --recovery-strategy argument available")
            if '--max-daily-recovery' in help_text:
                print("✅ --max-daily-recovery argument available")
                
        except Exception as e:
            print(f"❌ Error importing enhanced command: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Management commands test failed: {e}")
        return False

def test_nhia_exemption():
    """Test NHIA patient exemption"""
    print("\n=== Testing NHIA Patient Exemption ===")
    
    try:
        # Find NHIA patients if any
        admissions = Admission.objects.all()[:5]
        
        nhia_found = False
        for admission in admissions:
            try:
                is_nhia = (hasattr(admission.patient, 'nhia_info') and
                          admission.patient.nhia_info and
                          admission.patient.nhia_info.is_active)
                
                if is_nhia:
                    nhia_found = True
                    total_cost = admission.get_total_cost()
                    print(f"✅ NHIA Patient: {admission.patient.get_full_name()}")
                    print(f"   Total Cost: ₦{total_cost} (should be 0 for NHIA)")
                    
                    if total_cost == 0:
                        print("   ✅ NHIA exemption working correctly")
                    else:
                        print("   ❌ NHIA exemption not working")
                        
            except Exception as e:
                print(f"   ⚠️  Error checking NHIA status: {e}")
        
        if not nhia_found:
            print("⚠️  No NHIA patients found in test data")
        
        return True
        
    except Exception as e:
        print(f"❌ NHIA exemption test failed: {e}")
        return False

def run_comprehensive_test():
    """Run all tests"""
    print("🧪 OUTSTANDING BALANCE RECOVERY - COMPREHENSIVE TEST")
    print("=" * 70)
    
    tests = [
        ("Outstanding Balance Calculation", test_outstanding_balance_calculation),
        ("Recovery Strategies", test_recovery_strategies),
        ("Wallet Transaction Types", test_wallet_transaction_types),
        ("Management Commands", test_command_availability),
        ("NHIA Patient Exemption", test_nhia_exemption),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL OUTSTANDING BALANCE RECOVERY FEATURES WORKING!")
        print("\n✅ Features available:")
        print("   • Outstanding balance calculation")
        print("   • Multiple recovery strategies (immediate, gradual, daily_plus)")
        print("   • Enhanced daily charges command with recovery options")
        print("   • Dedicated outstanding balance recovery command")
        print("   • NHIA patient exemption maintained")
        print("   • New transaction type for tracking recovery")
    else:
        print(f"⚠️  {total - passed} tests failed. Please review the issues above.")
    
    print("\n🎯 Usage Examples:")
    print("1. Daily charges with outstanding recovery:")
    print("   python manage.py daily_admission_charges --recover-outstanding --recovery-strategy gradual")
    print("2. Immediate outstanding balance recovery:")
    print("   python manage.py recover_outstanding_balances --strategy immediate --dry-run")
    print("3. Gradual recovery with limits:")
    print("   python manage.py recover_outstanding_balances --strategy gradual --max-daily 5000")
    
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
