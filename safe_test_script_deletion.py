#!/usr/bin/env python
"""
Safe Test Script Deletion for HMS
This script safely deletes test scripts while ensuring no dependencies exist.
"""

import os
import sys
import django
import json
import shutil
import datetime as dt
from pathlib import Path

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

class SafeTestScriptDeletion:
    def __init__(self):
        self.deletion_results = []
        self.root_dir = Path('.')
        self.test_scripts = []
        self.backup_dir = Path('test_deletion_backup')
        
        # Define test scripts that are safe to delete
        self.safe_test_patterns = [
            'comprehensive_test.py',
            'final_test.py', 
            'quick_test.py',
            'simple_test.py',
            'simple_wallet_test.py',
            'test_ajax.py',
            'test_ajax_endpoint.py',
            'test_dispensary.py',
            'test_dispensary_view.py',
            'test_dispensed_items.py',
            'test_dispensing.py',
            'test_dispensing_simple.py',
            'test_dispensing_view.py',
            'test_payment_verification.py',
            'test_pharmacy_views.py',
            'test_prescription_creation.py',
            'test_pricing_logic.py',
            'test_profile_fix.py',
            'test_retainership_workflow.py',
            'test_server_startup.py',
            'test_wallet_transfer.py',
            'setup_test_inventory.py'
        ]
        
        # Files to preserve (essential for system operation)
        self.preserve_patterns = [
            'test_script_cleanup.py',
            'safe_test_script_deletion.py',
            'user_isolation_middleware.py',
            'user_isolation_examples.py',
            'manage.py',
            'requirements.txt'
        ]
    
    def discover_test_files(self):
        """Discover test files that can be safely deleted"""
        print("🔍 Discovering test files for safe deletion...")
        
        for pattern in self.safe_test_patterns:
            file_path = self.root_dir / pattern
            if file_path.exists():
                self.test_scripts.append(file_path)
        
        print(f"✅ Found {len(self.test_scripts)} test scripts for potential deletion")
        return self.test_scripts
    
    def analyze_dependencies(self):
        """Analyze if any test scripts are imported by the main system"""
        print("🔗 Analyzing dependencies...")
        
        # Check if any test scripts are imported in the main codebase
        main_apps = ['accounts', 'patients', 'doctors', 'appointments', 'pharmacy', 
                    'laboratory', 'billing', 'inpatient', 'hr', 'consultations',
                    'radiology', 'theatre', 'nhia', 'retainership', 'reporting', 'core', 'dashboard']
        
        dependencies_found = []
        
        for app in main_apps:
            app_path = Path(app)
            if app_path.exists():
                for py_file in app_path.rglob("*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Check for imports of test scripts
                        for script in self.test_scripts:
                            script_name = script.stem  # filename without extension
                            if f"import {script_name}" in content or f"from {script_name}" in content:
                                dependencies_found.append({
                                    'file': str(py_file),
                                    'imports': script_name
                                })
                    except Exception:
                        continue
        
        if dependencies_found:
            self.log_deletion_result("Dependency-Analysis", "ANALYSIS", "WARN", 
                                   f"Found {len(dependencies_found)} dependencies", 
                                   details=dependencies_found)
            return False
        else:
            self.log_deletion_result("Dependency-Analysis", "ANALYSIS", "PASS", 
                                   "No dependencies found in main codebase")
            return True
    
    def create_backup(self):
        """Create backup of test files before deletion"""
        print("💾 Creating backup of test files...")
        
        try:
            # Create backup directory
            self.backup_dir.mkdir(exist_ok=True)
            
            # Create timestamped backup subdirectory
            timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_subdir = self.backup_dir / f"test_deletion_backup_{timestamp}"
            backup_subdir.mkdir(exist_ok=True)
            
            # Backup test scripts
            for script in self.test_scripts:
                if script.exists():
                    shutil.copy2(script, backup_subdir / script.name)
            
            # Create backup manifest
            manifest = {
                'backup_timestamp': timestamp,
                'scripts_backed_up': [str(s) for s in self.test_scripts if s.exists()],
                'backup_location': str(backup_subdir)
            }
            
            with open(backup_subdir / 'deletion_backup_manifest.json', 'w') as f:
                json.dump(manifest, f, indent=2)
            
            self.log_deletion_result("Backup-Creation", "BACKUP", "PASS", 
                                   f"Backup created at {backup_subdir}")
            
            return backup_subdir
            
        except Exception as e:
            self.log_deletion_result("Backup-Creation", "BACKUP", "FAIL", 
                                   "Failed to create backup", e)
            return None
    
    def check_file_safety(self, file_path):
        """Check if a file is safe to delete"""
        
        # Check if file is in preserve list
        if file_path.name in self.preserve_patterns:
            return False, "File is in preserve list"
        
        # Check if file is a Django app test file (these should be preserved)
        if '/tests/' in str(file_path) or file_path.parent.name == 'tests':
            return False, "Django app test file should be preserved"
        
        # Check if file contains important Django test classes
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for Django TestCase classes
            if 'class ' in content and 'TestCase' in content:
                return False, "Contains Django TestCase classes"
            
            # Look for important imports that suggest it's part of the main system
            important_imports = [
                'from django.test import TestCase',
                'from django.test import TransactionTestCase',
                'from rest_framework.test import APITestCase'
            ]
            
            for imp in important_imports:
                if imp in content:
                    return False, "Contains important Django test imports"
        
        except Exception:
            pass
        
        return True, "Safe to delete"
    
    def delete_test_scripts(self):
        """Delete test scripts safely"""
        print("🗑️  Deleting test scripts...")
        
        deleted_scripts = []
        skipped_scripts = []
        failed_deletions = []
        
        for script in self.test_scripts:
            try:
                if not script.exists():
                    continue
                
                # Check if file is safe to delete
                is_safe, reason = self.check_file_safety(script)
                
                if not is_safe:
                    skipped_scripts.append((script, reason))
                    self.log_deletion_result(f"Skip-{script.name}", "SKIP", "SKIP", 
                                           f"Skipped: {reason}")
                    continue
                
                # Delete the file
                script.unlink()
                deleted_scripts.append(script)
                self.log_deletion_result(f"Delete-{script.name}", "DELETE", "PASS", 
                                       "Test script deleted successfully")
                
            except Exception as e:
                failed_deletions.append((script, e))
                self.log_deletion_result(f"Delete-{script.name}", "DELETE", "FAIL", 
                                       "Failed to delete test script", e)
        
        return deleted_scripts, skipped_scripts, failed_deletions
    
    def verify_system_integrity(self):
        """Verify that the main system is still functional after deletion"""
        print("✅ Verifying system integrity...")
        
        try:
            # Test Django setup
            from django.conf import settings
            self.log_deletion_result("Django-Setup", "VERIFICATION", "PASS", 
                                   "Django configuration intact")
            
            # Test model imports
            from accounts.models import CustomUser
            from patients.models import Patient
            from pharmacy.models import Medication
            self.log_deletion_result("Model-Imports", "VERIFICATION", "PASS", 
                                   "Core models importable")
            
            # Test basic database operations
            user_count = CustomUser.objects.count()
            patient_count = Patient.objects.count()
            self.log_deletion_result("Database-Operations", "VERIFICATION", "PASS", 
                                   f"Database accessible (Users: {user_count}, Patients: {patient_count})")
            
            # Test URL configuration
            from django.urls import reverse
            try:
                login_url = reverse('accounts:login')
                self.log_deletion_result("URL-Configuration", "VERIFICATION", "PASS", 
                                       "URL routing functional")
            except Exception as e:
                self.log_deletion_result("URL-Configuration", "VERIFICATION", "WARN", 
                                       "Some URL issues detected", e)
            
        except Exception as e:
            self.log_deletion_result("System-Verification", "VERIFICATION", "FAIL", 
                                   "System integrity verification failed", e)
    
    def log_deletion_result(self, operation, category, status, message="", error=None, details=None):
        """Log deletion results"""
        result = {
            'operation': operation,
            'category': category,
            'status': status,
            'message': message,
            'error': str(error) if error else None,
            'details': details,
            'timestamp': dt.datetime.now().isoformat()
        }
        self.deletion_results.append(result)
        
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️" if status == "WARN" else "⏭️"
        print(f"{status_symbol} {operation} ({category}): {status}")
        if message:
            print(f"   📝 {message}")
        if error:
            print(f"   🔥 Error: {error}")
    
    def run_safe_deletion(self):
        """Run the complete safe deletion process"""
        print("\n" + "="*80)
        print("🎯 SAFE TEST SCRIPT DELETION - HMS")
        print("="*80)
        
        # Step 1: Discover test files
        self.discover_test_files()
        
        # Step 2: Analyze dependencies
        dependencies_safe = self.analyze_dependencies()
        
        if not dependencies_safe:
            print("⚠️  Dependencies found. Aborting deletion for safety.")
            return
        
        # Step 3: Create backup
        backup_location = self.create_backup()
        
        if not backup_location:
            print("❌ Backup failed. Aborting deletion for safety.")
            return
        
        # Step 4: Delete test scripts
        deleted_scripts, skipped_scripts, failed_deletions = self.delete_test_scripts()
        
        # Step 5: Verify system integrity
        self.verify_system_integrity()
        
        # Generate final report
        self.generate_deletion_report(backup_location, deleted_scripts, skipped_scripts, failed_deletions)
    
    def generate_deletion_report(self, backup_location, deleted_scripts, skipped_scripts, failed_deletions):
        """Generate deletion report"""
        print("\n" + "="*80)
        print("📋 SAFE TEST SCRIPT DELETION REPORT")
        print("="*80)
        
        total_operations = len(self.deletion_results)
        passed = len([r for r in self.deletion_results if r['status'] == 'PASS'])
        failed = len([r for r in self.deletion_results if r['status'] == 'FAIL'])
        warnings = len([r for r in self.deletion_results if r['status'] == 'WARN'])
        skipped = len([r for r in self.deletion_results if r['status'] == 'SKIP'])
        
        print(f"📊 Total Operations: {total_operations}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"⏭️  Skipped: {skipped}")
        print(f"📈 Success Rate: {(passed/total_operations*100):.1f}%" if total_operations > 0 else "N/A")
        
        print(f"\n📁 Backup Location: {backup_location}")
        print(f"🗑️  Deleted Scripts: {len(deleted_scripts)}")
        print(f"⏭️  Skipped Scripts: {len(skipped_scripts)}")
        
        if failed_deletions:
            print(f"❌ Failed Deletions: {len(failed_deletions)}")
        
        # List deleted files
        if deleted_scripts:
            print(f"\n🗑️  Successfully Deleted Files:")
            for script in deleted_scripts:
                print(f"   • {script.name}")
        
        # List skipped files
        if skipped_scripts:
            print(f"\n⏭️  Skipped Files:")
            for script, reason in skipped_scripts:
                print(f"   • {script.name} - {reason}")
        
        # Save detailed report
        deletion_summary = {
            'summary': {
                'total_operations': total_operations,
                'passed': passed,
                'failed': failed,
                'warnings': warnings,
                'skipped': skipped,
                'success_rate': (passed/total_operations*100) if total_operations > 0 else 0
            },
            'backup_location': str(backup_location) if backup_location else None,
            'deleted_scripts': [str(s) for s in deleted_scripts],
            'skipped_scripts': [(str(s), reason) for s, reason in skipped_scripts],
            'failed_deletions': [(str(s), str(e)) for s, e in failed_deletions],
            'operations': self.deletion_results
        }
        
        with open('safe_test_deletion_report.json', 'w') as f:
            json.dump(deletion_summary, f, indent=2)
        
        print(f"\n📄 Detailed deletion report saved to: safe_test_deletion_report.json")

if __name__ == "__main__":
    deletion = SafeTestScriptDeletion()
    deletion.run_safe_deletion()
