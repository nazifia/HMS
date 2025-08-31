#!/usr/bin/env python
"""
Fix overcharged patient by reversing incorrect daily charges
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
from decimal import Decimal

def fix_overcharged_patient():
    print("=== Fixing Overcharged Patient: NAZIFI AHMAD ===")
    
    # Find the admission
    admission = Admission.objects.filter(patient__first_name='NAZIFI').first()
    
    if not admission:
        print("❌ No admission found for NAZIFI")
        return
    
    print(f"✅ Found admission: {admission}")
    print(f"   Admission Date: {admission.admission_date.date()}")
    print(f"   Discharge Date: {admission.discharge_date.date() if admission.discharge_date else 'Not discharged'}")
    print(f"   Status: {admission.status}")
    
    # Calculate correct duration
    admission_date = admission.admission_date.date()
    discharge_date = admission.discharge_date.date() if admission.discharge_date else date.today()
    correct_duration = (discharge_date - admission_date).days + 1  # Include admission day
    
    print(f"   Correct Duration: {correct_duration} days")
    
    # Get wallet
    try:
        wallet = PatientWallet.objects.get(patient=admission.patient)
        print(f"   Current Wallet Balance: ₦{wallet.balance}")
    except PatientWallet.DoesNotExist:
        print("   ❌ No wallet found for patient")
        return
    
    # Find all daily admission charges
    daily_charges = WalletTransaction.objects.filter(
        wallet=wallet,
        transaction_type='daily_admission_charge'
    ).order_by('created_at')
    
    print(f"\n=== Daily Charges Analysis ===")
    print(f"   Total daily charge transactions: {daily_charges.count()}")
    print(f"   Correct number should be: {correct_duration}")
    
    # Identify incorrect charges (after discharge date)
    incorrect_charges = []
    correct_charges = []
    
    for charge in daily_charges:
        # Extract date from description
        description = charge.description
        if 'Daily admission charge for' in description:
            try:
                # Extract date from description like "Daily admission charge for 2025-07-01 - A & E"
                date_str = description.split('for ')[1].split(' -')[0]
                charge_date = date.fromisoformat(date_str)
                
                if charge_date <= discharge_date:
                    correct_charges.append(charge)
                else:
                    incorrect_charges.append(charge)
            except:
                print(f"   ⚠️  Could not parse date from: {description}")
                incorrect_charges.append(charge)  # Assume incorrect if can't parse
    
    print(f"   Correct charges: {len(correct_charges)}")
    print(f"   Incorrect charges: {len(incorrect_charges)}")
    
    if len(incorrect_charges) == 0:
        print("   ✅ No incorrect charges found!")
        return
    
    # Calculate refund amount
    total_refund = sum(charge.amount for charge in incorrect_charges)
    print(f"   Total refund amount: ₦{total_refund}")
    
    # Ask for confirmation
    response = input(f"\nDo you want to refund ₦{total_refund} for {len(incorrect_charges)} incorrect charges? (y/n): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Process refunds
    print("\n=== Processing Refunds ===")
    
    for charge in incorrect_charges:
        try:
            # Credit back the amount
            wallet.credit(
                amount=charge.amount,
                description=f"Refund for incorrect daily charge: {charge.description}",
                transaction_type='refund',
                user=None  # System refund
            )
            
            # Mark the original transaction as reversed (add a note)
            charge.description += " [REVERSED - Charged after discharge]"
            charge.save()
            
            print(f"   ✅ Refunded ₦{charge.amount} for charge on {charge.created_at.date()}")
            
        except Exception as e:
            print(f"   ❌ Error refunding charge {charge.id}: {e}")
    
    # Final summary
    wallet.refresh_from_db()
    print(f"\n=== Final Summary ===")
    print(f"   New wallet balance: ₦{wallet.balance}")
    print(f"   Total refunded: ₦{total_refund}")
    print(f"   Corrected {len(incorrect_charges)} incorrect charges")
    
    # Verify correct charges
    expected_total = len(correct_charges) * admission.bed.ward.charge_per_day
    print(f"   Expected total for {len(correct_charges)} days: ₦{expected_total}")

def create_automatic_daily_charges_system():
    """Create a system to automatically run daily charges"""
    print("\n=== Setting Up Automatic Daily Charges ===")
    
    # Create a simple script that can be run daily
    script_content = '''#!/usr/bin/env python
"""
Daily Admission Charges - Run this script daily at midnight
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.core.management import call_command
from datetime import date

def run_daily_charges():
    """Run daily admission charges for today"""
    try:
        print(f"Running daily admission charges for {date.today()}")
        call_command('daily_admission_charges')
        print("Daily charges completed successfully")
    except Exception as e:
        print(f"Error running daily charges: {e}")

if __name__ == "__main__":
    run_daily_charges()
'''
    
    with open('run_daily_charges.py', 'w') as f:
        f.write(script_content)
    
    print("✅ Created run_daily_charges.py script")
    print("\nTo set up automatic daily execution:")
    print("1. For Windows: Use Task Scheduler")
    print("   - Create a daily task at 12:00 AM")
    print("   - Command: python run_daily_charges.py")
    print("\n2. For Linux/Mac: Use cron")
    print("   - Run: crontab -e")
    print("   - Add: 0 0 * * * cd /path/to/hms && python run_daily_charges.py")

if __name__ == "__main__":
    fix_overcharged_patient()
    create_automatic_daily_charges_system()
