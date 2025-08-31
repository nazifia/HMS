#!/usr/bin/env python
"""
Check admission charges for NAZIFI AHMAD
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from inpatient.models import Admission
from patients.models import PatientWallet, WalletTransaction
from datetime import date, timedelta

def check_admission_charges():
    print("=== Checking Admission Charges for NAZIFI AHMAD ===")
    
    # Find the admission
    admission = Admission.objects.filter(patient__first_name='NAZIFI').first()
    
    if not admission:
        print("❌ No admission found for NAZIFI")
        return
    
    print(f"✅ Found admission: {admission}")
    print(f"   Patient: {admission.patient.get_full_name()}")
    print(f"   Admission Date: {admission.admission_date}")
    print(f"   Status: {admission.status}")
    print(f"   Ward: {admission.bed.ward.name if admission.bed else 'No bed assigned'}")
    
    if admission.bed and admission.bed.ward:
        daily_charge = admission.bed.ward.charge_per_day
        print(f"   Daily Charge: ₦{daily_charge}")
    else:
        print("   ❌ No bed/ward assigned - cannot calculate charges")
        return
    
    duration = admission.get_duration()
    total_cost = admission.get_total_cost()
    
    print(f"   Duration: {duration} days")
    print(f"   Expected Total Cost: ₦{total_cost}")
    
    # Check wallet
    try:
        wallet = PatientWallet.objects.get(patient=admission.patient)
        print(f"   Current Wallet Balance: ₦{wallet.balance}")
    except PatientWallet.DoesNotExist:
        print("   ❌ No wallet found for patient")
        return
    
    # Check wallet transactions
    print("\n=== Wallet Transaction History ===")
    transactions = WalletTransaction.objects.filter(
        wallet=wallet
    ).order_by('-created_at')
    
    total_debited = 0
    admission_fees = 0
    daily_charges = 0
    
    for tx in transactions:
        print(f"   {tx.created_at.date()} | {tx.transaction_type} | ₦{tx.amount} | {tx.description}")
        if tx.transaction_type == 'admission_fee':
            admission_fees += tx.amount
        elif tx.transaction_type == 'daily_admission_charge':
            daily_charges += tx.amount
        total_debited += tx.amount
    
    print(f"\n=== Summary ===")
    print(f"   Total Admission Fees Deducted: ₦{admission_fees}")
    print(f"   Total Daily Charges Deducted: ₦{daily_charges}")
    print(f"   Total Amount Debited: ₦{total_debited}")
    print(f"   Expected Total (30 days × ₦{daily_charge}): ₦{daily_charge * 30}")
    print(f"   Missing Amount: ₦{(daily_charge * 30) - total_debited}")
    
    # Check if daily charges command has been run
    daily_charge_count = WalletTransaction.objects.filter(
        wallet=wallet,
        transaction_type='daily_admission_charge'
    ).count()
    
    print(f"\n=== Daily Charges Analysis ===")
    print(f"   Number of daily charge transactions: {daily_charge_count}")
    print(f"   Expected daily charge transactions: {duration}")
    print(f"   Missing daily charge transactions: {duration - daily_charge_count}")
    
    if daily_charge_count == 0:
        print("   ⚠️  NO DAILY CHARGES HAVE BEEN PROCESSED!")
        print("   ⚠️  The daily_admission_charges management command has not been run.")
    elif daily_charge_count < duration:
        print(f"   ⚠️  MISSING {duration - daily_charge_count} DAILY CHARGE TRANSACTIONS!")
        print("   ⚠️  The daily_admission_charges command may not be running daily.")
    else:
        print("   ✅ All daily charges have been processed.")

def run_missing_daily_charges():
    """Run daily charges for missing days"""
    print("\n=== Running Missing Daily Charges ===")
    
    admission = Admission.objects.filter(patient__first_name='NAZIFI').first()
    if not admission:
        print("❌ No admission found")
        return
    
    # Import the management command
    from inpatient.management.commands.daily_admission_charges import Command
    
    # Get the date range
    start_date = admission.admission_date.date()
    end_date = date.today()
    
    print(f"Processing charges from {start_date} to {end_date}")
    
    # Run the command for each missing day
    command = Command()
    current_date = start_date
    
    while current_date <= end_date:
        print(f"Processing charges for {current_date}...")
        try:
            # Check if charges already exist for this date
            existing_charges = WalletTransaction.objects.filter(
                wallet__patient=admission.patient,
                transaction_type='daily_admission_charge',
                created_at__date=current_date
            ).exists()
            
            if not existing_charges:
                result = command.process_admission_charge(admission, current_date, dry_run=False)
                if result:
                    print(f"   ✅ Processed ₦{result} for {current_date}")
                else:
                    print(f"   ⚠️  No charge applicable for {current_date}")
            else:
                print(f"   ⏭️  Charges already exist for {current_date}")
                
        except Exception as e:
            print(f"   ❌ Error processing {current_date}: {e}")
        
        current_date += timedelta(days=1)
    
    print("✅ Finished processing missing daily charges")

if __name__ == "__main__":
    check_admission_charges()
    
    # Ask if user wants to run missing charges
    response = input("\nDo you want to run missing daily charges? (y/n): ")
    if response.lower() == 'y':
        run_missing_daily_charges()
        print("\n=== Final Check ===")
        check_admission_charges()
