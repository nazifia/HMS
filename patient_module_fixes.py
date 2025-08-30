#!/usr/bin/env python
"""
Patient Management Module Comprehensive Fixes
This script addresses all issues in the patient management system
"""

import os
import sys
import django
from django.db import transaction
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from patients.models import Patient, PatientWallet, WalletTransaction, MedicalHistory, Vitals
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()

def fix_patient_registration():
    """Fix patient registration issues"""
    print("=== Fixing Patient Registration ===")
    
    # Fix patients without patient_id
    patients_without_id = Patient.objects.filter(patient_id__isnull=True)
    print(f"Found {patients_without_id.count()} patients without IDs")
    
    for patient in patients_without_id:
        try:
            patient.save()  # This will trigger ID generation
            print(f"✓ Generated ID {patient.patient_id} for {patient.get_full_name()}")
        except Exception as e:
            print(f"✗ Failed to generate ID for patient {patient.id}: {e}")
    
    # Fix duplicate patient IDs
    from django.db.models import Count
    duplicate_ids = Patient.objects.values('patient_id').annotate(
        count=Count('patient_id')
    ).filter(count__gt=1)
    
    if duplicate_ids.exists():
        print(f"Found {duplicate_ids.count()} duplicate patient IDs")
        for dup in duplicate_ids:
            patients = Patient.objects.filter(patient_id=dup['patient_id'])
            # Keep the first one, regenerate IDs for others
            for patient in patients[1:]:
                patient.patient_id = None
                patient.save()
                print(f"✓ Fixed duplicate ID for {patient.get_full_name()}")

def fix_wallet_system():
    """Fix patient wallet system issues"""
    print("\n=== Fixing Patient Wallet System ===")
    
    # Ensure all patients have wallets
    patients_without_wallets = Patient.objects.filter(wallet__isnull=True)
    print(f"Found {patients_without_wallets.count()} patients without wallets")
    
    for patient in patients_without_wallets:
        try:
            PatientWallet.objects.create(
                patient=patient,
                balance=Decimal('0.00')
            )
            print(f"✓ Created wallet for {patient.get_full_name()}")
        except Exception as e:
            print(f"✗ Failed to create wallet for {patient.get_full_name()}: {e}")
    
    # Fix wallet balance inconsistencies
    wallets_with_issues = PatientWallet.objects.filter(balance__lt=0)
    if wallets_with_issues.exists():
        print(f"Found {wallets_with_issues.count()} wallets with negative balances")
        for wallet in wallets_with_issues:
            # Calculate actual balance from transactions
            transactions = WalletTransaction.objects.filter(wallet=wallet)
            actual_balance = sum(
                t.amount if t.transaction_type == 'credit' else -t.amount 
                for t in transactions
            )
            
            if wallet.balance != actual_balance:
                wallet.balance = actual_balance
                wallet.save()
                print(f"✓ Fixed balance for {wallet.patient.get_full_name()}: {actual_balance}")

def fix_medical_history():
    """Fix medical history management"""
    print("\n=== Fixing Medical History Management ===")
    
    # Check for orphaned medical histories
    orphaned_histories = MedicalHistory.objects.filter(patient__isnull=True)
    if orphaned_histories.exists():
        print(f"Found {orphaned_histories.count()} orphaned medical histories")
        orphaned_histories.delete()
        print("✓ Cleaned up orphaned medical histories")
    
    # Ensure medical histories have proper timestamps
    histories_without_dates = MedicalHistory.objects.filter(date_recorded__isnull=True)
    for history in histories_without_dates:
        history.date_recorded = history.created_at if hasattr(history, 'created_at') else timezone.now()
        history.save()
        print(f"✓ Fixed date for medical history {history.id}")

def fix_vitals_system():
    """Fix patient vitals system"""
    print("\n=== Fixing Patient Vitals System ===")
    
    # Check for invalid vital signs
    invalid_vitals = Vitals.objects.filter(
        models.Q(systolic_bp__lt=0) | 
        models.Q(diastolic_bp__lt=0) |
        models.Q(heart_rate__lt=0) |
        models.Q(temperature__lt=0) |
        models.Q(respiratory_rate__lt=0)
    )
    
    if invalid_vitals.exists():
        print(f"Found {invalid_vitals.count()} records with invalid vital signs")
        for vital in invalid_vitals:
            print(f"⚠ Invalid vitals for patient {vital.patient.get_full_name()} on {vital.date_recorded}")

