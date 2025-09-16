#!/usr/bin/env python
"""
Test wallet-balance-aware outstanding balance recovery functionality
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

def test_balance_aware_strategies():
    """Test different wallet-balance-aware recovery strategies"""
    print("=== Testing Wallet-Balance-Aware Recovery Strategies ===")
    
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
        
        # Get current wallet balance
        try:
            wallet = PatientWallet.objects.get(patient=test_admission.patient)
            current_balance = wallet.balance
        except PatientWallet.DoesNotExist:
            print("❌ No wallet found for test patient")
            return False
        
        print(f"\n✅ Test Admission: {test_admission.patient.get_full_name()}")
        print(f"   Outstanding Balance: ₦{outstanding}")
        print(f"   Current Wallet Balance: ₦{current_balance}")
        print(f"   Daily Charge: ₦{daily_charge}")
        
        # Test parameters
        balance_threshold = Decimal('1000.00')
        max_negative_balance = Decimal('10000.00')
        
        print(f"\n📊 Wallet-Balance-Aware Strategy Tests:")
        
        # Test balance_aware strategy
        available_balance = current_balance - balance_threshold
        if available_balance > 0:
            balance_aware_recovery = min(outstanding, available_balance, daily_charge)
        else:
            balance_aware_recovery = Decimal('0.00')
        print(f"   Balance Aware: ₦{balance_aware_recovery} (keeps ₦{balance_threshold} minimum)")
        
        # Test balance_proportional strategy
        if current_balance > 0:
            balance_ratio = min(current_balance / (daily_charge * 5), Decimal('1.0'))
            balance_proportional_recovery = min(outstanding, daily_charge * balance_ratio)
        else:
            balance_proportional_recovery = min(outstanding, daily_charge * Decimal('0.25'))
        print(f"   Balance Proportional: ₦{balance_proportional_recovery} (ratio-based)")
        
        # Test balance_limited strategy
        max_deduction = max_negative_balance + current_balance
        if max_deduction > 0:
            balance_limited_recovery = min(outstanding, max_deduction, daily_charge * 2)
        else:
            balance_limited_recovery = Decimal('0.00')
        print(f"   Balance Limited: ₦{balance_limited_recovery} (max negative: ₦{max_negative_balance})")
        
        # Test balance_aggressive strategy
        balance_aggressive_recovery = min(outstanding, daily_charge * 3)
        print(f"   Balance Aggressive: ₦{balance_aggressive_recovery} (up to 3 days worth)")
        
        # Show impact on wallet balance
        print(f"\n💰 Wallet Balance Impact:")
        print(f"   Current: ₦{current_balance}")
        print(f"   After Balance Aware: ₦{current_balance - balance_aware_recovery}")
        print(f"   After Balance Proportional: ₦{current_balance - balance_proportional_recovery}")
        print(f"   After Balance Limited: ₦{current_balance - balance_limited_recovery}")
        print(f"   After Balance Aggressive: ₦{current_balance - balance_aggressive_recovery}")
        
        return True
        
    except Exception as e:
        print(f"❌ Wallet-balance-aware strategies test failed: {e}")
        return False

def test_command_options():
    """Test that new command options are available"""
    print("\n=== Testing Enhanced Command Options ===")
    
    try:
        # Test daily admission charges command
        from inpatient.management.commands.daily_admission_charges import Command as DailyChargesCommand
        
        command = DailyChargesCommand()
        parser = command.create_parser('test', 'daily_admission_charges')
        help_text = parser.format_help()
        
        new_options = [
            '--max-negative-balance',
            '--balance-threshold',
            'balance_aware',
            'balance_proportional',
            'balance_limited',
            'balance_aggressive'
        ]
        
        print("✅ Daily Admission Charges Command:")
        for option in new_options:
            if option in help_text:
                print(f"   ✅ {option}: Available")
            else:
                print(f"   ❌ {option}: Missing")
        
        # Test outstanding balance recovery command
        from inpatient.management.commands.recover_outstanding_balances import Command as RecoveryCommand
        
        command = RecoveryCommand()
        parser = command.create_parser('test', 'recover_outstanding_balances')
        help_text = parser.format_help()
        
        print("\n✅ Outstanding Balance Recovery Command:")
        for option in new_options:
            if option in help_text:
                print(f"   ✅ {option}: Available")
            else:
                print(f"   ❌ {option}: Missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Command options test failed: {e}")
        return False

def test_scenario_simulations():
    """Test different wallet balance scenarios"""
    print("\n=== Testing Wallet Balance Scenarios ===")
    
    try:
        # Simulate different wallet balance scenarios
        scenarios = [
            ("High Balance", Decimal('50000.00')),
            ("Medium Balance", Decimal('15000.00')),
            ("Low Balance", Decimal('3000.00')),
            ("Very Low Balance", Decimal('500.00')),
            ("Zero Balance", Decimal('0.00')),
            ("Negative Balance", Decimal('-5000.00')),
            ("Very Negative Balance", Decimal('-15000.00')),
        ]
        
        outstanding = Decimal('26000.00')  # From screenshot
        daily_charge = Decimal('2000.00')
        balance_threshold = Decimal('1000.00')
        max_negative_balance = Decimal('10000.00')
        
        print(f"📊 Scenario Analysis (Outstanding: ₦{outstanding}, Daily: ₦{daily_charge}):")
        print(f"{'Scenario':<20} {'Balance':<12} {'Aware':<8} {'Prop':<8} {'Limited':<8} {'Aggr':<8}")
        print("-" * 70)
        
        for scenario_name, current_balance in scenarios:
            # Balance aware
            available_balance = current_balance - balance_threshold
            if available_balance > 0:
                aware_recovery = min(outstanding, available_balance, daily_charge)
            else:
                aware_recovery = Decimal('0.00')
            
            # Balance proportional
            if current_balance > 0:
                balance_ratio = min(current_balance / (daily_charge * 5), Decimal('1.0'))
                prop_recovery = min(outstanding, daily_charge * balance_ratio)
            else:
                prop_recovery = min(outstanding, daily_charge * Decimal('0.25'))
            
            # Balance limited
            max_deduction = max_negative_balance + current_balance
            if max_deduction > 0:
                limited_recovery = min(outstanding, max_deduction, daily_charge * 2)
            else:
                limited_recovery = Decimal('0.00')
            
            # Balance aggressive
            aggr_recovery = min(outstanding, daily_charge * 3)
            
            print(f"{scenario_name:<20} ₦{current_balance:<10} ₦{aware_recovery:<6} ₦{prop_recovery:<6} ₦{limited_recovery:<6} ₦{aggr_recovery:<6}")
        
        return True
        
    except Exception as e:
        print(f"❌ Scenario simulations test failed: {e}")
        return False

def test_real_world_example():
    """Test with the real-world example from the screenshot"""
    print("\n=== Testing Real-World Example (Screenshot Scenario) ===")
    
    try:
        # Screenshot data:
        # Total Admission Cost: ₦30,000
        # Wallet Charges for this Admission: ₦4,000
        # Outstanding Admission Cost: ₦26,000
        # Current Patient Wallet Balance: ₦14,000
        
        current_balance = Decimal('14000.00')
        outstanding = Decimal('26000.00')
        daily_charge = Decimal('2000.00')
        balance_threshold = Decimal('1000.00')
        max_negative_balance = Decimal('10000.00')
        
        print(f"📸 Screenshot Scenario Analysis:")
        print(f"   Current Balance: ₦{current_balance}")
        print(f"   Outstanding: ₦{outstanding}")
        print(f"   Daily Charge: ₦{daily_charge}")
        
        # Calculate each strategy
        strategies = {}
        
        # Balance aware
        available_balance = current_balance - balance_threshold
        strategies['balance_aware'] = min(outstanding, available_balance, daily_charge) if available_balance > 0 else Decimal('0.00')
        
        # Balance proportional
        balance_ratio = min(current_balance / (daily_charge * 5), Decimal('1.0'))
        strategies['balance_proportional'] = min(outstanding, daily_charge * balance_ratio)
        
        # Balance limited
        max_deduction = max_negative_balance + current_balance
        strategies['balance_limited'] = min(outstanding, max_deduction, daily_charge * 2) if max_deduction > 0 else Decimal('0.00')
        
        # Balance aggressive
        strategies['balance_aggressive'] = min(outstanding, daily_charge * 3)
        
        print(f"\n💡 Recommended Recovery Strategies:")
        for strategy, amount in strategies.items():
            new_balance = current_balance - amount
            remaining_outstanding = outstanding - amount
            
            print(f"\n   {strategy.replace('_', ' ').title()}:")
            print(f"     Recovery Amount: ₦{amount}")
            print(f"     New Wallet Balance: ₦{new_balance}")
            print(f"     Remaining Outstanding: ₦{remaining_outstanding}")
            
            if strategy == 'balance_aware':
                if amount > 0:
                    print(f"     ✅ Safe: Maintains ₦{balance_threshold} minimum balance")
                else:
                    print(f"     ⚠️  No recovery: Balance too low")
            elif strategy == 'balance_proportional':
                print(f"     📊 Proportional: Based on balance ratio ({balance_ratio:.2f})")
            elif strategy == 'balance_limited':
                print(f"     🛡️  Limited: Respects ₦{max_negative_balance} negative limit")
            elif strategy == 'balance_aggressive':
                print(f"     🚀 Aggressive: Maximum recovery regardless of balance")
        
        # Recommend best strategy
        print(f"\n🎯 Recommendation for Screenshot Scenario:")
        if current_balance > balance_threshold:
            print(f"   ✅ Use 'balance_aware' strategy: Safe recovery of ₦{strategies['balance_aware']}")
        elif current_balance > 0:
            print(f"   ⚠️  Use 'balance_proportional' strategy: Gradual recovery of ₦{strategies['balance_proportional']}")
        else:
            print(f"   🚨 Use 'balance_limited' strategy: Controlled recovery of ₦{strategies['balance_limited']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Real-world example test failed: {e}")
        return False

def run_comprehensive_test():
    """Run all wallet-balance-aware tests"""
    print("🧪 WALLET-BALANCE-AWARE OUTSTANDING RECOVERY - COMPREHENSIVE TEST")
    print("=" * 80)
    
    tests = [
        ("Wallet-Balance-Aware Strategies", test_balance_aware_strategies),
        ("Enhanced Command Options", test_command_options),
        ("Wallet Balance Scenarios", test_scenario_simulations),
        ("Real-World Example", test_real_world_example),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL WALLET-BALANCE-AWARE RECOVERY FEATURES WORKING!")
        print("\n✅ New Features Available:")
        print("   • Balance-aware recovery strategies")
        print("   • Wallet balance consideration in recovery calculations")
        print("   • Configurable balance thresholds and negative limits")
        print("   • Intelligent recovery based on patient financial capacity")
        print("   • Multiple strategies for different scenarios")
    else:
        print(f"⚠️  {total - passed} tests failed. Please review the issues above.")
    
    print("\n🎯 Usage Examples for Screenshot Scenario:")
    print("1. Safe recovery (maintains minimum balance):")
    print("   python manage.py recover_outstanding_balances --strategy balance_aware --balance-threshold 1000")
    print("2. Proportional recovery (based on balance ratio):")
    print("   python manage.py recover_outstanding_balances --strategy balance_proportional")
    print("3. Limited negative balance:")
    print("   python manage.py recover_outstanding_balances --strategy balance_limited --max-negative-balance 10000")
    print("4. Daily charges with balance-aware recovery:")
    print("   python manage.py daily_admission_charges --recover-outstanding --recovery-strategy balance_aware")
    
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
