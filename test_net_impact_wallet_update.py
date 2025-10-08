#!/usr/bin/env python
"""
Test script to verify that net impact calculations properly update wallet balances.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from decimal import Decimal
from django.utils import timezone
from accounts.models import CustomUser
from patients.models import Patient, PatientWallet, WalletTransaction
from inpatient.models import Admission, Ward
from billing.models import Invoice
from datetime import date, timedelta

def create_test_data():
    """Create test data for testing net impact calculations"""
    print("Creating test data...")
    
    # Create test patient directly
    import random
    random_suffix = random.randint(1000, 9999)
    patient, _ = Patient.objects.get_or_create(
        patient_id=f'TEST{random_suffix}',
        defaults={
            'first_name': 'Test',
            'last_name': 'Patient',
            'date_of_birth': date(1990, 1, 1),
            'gender': 'M',
            'phone_number': f'123456{random_suffix}',
            'address': 'Test Address',
            'email': f'test{random_suffix}@example.com'
        }
    )
    
    # Create or get patient wallet with initial balance
    wallet, _ = PatientWallet.objects.get_or_create(
        patient=patient,
        defaults={'balance': Decimal('1000.00')}
    )
    
    # Create test ward
    ward, _ = Ward.objects.get_or_create(
        name='Test Ward',
        defaults={
            'ward_type': 'general',
            'charge_per_day': Decimal('100.00'),
            'capacity': 10
        }
    )
    
    # Create test bed
    from inpatient.models import Bed
    bed, _ = Bed.objects.get_or_create(
        ward=ward,
        bed_number='TEST001',
        defaults={
            'is_occupied': False
        }
    )
    
    # Create test admission
    attending_doctor = CustomUser.objects.filter(is_staff=True).first()
    if not attending_doctor:
        # Create a doctor user if none exists
        attending_doctor, _ = CustomUser.objects.get_or_create(
            username='test_doctor',
            defaults={
                'email': 'doctor@example.com',
                'first_name': 'Test',
                'last_name': 'Doctor',
                'phone_number': '9876543210',
                'is_staff': True
            }
        )
    
    admission, _ = Admission.objects.get_or_create(
        patient=patient,
        bed=bed,
        defaults={
            'admission_date': timezone.now() - timedelta(days=3),
            'status': 'admitted',
            'diagnosis': 'Test diagnosis',
            'reason_for_admission': 'Test reason',
            'attending_doctor': attending_doctor,
            'created_by': attending_doctor
        }
    )
    
    # Create test invoice
    invoice, _ = Invoice.objects.get_or_create(
        patient=patient,
        defaults={
            'invoice_number': 'INV001',
            'total_amount': Decimal('500.00'),
            'status': 'pending',
            'date_issued': date.today()
        }
    )
    
    return patient, wallet, admission, invoice

def test_wallet_impact_without_update():
    """Test net impact calculation without updating wallet balance"""
    print("\n=== Testing Net Impact Without Update ===")
    
    patient, wallet, admission, invoice = create_test_data()
    
    # Set initial balance
    initial_balance = Decimal('1000.00')
    wallet.balance = initial_balance
    wallet.save()
    
    print(f"Initial wallet balance: ₦{wallet.balance}")
    
    # Test patient wallet impact without update
    net_impact = wallet.get_total_wallet_impact_with_admissions(update_balance=False)
    print(f"Net impact (without update): ₦{net_impact}")
    print(f"Wallet balance after calculation: ₦{wallet.balance}")
    
    # Verify balance hasn't changed
    assert wallet.balance == initial_balance, "Balance should not change when update_balance=False"
    print("PASS: Balance unchanged when update_balance=False")
    
    # Test admission wallet impact without update
    admission_net_impact = admission.get_total_wallet_impact(update_balance=False)
    print(f"Admission net impact (without update): ₦{admission_net_impact}")
    print(f"Wallet balance after admission calculation: ₦{wallet.balance}")
    
    # Verify balance hasn't changed
    assert wallet.balance == initial_balance, "Balance should not change when update_balance=False"
    print("PASS: Balance unchanged for admission impact when update_balance=False")

def test_wallet_impact_with_update():
    """Test net impact calculation with updating wallet balance"""
    print("\n=== Testing Net Impact With Update ===")
    
    patient, wallet, admission, invoice = create_test_data()
    
    # Set initial balance
    initial_balance = Decimal('1000.00')
    wallet.balance = initial_balance
    wallet.save()
    
    # Create an outstanding invoice to ensure there's something to deduct
    import random
    random_suffix = random.randint(1000, 9999)
    outstanding_invoice, _ = Invoice.objects.get_or_create(
        patient=patient,
        invoice_number=f'OUTSTANDING{random_suffix}',
        defaults={
            'subtotal': Decimal('500.00'),
            'tax_amount': Decimal('0.00'),
            'total_amount': Decimal('500.00'),
            'status': 'pending',
            'invoice_date': date.today(),
            'due_date': date.today() + timedelta(days=30)
        }
    )
    
    print(f"Initial wallet balance: ₦{wallet.balance}")
    print(f"Outstanding invoice amount: ₦{outstanding_invoice.total_amount}")
    
    # Count transactions before
    transaction_count_before = WalletTransaction.objects.filter(wallet=wallet).count()
    
    # Test patient wallet impact with update
    balance_before = wallet.balance
    net_impact = wallet.get_total_wallet_impact_with_admissions(update_balance=True)
    balance_after = wallet.balance
    
    print(f"Balance before calculation: ₦{balance_before}")
    print(f"Net impact (with update): ₦{net_impact}")
    print(f"Balance after calculation: ₦{balance_after}")
    print(f"Balance changed: {balance_before != balance_after}")
    
    # Verify balance has changed
    expected_balance = max(net_impact, Decimal('0.00'))
    assert wallet.balance == expected_balance, f"Balance should be {expected_balance} but is {wallet.balance}"
    print(f"PASS: Balance updated to: ₦{wallet.balance}")
    
    # Verify transaction was created
    transaction_count_after = WalletTransaction.objects.filter(wallet=wallet).count()
    print(f"Transaction count before: {transaction_count_before}")
    print(f"Transaction count after: {transaction_count_after}")
    
    # List all recent transactions for debugging
    recent_transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')[:5]
    for t in recent_transactions:
        print(f"Recent transaction: {t.transaction_type} - ₦{t.amount} - {t.description}")
    
    if transaction_count_after > transaction_count_before:
        print("PASS: Transaction record created")
        # Check the transaction details
        latest_transaction = WalletTransaction.objects.filter(wallet=wallet).latest('created_at')
        print(f"Transaction type: {latest_transaction.transaction_type}")
        print(f"Transaction amount: ₦{latest_transaction.amount}")
        print(f"Transaction description: {latest_transaction.description}")
    else:
        print("WARNING: No new transaction created")

def test_admission_wallet_impact_with_update():
    """Test admission net impact calculation with updating wallet balance"""
    print("\n=== Testing Admission Net Impact With Update ===")
    
    patient, wallet, admission, invoice = create_test_data()
    
    # Set initial balance after admission fee has been automatically deducted
    # The admission fee is already deducted when admission is created via signals
    # So we need to check the current balance after that deduction
    current_balance = wallet.balance
    print(f"Current wallet balance after admission fee deduction: ₦{current_balance}")
    
    # Get admission cost and outstanding amount
    admission_cost = admission.get_total_cost()
    outstanding_cost = admission.get_outstanding_admission_cost()
    print(f"Total admission cost: ₦{admission_cost}")
    print(f"Outstanding admission cost: ₦{outstanding_cost}")
    
    # Count transactions before
    transaction_count_before = WalletTransaction.objects.filter(wallet=wallet).count()
    
    # Test admission wallet impact with update
    net_impact = admission.get_total_wallet_impact(update_balance=True)
    print(f"Admission net impact (with update): ₦{net_impact}")
    print(f"Wallet balance after calculation: ₦{wallet.balance}")
    
    # Verify balance has changed
    expected_balance = max(net_impact, Decimal('0.00'))
    assert wallet.balance == expected_balance, f"Balance should be {expected_balance} but is {wallet.balance}"
    print(f"PASS: Balance updated to: ₦{wallet.balance}")
    
    # If the admission was already fully paid, the balance won't change
    if outstanding_cost == 0:
        print("INFO: Admission was already fully paid, so balance didn't change")
    
    # Verify transaction was created if balance changed
    transaction_count_after = WalletTransaction.objects.filter(wallet=wallet).count()
    if current_balance != expected_balance:
        assert transaction_count_after == transaction_count_before + 1, "A new transaction should be created"
        print("PASS: Transaction record created for admission impact")
        
        # Check the transaction details
        latest_transaction = WalletTransaction.objects.filter(wallet=wallet).latest('created_at')
        print(f"Transaction type: {latest_transaction.transaction_type}")
        print(f"Transaction amount: ₦{latest_transaction.amount}")
        print(f"Transaction description: {latest_transaction.description}")
    else:
        print("INFO: Balance unchanged, no transaction expected")

def test_negative_net_impact():
    """Test net impact calculation when result is negative"""
    print("\n=== Testing Negative Net Impact ===")
    
    patient, wallet, admission, invoice = create_test_data()
    
    # After creating test data, the admission fee has already been deducted
    # We need to add a high-value invoice to create a negative net impact scenario
    from billing.models import Invoice
    import random
    random_suffix = random.randint(1000, 9999)
    high_value_invoice, _ = Invoice.objects.get_or_create(
        patient=patient,
        invoice_number=f'HIGH{random_suffix}',
        defaults={
            'subtotal': Decimal('1000.00'),
            'tax_amount': Decimal('0.00'),
            'total_amount': Decimal('1000.00'),
            'status': 'pending',
            'invoice_date': date.today(),
            'due_date': date.today() + timedelta(days=30)
        }
    )
    
    # Set low initial balance
    initial_balance = Decimal('100.00')
    wallet.balance = initial_balance
    wallet.save()
    
    print(f"Initial wallet balance: ₦{wallet.balance}")
    print(f"High value invoice amount: ₦{high_value_invoice.total_amount}")
    
    # Test patient wallet impact with update
    net_impact = wallet.get_total_wallet_impact_with_admissions(update_balance=True)
    print(f"Net impact (negative): ₦{net_impact}")
    print(f"Wallet balance after calculation: ₦{wallet.balance}")
    
    # Verify balance is 0 when net impact is negative
    assert wallet.balance == Decimal('0.00'), f"Balance should be 0.00 when net impact is negative but is {wallet.balance}"
    print("✓ Balance set to 0 when net impact is negative")

def main():
    """Run all tests"""
    print("Testing Net Impact Wallet Balance Updates")
    print("=" * 50)
    
    try:
        test_wallet_impact_without_update()
        test_wallet_impact_with_update()
        test_admission_wallet_impact_with_update()
        test_negative_net_impact()
        
        print("\n" + "=" * 50)
        print("All tests passed successfully!")
        
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()