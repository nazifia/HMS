#!/usr/bin/env python
"""
Database Fixes and Optimizations Script
This script identifies and fixes common database issues across all HMS modules
"""

import os
import sys
import django
from django.db import connection, transaction
from django.core.management import call_command

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def check_database_integrity():
    """Check database integrity and identify issues"""
    print("Checking database integrity...")
    
    issues = []
    
    # Check for missing indexes
    with connection.cursor() as cursor:
        # Check if important indexes exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
        """)
        existing_indexes = [row[0] for row in cursor.fetchall()]
        
        required_indexes = [
            'idx_patient_id',
            'idx_patient_phone', 
            'idx_patient_email',
            'idx_prescription_patient',
            'idx_appointment_date',
            'idx_invoice_patient'
        ]
        
        missing_indexes = [idx for idx in required_indexes if idx not in existing_indexes]
        if missing_indexes:
            issues.append(f"Missing indexes: {missing_indexes}")
    
    return issues

def create_missing_indexes():
    """Create missing database indexes for performance"""
    print("Creating missing database indexes...")
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_patients_patient_id ON patients_patient(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients_patient(phone_number);",
        "CREATE INDEX IF NOT EXISTS idx_patients_email ON patients_patient(email);",
        "CREATE INDEX IF NOT EXISTS idx_patients_type ON patients_patient(patient_type);",
        "CREATE INDEX IF NOT EXISTS idx_patients_active ON patients_patient(is_active);",
        "CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON pharmacy_prescription(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_prescriptions_date ON pharmacy_prescription(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments_appointment(appointment_date);",
        "CREATE INDEX IF NOT EXISTS idx_appointments_doctor ON appointments_appointment(doctor_id);",
        "CREATE INDEX IF NOT EXISTS idx_invoices_patient ON billing_invoice(patient_id);",
        "CREATE INDEX IF NOT EXISTS idx_invoices_date ON billing_invoice(invoice_date);",
        "CREATE INDEX IF NOT EXISTS idx_users_username ON accounts_customuser(username);",
        "CREATE INDEX IF NOT EXISTS idx_users_phone ON accounts_customuser(phone_number);",
    ]
    
    with connection.cursor() as cursor:
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                print(f"✓ Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
            except Exception as e:
                print(f"✗ Failed to create index: {e}")

def fix_duplicate_data():
    """Identify and fix duplicate data issues"""
    print("Checking for duplicate data...")

    from django.db import models
    from patients.models import Patient
    from pharmacy.models import Medication

    # Check for duplicate patient IDs
    duplicate_patients = Patient.objects.values('patient_id').annotate(
        count=models.Count('patient_id')
    ).filter(count__gt=1)

    if duplicate_patients.exists():
        print(f"Found {duplicate_patients.count()} duplicate patient IDs")
        # Handle duplicates (this would need careful manual review)
    else:
        print("✓ No duplicate patient IDs found")

    # Check for duplicate medications
    duplicate_meds = Medication.objects.values('name', 'strength').annotate(
        count=models.Count('id')
    ).filter(count__gt=1)

    if duplicate_meds.exists():
        print(f"Found {duplicate_meds.count()} potential duplicate medications")
    else:
        print("✓ No duplicate medications found")

def optimize_database():
    """Run database optimization commands"""
    print("Optimizing database...")
    
    with connection.cursor() as cursor:
        # SQLite specific optimizations
        cursor.execute("PRAGMA optimize;")
        cursor.execute("VACUUM;")
        cursor.execute("ANALYZE;")
    
    print("✓ Database optimization completed")

def check_foreign_key_constraints():
    """Check for foreign key constraint violations"""
    print("Checking foreign key constraints...")
    
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_key_check;")
        violations = cursor.fetchall()
        
        if violations:
            print(f"Found {len(violations)} foreign key violations:")
            for violation in violations:
                print(f"  - {violation}")
        else:
            print("✓ No foreign key violations found")

def main():
    """Main function to run all database fixes"""
    print("=== HMS Database Fixes and Optimizations ===\n")
    
    try:
        # Check database integrity
        issues = check_database_integrity()
        if issues:
            print("Issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✓ No major integrity issues found")
        
        # Create missing indexes
        create_missing_indexes()
        
        # Fix duplicate data
        fix_duplicate_data()
        
        # Check foreign key constraints
        check_foreign_key_constraints()
        
        # Optimize database
        optimize_database()
        
        print("\n=== Database fixes completed ===")
        
    except Exception as e:
        print(f"Error during database fixes: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
