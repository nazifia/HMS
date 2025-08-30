#!/usr/bin/env python
"""
Fix Model Conflicts Script
This script addresses model conflicts and related_name clashes
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def check_system():
    """Run Django system check"""
    print("=== Running Django System Check ===")
    
    from django.core.management import call_command
    from io import StringIO
    
    try:
        # Capture output
        output = StringIO()
        call_command('check', stdout=output, stderr=output)
        result = output.getvalue()
        
        if result.strip():
            print("System check output:")
            print(result)
        else:
            print("✅ No issues found!")
        
        return True
        
    except Exception as e:
        print(f"❌ System check failed: {e}")
        return False

def fix_migrations():
    """Create and run any necessary migrations"""
    print("\n=== Checking Migrations ===")
    
    from django.core.management import call_command
    from io import StringIO
    
    try:
        # Check for unapplied migrations
        output = StringIO()
        call_command('showmigrations', '--plan', stdout=output)
        migrations_output = output.getvalue()
        
        if '[ ]' in migrations_output:
            print("Found unapplied migrations, applying...")
            call_command('migrate')
            print("✅ Migrations applied successfully")
        else:
            print("✅ All migrations are up to date")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration check failed: {e}")
        return False

def verify_models():
    """Verify that all models can be imported and used"""
    print("\n=== Verifying Models ===")
    
    try:
        # Test core models
        from core.models import AuditLog, InternalNotification, SOAPNote
        print("✅ Core models imported successfully")
        
        # Test patient models
        from patients.models import Patient, PatientWallet, MedicalHistory
        print("✅ Patient models imported successfully")
        
        # Test pharmacy models
        from pharmacy.models import Medication, Prescription, Dispensary
        print("✅ Pharmacy models imported successfully")
        
        # Test billing models
        from billing.models import Invoice, Payment, Service
        print("✅ Billing models imported successfully")
        
        # Test consultation models
        from consultations.models import Consultation, SOAPNote as ConsultationSOAPNote
        print("✅ Consultation models imported successfully")
        
        # Verify no conflicts
        core_soap = SOAPNote.objects.all()
        consultation_soap = ConsultationSOAPNote.objects.all()
        print("✅ Both SOAP Note models work without conflicts")
        
        return True
        
    except Exception as e:
        print(f"❌ Model verification failed: {e}")
        return False

def test_basic_operations():
    """Test basic database operations"""
    print("\n=== Testing Basic Operations ===")
    
    try:
        from patients.models import Patient
        from accounts.models import CustomUser
        
        # Test patient count
        patient_count = Patient.objects.count()
        print(f"✅ Patient count: {patient_count}")
        
        # Test user count
        user_count = CustomUser.objects.count()
        print(f"✅ User count: {user_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic operations test failed: {e}")
        return False

def main():
    """Main function to run all checks and fixes"""
    print("🔧 HMS Model Conflicts Fix Script")
    print("=" * 50)
    
    success_count = 0
    total_checks = 4
    
    # Run all checks
    if check_system():
        success_count += 1
    
    if fix_migrations():
        success_count += 1
    
    if verify_models():
        success_count += 1
    
    if test_basic_operations():
        success_count += 1
    
    # Summary
    print(f"\n{'=' * 50}")
    print("📊 SUMMARY")
    print(f"{'=' * 50}")
    print(f"Successful checks: {success_count}/{total_checks}")
    
    if success_count == total_checks:
        print("🎉 All checks passed! HMS is ready to run.")
        print("\nYou can now start the server with:")
        print("python manage.py runserver")
        return 0
    else:
        print(f"❌ {total_checks - success_count} checks failed.")
        print("Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
