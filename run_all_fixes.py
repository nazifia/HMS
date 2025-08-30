#!/usr/bin/env python
"""
Master Script to Run All HMS Fixes
This script executes all fixes in the correct order
"""

import os
import sys
import subprocess
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def run_script(script_name, description):
    """Run a Python script and capture output"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Script: {script_name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ SUCCESS")
            if result.stdout:
                print("Output:")
                print(result.stdout)
        else:
            print("❌ FAILED")
            if result.stderr:
                print("Error:")
                print(result.stderr)
            if result.stdout:
                print("Output:")
                print(result.stdout)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT - Script took too long to execute")
        return False
    except Exception as e:
        print(f"💥 EXCEPTION - {e}")
        return False

def run_django_command(command, description):
    """Run a Django management command"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: python manage.py {command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, 'manage.py'] + command.split(), 
                              capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print("✅ SUCCESS")
            if result.stdout:
                print("Output:")
                print(result.stdout)
        else:
            print("❌ FAILED")
            if result.stderr:
                print("Error:")
                print(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT - Command took too long")
        return False
    except Exception as e:
        print(f"💥 EXCEPTION - {e}")
        return False

def create_backup():
    """Create a backup before running fixes"""
    print("\n📦 Creating backup...")
    backup_name = f"hms_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Copy database
        if os.path.exists('db.sqlite3'):
            import shutil
            shutil.copy2('db.sqlite3', f'{backup_name}_db.sqlite3')
            print(f"✅ Database backed up to {backup_name}_db.sqlite3")
        
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def verify_system():
    """Verify system integrity after fixes"""
    print("\n🔍 Verifying system integrity...")
    
    try:
        from patients.models import Patient
        from pharmacy.models import Medication
        from billing.models import Invoice
        from accounts.models import CustomUser
        
        # Basic counts
        patient_count = Patient.objects.count()
        medication_count = Medication.objects.count()
        invoice_count = Invoice.objects.count()
        user_count = CustomUser.objects.count()
        
        print(f"✅ System verification complete:")
        print(f"   - Patients: {patient_count}")
        print(f"   - Medications: {medication_count}")
        print(f"   - Invoices: {invoice_count}")
        print(f"   - Users: {user_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ System verification failed: {e}")
        return False

def main():
    """Main function to run all fixes"""
    print("🏥 HMS Comprehensive Fixes - Master Execution Script")
    print(f"Started at: {datetime.now()}")
    
    # Track results
    results = []
    
    # Step 1: Create backup
    if create_backup():
        results.append(("Backup Creation", True))
    else:
        results.append(("Backup Creation", False))
        print("⚠️  Continuing without backup...")
    
    # Step 2: Run Django checks
    success = run_django_command("check", "Django System Check")
    results.append(("Django System Check", success))
    
    # Step 3: Run database fixes
    success = run_script("database_fixes.py", "Database Fixes and Optimizations")
    results.append(("Database Fixes", success))
    
    # Step 4: Run patient module fixes
    success = run_script("patient_module_fixes.py", "Patient Module Fixes")
    results.append(("Patient Module Fixes", success))
    
    # Step 5: Run all modules fixes
    success = run_script("all_modules_fixes.py", "All Modules Comprehensive Fixes")
    results.append(("All Modules Fixes", success))
    
    # Step 6: Run comprehensive fixes
    success = run_script("comprehensive_hms_fixes.py", "Comprehensive HMS Fixes")
    results.append(("Comprehensive Fixes", success))
    
    # Step 7: Run migrations (if any)
    success = run_django_command("migrate", "Database Migrations")
    results.append(("Database Migrations", success))
    
    # Step 8: Collect static files
    success = run_django_command("collectstatic --noinput", "Collect Static Files")
    results.append(("Collect Static Files", success))
    
    # Step 9: Final system check
    success = run_django_command("check --deploy", "Production Deployment Check")
    results.append(("Production Check", success))
    
    # Step 10: Verify system
    success = verify_system()
    results.append(("System Verification", success))
    
    # Print final summary
    print(f"\n{'='*80}")
    print("🎯 FINAL EXECUTION SUMMARY")
    print(f"{'='*80}")
    
    total_tasks = len(results)
    successful_tasks = sum(1 for _, success in results if success)
    
    for task_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{task_name:<30} {status}")
    
    print(f"\n📊 Overall Results:")
    print(f"   Total Tasks: {total_tasks}")
    print(f"   Successful: {successful_tasks}")
    print(f"   Failed: {total_tasks - successful_tasks}")
    print(f"   Success Rate: {(successful_tasks/total_tasks)*100:.1f}%")
    
    if successful_tasks == total_tasks:
        print("\n🎉 ALL FIXES COMPLETED SUCCESSFULLY!")
        print("✅ HMS system is now optimized and production-ready")
    else:
        print(f"\n⚠️  {total_tasks - successful_tasks} tasks failed")
        print("❗ Please review the error messages above")
    
    print(f"\nCompleted at: {datetime.now()}")
    
    return 0 if successful_tasks == total_tasks else 1

if __name__ == "__main__":
    sys.exit(main())