def enhance_patient_search():
    """Enhance patient search functionality"""
    print("\n=== Enhancing Patient Search ===")
    
    # Create search indexes if they don't exist
    from django.db import connection
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_patients_search_name ON patients_patient(first_name, last_name);",
        "CREATE INDEX IF NOT EXISTS idx_patients_search_phone ON patients_patient(phone_number);",
        "CREATE INDEX IF NOT EXISTS idx_patients_search_email ON patients_patient(email);",
        "CREATE INDEX IF NOT EXISTS idx_patients_search_id ON patients_patient(patient_id);",
    ]
    
    with connection.cursor() as cursor:
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                index_name = index_sql.split('idx_')[1].split(' ')[0]
                print(f"✓ Created/verified search index: {index_name}")
            except Exception as e:
                print(f"✗ Failed to create search index: {e}")

def validate_patient_data():
    """Validate patient data integrity"""
    print("\n=== Validating Patient Data ===")
    
    # Check for patients with invalid ages
    from django.utils import timezone
    today = timezone.now().date()
    
    invalid_ages = Patient.objects.filter(date_of_birth__gt=today)
    if invalid_ages.exists():
        print(f"Found {invalid_ages.count()} patients with future birth dates")
        for patient in invalid_ages:
            print(f"⚠ Invalid birth date for {patient.get_full_name()}: {patient.date_of_birth}")
    
    # Check for patients over 150 years old
    from datetime import date, timedelta
    old_date = today - timedelta(days=150*365)
    very_old_patients = Patient.objects.filter(date_of_birth__lt=old_date)
    
    if very_old_patients.exists():
        print(f"Found {very_old_patients.count()} patients over 150 years old")
        for patient in very_old_patients:
            print(f"⚠ Very old patient: {patient.get_full_name()}, Age: {patient.get_age()}")

def fix_patient_relationships():
    """Fix patient relationship issues"""
    print("\n=== Fixing Patient Relationships ===")
    
    # Check for patients with invalid primary doctors
    patients_with_invalid_doctors = Patient.objects.filter(
        primary_doctor__isnull=False,
        primary_doctor__is_active=False
    )
    
    if patients_with_invalid_doctors.exists():
        print(f"Found {patients_with_invalid_doctors.count()} patients with inactive primary doctors")
        for patient in patients_with_invalid_doctors:
            patient.primary_doctor = None
            patient.save()
            print(f"✓ Removed inactive doctor from {patient.get_full_name()}")

def create_patient_reports():
    """Create patient management reports"""
    print("\n=== Creating Patient Reports ===")
    
    total_patients = Patient.objects.count()
    active_patients = Patient.objects.filter(is_active=True).count()
    nhia_patients = Patient.objects.filter(patient_type='nhia').count()
    patients_with_wallets = Patient.objects.filter(wallet__isnull=False).count()
    
    print(f"📊 Patient Statistics:")
    print(f"   Total Patients: {total_patients}")
    print(f"   Active Patients: {active_patients}")
    print(f"   NHIA Patients: {nhia_patients}")
    print(f"   Patients with Wallets: {patients_with_wallets}")
    
    # Wallet statistics
    total_wallet_balance = PatientWallet.objects.aggregate(
        total=models.Sum('balance')
    )['total'] or Decimal('0.00')
    
    print(f"   Total Wallet Balance: ₦{total_wallet_balance:,.2f}")

def main():
    """Main function to run all patient module fixes"""
    print("=== Patient Management Module Comprehensive Fixes ===\n")
    
    try:
        with transaction.atomic():
            fix_patient_registration()
            fix_wallet_system()
            fix_medical_history()
            fix_vitals_system()
            enhance_patient_search()
            validate_patient_data()
            fix_patient_relationships()
            create_patient_reports()
        
        print("\n=== Patient module fixes completed successfully ===")
        return 0
        
    except Exception as e:
        print(f"\n✗ Error during patient module fixes: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
