#!/usr/bin/env python
"""
Final Migration Fix Script
This script ensures all migrations are applied and the database is ready
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def check_migrations():
    """Check if all migrations are applied"""
    print("=== Checking Migration Status ===")
    
    from django.core.management import call_command
    from io import StringIO
    
    try:
        # Check migration status
        output = StringIO()
        call_command('showmigrations', '--plan', stdout=output)
        migrations_output = output.getvalue()
        
        if '[ ]' in migrations_output:
            print("❌ Found unapplied migrations")
            print("Applying migrations...")
            call_command('migrate')
            print("✅ All migrations applied successfully")
        else:
            print("✅ All migrations are up to date")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration check failed: {e}")
        return False

def test_database_access():
    """Test database access with the new fields"""
    print("\n=== Testing Database Access ===")
    
    try:
        from patients.models import Patient
        from core.models import AuditLog, InternalNotification
        
        # Test patient model with new fields
        patient_count = Patient.objects.count()
        print(f"✅ Patient model access successful: {patient_count} patients")
        
        # Test if we can access the new created_at field
        if patient_count > 0:
            first_patient = Patient.objects.first()
            created_at = first_patient.created_at
            print(f"✅ Patient created_at field accessible: {created_at}")
        
        # Test core models
        audit_count = AuditLog.objects.count()
        print(f"✅ AuditLog model access successful: {audit_count} logs")
        
        notification_count = InternalNotification.objects.count()
        print(f"✅ InternalNotification model access successful: {notification_count} notifications")
        
        return True
        
    except Exception as e:
        print(f"❌ Database access test failed: {e}")
        return False

def test_pharmacy_prescriptions():
    """Test the specific pharmacy prescriptions page that was failing"""
    print("\n=== Testing Pharmacy Prescriptions Access ===")
    
    try:
        from pharmacy.models import Prescription
        from patients.models import Patient
        
        # Test prescription access
        prescription_count = Prescription.objects.count()
        print(f"✅ Prescription model access successful: {prescription_count} prescriptions")
        
        # Test the specific query that was failing
        prescriptions_with_patients = Prescription.objects.select_related('patient').all()[:5]
        for prescription in prescriptions_with_patients:
            patient = prescription.patient
            # This should now work without the "no such column" error
            created_at = patient.created_at if hasattr(patient, 'created_at') else 'N/A'
            print(f"✅ Prescription {prescription.id} - Patient: {patient.get_full_name()} - Created: {created_at}")
        
        return True
        
    except Exception as e:
        print(f"❌ Pharmacy prescriptions test failed: {e}")
        return False

def run_system_check():
    """Run Django system check"""
    print("\n=== Running System Check ===")
    
    from django.core.management import call_command
    
    try:
        call_command('check')
        print("✅ System check passed")
        return True
    except Exception as e:
        print(f"❌ System check failed: {e}")
        return False

def update_existing_records():
    """Update existing records to have proper timestamps"""
    print("\n=== Updating Existing Records ===")
    
    try:
        from patients.models import Patient
        from django.utils import timezone
        
        # Update patients without created_at
        patients_without_created_at = Patient.objects.filter(created_at__isnull=True)
        count = patients_without_created_at.count()
        
        if count > 0:
            print(f"Updating {count} patients without created_at timestamps...")
            patients_without_created_at.update(
                created_at=timezone.now(),
                updated_at=timezone.now()
            )
            print(f"✅ Updated {count} patient records")
        else:
            print("✅ All patient records have timestamps")
        
        return True
        
    except Exception as e:
        print(f"❌ Record update failed: {e}")
        return False

def main():
    """Main function to run all fixes"""
    print("🔧 Final Migration Fix Script")
    print("=" * 50)
    
    success_count = 0
    total_checks = 5
    
    # Run all checks
    if check_migrations():
        success_count += 1
    
    if update_existing_records():
        success_count += 1
    
    if test_database_access():
        success_count += 1
    
    if test_pharmacy_prescriptions():
        success_count += 1
    
    if run_system_check():
        success_count += 1
    
    # Summary
    print(f"\n{'=' * 50}")
    print("📊 FINAL SUMMARY")
    print(f"{'=' * 50}")
    print(f"Successful checks: {success_count}/{total_checks}")
    
    if success_count == total_checks:
        print("🎉 All checks passed! Database migration fix complete.")
        print("\n✅ The pharmacy prescriptions page should now work correctly.")
        print("✅ You can now start the server with: python manage.py runserver")
        return 0
    else:
        print(f"❌ {total_checks - success_count} checks failed.")
        print("Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
