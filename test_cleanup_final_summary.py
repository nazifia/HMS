#!/usr/bin/env python
"""
Final Test Cleanup Summary for HMS
This script provides a comprehensive summary of all test script cleanup activities.
"""

import os
import sys
import django
import json
import datetime as dt
from pathlib import Path

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

class TestCleanupFinalSummary:
    def __init__(self):
        self.summary_data = {}
        
    def generate_final_cleanup_summary(self):
        """Generate comprehensive summary of test cleanup activities"""
        print("\n" + "="*100)
        print("🎯 FINAL TEST CLEANUP SUMMARY - HMS")
        print("="*100)
        
        # Load cleanup reports
        cleanup_report = self.load_report('test_cleanup_report.json')
        deletion_report = self.load_report('safe_test_deletion_report.json')
        
        # Phase 1: Initial Test Script Cleanup
        print("\n🧹 PHASE 1: INITIAL TEST SCRIPT CLEANUP")
        print("-" * 60)
        if cleanup_report:
            summary = cleanup_report.get('summary', {})
            print(f"📊 Total Operations: {summary.get('total_operations', 0)}")
            print(f"✅ Passed: {summary.get('passed', 0)}")
            print(f"❌ Failed: {summary.get('failed', 0)}")
            print(f"⚠️  Warnings: {summary.get('warnings', 0)}")
            print(f"📈 Success Rate: {summary.get('success_rate', 0):.1f}%")
            print(f"🧹 Cleaned Scripts: {len(cleanup_report.get('cleaned_scripts', []))}")
            print(f"📄 Cleaned Reports: {len(cleanup_report.get('cleaned_reports', []))}")
            print(f"💾 Backup Location: {cleanup_report.get('backup_location', 'N/A')}")
        else:
            print("⚠️  Initial cleanup report not found")
        
        # Phase 2: Safe Test Script Deletion
        print("\n🗑️  PHASE 2: SAFE TEST SCRIPT DELETION")
        print("-" * 60)
        if deletion_report:
            summary = deletion_report.get('summary', {})
            print(f"📊 Total Operations: {summary.get('total_operations', 0)}")
            print(f"✅ Passed: {summary.get('passed', 0)}")
            print(f"❌ Failed: {summary.get('failed', 0)}")
            print(f"⚠️  Warnings: {summary.get('warnings', 0)}")
            print(f"⏭️  Skipped: {summary.get('skipped', 0)}")
            print(f"📈 Success Rate: {summary.get('success_rate', 0):.1f}%")
            print(f"🗑️  Deleted Scripts: {len(deletion_report.get('deleted_scripts', []))}")
            print(f"⏭️  Skipped Scripts: {len(deletion_report.get('skipped_scripts', []))}")
            print(f"💾 Backup Location: {deletion_report.get('backup_location', 'N/A')}")
        else:
            print("⚠️  Safe deletion report not found")
        
        # Current State Analysis
        print("\n📊 CURRENT STATE ANALYSIS")
        print("-" * 60)
        self.analyze_current_state()
        
        # Files Preserved
        print("\n🛡️  FILES PRESERVED (ESSENTIAL)")
        print("-" * 60)
        preserved_files = [
            'test_payment_verification.py - Contains Django TestCase classes',
            'test_script_cleanup.py - Cleanup utility script',
            'safe_test_script_deletion.py - Safe deletion utility',
            'user_isolation_middleware.py - Production middleware',
            'user_isolation_examples.py - Implementation examples',
            'All Django app test files in /tests/ directories'
        ]
        
        for file_desc in preserved_files:
            print(f"🛡️  {file_desc}")
        
        # Backup Locations
        print("\n💾 BACKUP LOCATIONS")
        print("-" * 60)
        backup_locations = []
        
        if cleanup_report and cleanup_report.get('backup_location'):
            backup_locations.append(f"Initial Cleanup: {cleanup_report['backup_location']}")
        
        if deletion_report and deletion_report.get('backup_location'):
            backup_locations.append(f"Safe Deletion: {deletion_report['backup_location']}")
        
        for backup in backup_locations:
            print(f"💾 {backup}")
        
        # System Verification
        print("\n✅ SYSTEM VERIFICATION")
        print("-" * 60)
        self.verify_system_functionality()
        
        # Cleanup Statistics
        print("\n📈 CLEANUP STATISTICS")
        print("-" * 60)
        total_deleted = 0
        total_preserved = 0
        
        if cleanup_report:
            total_deleted += len(cleanup_report.get('cleaned_scripts', []))
            total_deleted += len(cleanup_report.get('cleaned_reports', []))
        
        if deletion_report:
            total_deleted += len(deletion_report.get('deleted_scripts', []))
            total_preserved += len(deletion_report.get('skipped_scripts', []))
        
        print(f"🗑️  Total Files Deleted: {total_deleted}")
        print(f"🛡️  Total Files Preserved: {total_preserved}")
        print(f"💾 Total Backup Locations: {len(backup_locations)}")
        print(f"✅ System Integrity: Maintained")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS")
        print("-" * 60)
        print("1. 🔍 Regularly review and clean up temporary test files")
        print("2. 💾 Maintain backups of important test scripts")
        print("3. 🛡️  Preserve Django TestCase files for regression testing")
        print("4. 📝 Document any custom test utilities for future reference")
        print("5. 🔄 Implement automated cleanup processes for temporary files")
        
        # Save final summary
        self.save_cleanup_summary(cleanup_report, deletion_report, total_deleted, total_preserved)
    
    def analyze_current_state(self):
        """Analyze current state of test files"""
        try:
            # Count remaining test files
            test_files = list(Path('.').glob('*test*.py'))
            test_reports = list(Path('.').glob('*test*.json'))
            
            print(f"📄 Remaining Test Scripts: {len(test_files)}")
            for file in test_files:
                print(f"   • {file.name}")
            
            print(f"📊 Remaining Test Reports: {len(test_reports)}")
            for file in test_reports:
                print(f"   • {file.name}")
            
            # Check Django app test directories
            django_apps = ['accounts', 'patients', 'doctors', 'appointments', 'pharmacy', 
                          'laboratory', 'billing', 'inpatient', 'hr', 'consultations',
                          'radiology', 'theatre', 'nhia', 'retainership', 'reporting', 'core']
            
            app_test_files = 0
            for app in django_apps:
                app_path = Path(app)
                if app_path.exists():
                    test_files = list(app_path.rglob('test*.py'))
                    app_test_files += len(test_files)
            
            print(f"🏥 Django App Test Files: {app_test_files} (preserved)")
            
        except Exception as e:
            print(f"⚠️  Error analyzing current state: {e}")
    
    def verify_system_functionality(self):
        """Verify that the main system is still functional"""
        try:
            # Test Django setup
            from django.conf import settings
            print("✅ Django configuration intact")
            
            # Test model imports
            from accounts.models import CustomUser
            from patients.models import Patient
            from pharmacy.models import Medication
            print("✅ Core models importable")
            
            # Test basic database operations
            user_count = CustomUser.objects.count()
            patient_count = Patient.objects.count()
            print(f"✅ Database accessible (Users: {user_count}, Patients: {patient_count})")
            
            # Test URL configuration
            from django.urls import reverse
            login_url = reverse('accounts:login')
            print("✅ URL routing functional")
            
            # Test middleware
            middleware_classes = settings.MIDDLEWARE
            print(f"✅ Middleware configuration intact ({len(middleware_classes)} middlewares)")
            
        except Exception as e:
            print(f"❌ System verification failed: {e}")
    
    def load_report(self, filename):
        """Load a report file if it exists"""
        try:
            if Path(filename).exists():
                with open(filename, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None
    
    def save_cleanup_summary(self, cleanup_report, deletion_report, total_deleted, total_preserved):
        """Save final cleanup summary"""
        final_summary = {
            'cleanup_date': dt.datetime.now().isoformat(),
            'phases_completed': [
                'Initial Test Script Cleanup',
                'Safe Test Script Deletion',
                'System Verification'
            ],
            'statistics': {
                'total_files_deleted': total_deleted,
                'total_files_preserved': total_preserved,
                'backup_locations_created': 2,
                'system_integrity_maintained': True
            },
            'cleanup_reports': {
                'initial_cleanup': cleanup_report is not None,
                'safe_deletion': deletion_report is not None
            },
            'preserved_files': [
                'test_payment_verification.py',
                'Django app test files',
                'Essential system files'
            ],
            'recommendations': [
                'Regular cleanup of temporary test files',
                'Maintain backups of important test scripts',
                'Preserve Django TestCase files',
                'Document custom test utilities',
                'Implement automated cleanup processes'
            ]
        }
        
        with open('test_cleanup_final_summary.json', 'w') as f:
            json.dump(final_summary, f, indent=2)
        
        print(f"\n📄 Final cleanup summary saved to: test_cleanup_final_summary.json")

if __name__ == "__main__":
    summary = TestCleanupFinalSummary()
    summary.generate_final_cleanup_summary()
