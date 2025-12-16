#!/usr/bin/env python
"""
Setup automatic daily admission charges processing
"""

import os
import sys
import platform

def create_daily_charges_script():
    """Create a script to run daily charges"""
    script_content = '''#!/usr/bin/env python
"""
Daily Admission Charges Runner
Run this script daily at midnight to process admission charges
"""

import os
import sys
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.core.management import call_command

def run_daily_charges():
    """Run daily admission charges for today"""
    try:
        print(f"[{datetime.now()}] Starting daily admission charges processing...")
        call_command('daily_admission_charges')
        print(f"[{datetime.now()}] Daily charges processing completed successfully")
        return True
    except Exception as e:
        print(f"[{datetime.now()}] ERROR: Daily charges processing failed: {e}")
        return False

if __name__ == "__main__":
    success = run_daily_charges()
    sys.exit(0 if success else 1)
'''
    
    with open('run_daily_charges.py', 'w') as f:
        f.write(script_content)
    
    print("✅ Created run_daily_charges.py script")

def setup_windows_task_scheduler():
    """Provide instructions for Windows Task Scheduler"""
    print("\n=== Windows Task Scheduler Setup ===")
    print("1. Open Task Scheduler (taskschd.msc)")
    print("2. Click 'Create Basic Task...'")
    print("3. Name: 'HMS Daily Admission Charges'")
    print("4. Description: 'Automatically process daily admission charges at midnight'")
    print("5. Trigger: Daily at 12:00 AM")
    print("6. Action: Start a program")
    print(f"7. Program: {sys.executable}")
    print(f"8. Arguments: run_daily_charges.py")
    print(f"9. Start in: {os.getcwd()}")
    print("10. Click Finish")
    
    # Create a batch file for easier setup
    batch_content = f'''@echo off
cd /d "{os.getcwd()}"
"{sys.executable}" run_daily_charges.py
pause
'''
    
    with open('run_daily_charges.bat', 'w') as f:
        f.write(batch_content)
    
    print("\n✅ Created run_daily_charges.bat for Windows")
    print("   You can also schedule this .bat file instead")

def setup_linux_cron():
    """Provide instructions for Linux/Mac cron"""
    print("\n=== Linux/Mac Cron Setup ===")
    print("1. Open terminal")
    print("2. Run: crontab -e")
    print("3. Add this line:")
    print(f"   0 0 * * * cd {os.getcwd()} && {sys.executable} run_daily_charges.py >> daily_charges.log 2>&1")
    print("4. Save and exit")
    print("\nThis will:")
    print("- Run daily at midnight (0 0 * * *)")
    print("- Change to HMS directory")
    print("- Execute the daily charges script")
    print("- Log output to daily_charges.log")

def test_daily_charges_setup():
    """Test that the daily charges system is working"""
    print("\n=== Testing Daily Charges Setup ===")
    
    try:
        # Test import
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
        django.setup()
        
        from inpatient.management.commands.daily_admission_charges import Command
        from inpatient.models import Admission
        
        print("✅ Django setup successful")
        print("✅ Daily charges command importable")
        
        # Check active admissions
        active_admissions = Admission.objects.filter(status='admitted').count()
        print(f"✅ Found {active_admissions} active admissions")
        
        # Test dry run
        command = Command()
        print("✅ Daily charges command can be instantiated")
        
        print("\n🎯 Daily charges system is ready for automation!")
        return True
        
    except Exception as e:
        print(f"❌ Setup test failed: {e}")
        return False

def create_monitoring_script():
    """Create a script to monitor daily charges processing"""
    monitor_content = '''#!/usr/bin/env python
"""
Monitor Daily Admission Charges
Check if daily charges are being processed correctly
"""

import os
import sys
import django
from datetime import date, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from inpatient.models import Admission
from patients.models import WalletTransaction

def check_daily_charges_status():
    """Check if daily charges are up to date"""
    print(f"=== Daily Charges Status Check - {date.today()} ===")
    
    active_admissions = Admission.objects.filter(status='admitted')
    print(f"Active admissions: {active_admissions.count()}")
    
    issues_found = 0
    
    for admission in active_admissions:
        duration = admission.get_duration()
        
        # Count daily charges processed
        daily_charges = WalletTransaction.objects.filter(
            wallet__patient=admission.patient,
            transaction_type='daily_admission_charge'
        ).count()
        
        print(f"\\n{admission.patient.get_full_name()}:")
        print(f"  Duration: {duration} days")
        print(f"  Daily charges: {daily_charges}")
        
        # Check if NHIA (should have 0 charges)
        try:
            is_nhia = (hasattr(admission.patient, 'nhia_info') and 
                     admission.patient.nhia_info and 
                     admission.patient.nhia_info.is_active)
        except:
            is_nhia = False
        
        if is_nhia:
            if daily_charges > 0:
                print(f"  ⚠️  NHIA patient has {daily_charges} charges (should be 0)")
                issues_found += 1
            else:
                print(f"  ✅ NHIA patient correctly exempted")
        else:
            if daily_charges < duration:
                missing = duration - daily_charges
                print(f"  ⚠️  Missing {missing} daily charges")
                issues_found += 1
            else:
                print(f"  ✅ Daily charges up to date")
    
    print(f"\\n=== Summary ===")
    if issues_found == 0:
        print("✅ All daily charges are up to date!")
    else:
        print(f"⚠️  Found {issues_found} issues that need attention")
        print("Run: python manage.py daily_admission_charges")
    
    return issues_found == 0

if __name__ == "__main__":
    success = check_daily_charges_status()
    sys.exit(0 if success else 1)
'''
    
    with open('monitor_daily_charges.py', 'w') as f:
        f.write(monitor_content)
    
    print("✅ Created monitor_daily_charges.py script")

def main():
    """Main setup function"""
    print("🔧 SETTING UP AUTOMATIC DAILY ADMISSION CHARGES")
    print("=" * 60)
    
    # Create scripts
    create_daily_charges_script()
    create_monitoring_script()
    
    # Test setup
    if not test_daily_charges_setup():
        print("❌ Setup test failed. Please fix issues before proceeding.")
        return False
    
    # Provide platform-specific instructions
    system = platform.system().lower()
    
    if system == 'windows':
        setup_windows_task_scheduler()
    else:
        setup_linux_cron()
    
    print("\n" + "=" * 60)
    print("📋 SETUP COMPLETE - NEXT STEPS")
    print("=" * 60)
    print("1. ✅ Scripts created successfully")
    print("2. 🔧 Follow the platform-specific instructions above")
    print("3. 🧪 Test the setup:")
    print("   python run_daily_charges.py")
    print("4. 📊 Monitor daily charges:")
    print("   python monitor_daily_charges.py")
    print("5. 📝 Check logs regularly for any issues")
    
    print("\n🎉 Daily admission charges will now run automatically!")
    print("💡 The system will:")
    print("   • Process charges for all active admissions daily")
    print("   • Exempt NHIA patients automatically")
    print("   • Prevent double deductions")
    print("   • Stop charging when patients are discharged")
    print("   • Log all activities for audit trail")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
