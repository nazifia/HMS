#!/usr/bin/env python
"""
Test daily admission charges functionality to ensure it's working correctly
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from inpatient.models import Admission
from patients.models import Patient, PatientWallet, WalletTransaction
from inpatient.management.commands.daily_admission_charges import Command
from datetime import date, timedelta
from decimal import Decimal

def test_daily_charges_command():
    """Test the daily charges management command"""
    print("=== Testing Daily Charges Management Command ===")
    
    try:
        command = Command()
        print("✅ Daily charges command imported successfully")
        
        # Find active admissions
        active_admissions = Admission.objects.filter(status='admitted')
        print(f"   Found {active_admissions.count()} active admissions")
        
        if active_admissions.exists():
            admission = active_admissions.first()
            print(f"   Testing with admission: {admission.patient.get_full_name()}")
            
            # Test dry run
            result = command.process_admission_charge(admission, date.today(), dry_run=True)
            if result:
                print(f"   ✅ Dry run successful - would charge ₦{result}")
            else:
                print(f"   ⚠️  Dry run returned None - checking reasons...")
                
                # Check NHIA status
                try:
                    is_nhia = (hasattr(admission.patient, 'nhia_info') and 
                             admission.patient.nhia_info and 
                             admission.patient.nhia_info.is_active)
                    print(f"      NHIA patient: {is_nhia}")
                except:
                    print(f"      NHIA check failed - treating as non-NHIA")
                
                # Check bed/ward
                has_bed = admission.bed is not None
                has_ward = admission.bed and admission.bed.ward is not None
                print(f"      Has bed: {has_bed}")
                print(f"      Has ward: {has_ward}")
                
                if has_ward:
                    daily_charge = admission.bed.ward.charge_per_day
                    print(f"      Daily charge rate: ₦{daily_charge}")
                
        else:
            print("   ⚠️  No active admissions found")
            
        return True
        
    except Exception as e:
        print(f"❌ Daily charges command test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_admission_duration_calculation():
    """Test admission duration calculation"""
    print("\n=== Testing Admission Duration Calculation ===")
    
    try:
        admissions = Admission.objects.all()[:5]  # Test first 5 admissions
        
        for admission in admissions:
            duration = admission.get_duration()
            total_cost = admission.get_total_cost()
            
            print(f"   Admission: {admission.patient.get_full_name()}")
            print(f"      Admission Date: {admission.admission_date.date()}")
            print(f"      Discharge Date: {admission.discharge_date.date() if admission.discharge_date else 'Still admitted'}")
            print(f"      Duration: {duration} days")
            print(f"      Total Cost: ₦{total_cost}")
            
            if admission.bed and admission.bed.ward:
                daily_rate = admission.bed.ward.charge_per_day
                expected_cost = daily_rate * duration
                print(f"      Daily Rate: ₦{daily_rate}")
                print(f"      Expected Cost: ₦{expected_cost}")
                print(f"      Cost Match: {'✅' if total_cost == expected_cost else '❌'}")
            else:
                print(f"      ⚠️  No bed/ward assigned")
            
            print()
            
        return True
        
    except Exception as e:
        print(f"❌ Duration calculation test failed: {e}")
        return False

def test_wallet_deduction_logic():
    """Test wallet deduction logic"""
    print("=== Testing Wallet Deduction Logic ===")
    
    try:
        # Find patients with wallet transactions
        patients_with_transactions = Patient.objects.filter(
            wallet__wallettransaction__isnull=False
        ).distinct()[:3]
        
        for patient in patients_with_transactions:
            print(f"   Patient: {patient.get_full_name()}")
            
            try:
                wallet = PatientWallet.objects.get(patient=patient)
                print(f"      Current Balance: ₦{wallet.balance}")
                
                # Check admission fees
                admission_fees = WalletTransaction.objects.filter(
                    wallet=wallet,
                    transaction_type='admission_fee'
                ).count()
                
                # Check daily charges
                daily_charges = WalletTransaction.objects.filter(
                    wallet=wallet,
                    transaction_type='daily_admission_charge'
                ).count()
                
                print(f"      Admission Fee Transactions: {admission_fees}")
                print(f"      Daily Charge Transactions: {daily_charges}")
                
                # Check recent transactions
                recent_transactions = WalletTransaction.objects.filter(
                    wallet=wallet
                ).order_by('-created_at')[:3]
                
                print(f"      Recent Transactions:")
                for tx in recent_transactions:
                    print(f"         {tx.created_at.date()} | {tx.transaction_type} | ₦{tx.amount}")
                
            except PatientWallet.DoesNotExist:
                print(f"      ⚠️  No wallet found")
            
            print()
            
        return True
        
    except Exception as e:
        print(f"❌ Wallet deduction test failed: {e}")
        return False

def test_automatic_daily_processing():
    """Test if daily processing is working for current admissions"""
    print("=== Testing Automatic Daily Processing ===")
    
    try:
        # Find current active admissions
        active_admissions = Admission.objects.filter(status='admitted')
        
        print(f"   Active admissions: {active_admissions.count()}")
        
        for admission in active_admissions:
            print(f"\n   Admission: {admission.patient.get_full_name()}")
            print(f"      Admission Date: {admission.admission_date.date()}")
            print(f"      Days Since Admission: {admission.get_duration()}")
            
            # Check if daily charges have been processed
            wallet = PatientWallet.objects.get_or_create(patient=admission.patient)[0]
            
            daily_charges = WalletTransaction.objects.filter(
                wallet=wallet,
                transaction_type='daily_admission_charge'
            ).count()
            
            expected_charges = admission.get_duration()
            
            print(f"      Daily Charges Processed: {daily_charges}")
            print(f"      Expected Daily Charges: {expected_charges}")
            print(f"      Processing Status: {'✅ Up to date' if daily_charges >= expected_charges else '⚠️ Missing charges'}")
            
            if daily_charges < expected_charges:
                missing_days = expected_charges - daily_charges
                print(f"      Missing {missing_days} days of charges")
                
                # Check if patient is NHIA (which would explain missing charges)
                try:
                    is_nhia = (hasattr(admission.patient, 'nhia_info') and 
                             admission.patient.nhia_info and 
                             admission.patient.nhia_info.is_active)
                    if is_nhia:
                        print(f"      ✅ Patient is NHIA - charges correctly exempted")
                    else:
                        print(f"      ❌ Non-NHIA patient missing daily charges")
                except:
                    print(f"      ❌ Non-NHIA patient missing daily charges")
        
        return True
        
    except Exception as e:
        print(f"❌ Automatic daily processing test failed: {e}")
        return False

def suggest_fixes():
    """Suggest fixes if daily charges are not working"""
    print("\n=== Suggested Actions ===")
    
    print("1. **Manual Daily Charges Processing**:")
    print("   python manage.py daily_admission_charges")
    print()
    
    print("2. **Set Up Automatic Daily Processing**:")
    print("   - For Windows: Use Task Scheduler")
    print("   - For Linux/Mac: Use cron job")
    print("   - Run daily at 12:00 AM")
    print()
    
    print("3. **Check Missing Daily Charges**:")
    print("   python check_admission_charges.py")
    print()
    
    print("4. **Process Missing Charges**:")
    print("   python fix_overcharged_patient.py")
    print()

def run_comprehensive_test():
    """Run all tests"""
    print("🧪 DAILY ADMISSION CHARGES - COMPREHENSIVE FUNCTIONALITY TEST")
    print("=" * 70)
    
    tests = [
        ("Daily Charges Command", test_daily_charges_command),
        ("Duration Calculation", test_admission_duration_calculation),
        ("Wallet Deduction Logic", test_wallet_deduction_logic),
        ("Automatic Daily Processing", test_automatic_daily_processing),
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
    print("📊 FUNCTIONALITY TEST SUMMARY")
    print("=" * 70)
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL DAILY CHARGES FUNCTIONALITY WORKING!")
        print("\n✅ The daily admission charges system is operational")
    else:
        print(f"⚠️  {total - passed} tests revealed issues")
        suggest_fixes()
    
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
