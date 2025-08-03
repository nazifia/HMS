#!/usr/bin/env python
"""
Test Script Cleanup for HMS
This script cleans up test scripts while maintaining system functionality.
"""

import os
import sys
import django
import json
import shutil
import traceback
import datetime as dt
from pathlib import Path

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

class TestScriptCleanup:
    def __init__(self):
        self.cleanup_results = []
        self.root_dir = Path('.')
        self.test_scripts = []
        self.test_reports = []
        self.backup_dir = Path('test_backups')
        
    def discover_test_files(self):
        """Discover all test-related files"""
        print("🔍 Discovering test files...")
        
        # Test scripts to clean up
        test_script_patterns = [
            'function_discovery.py',
            'comprehensive_function_tester.py',
            'view_url_tester.py',
            'api_integration_tester.py',
            'business_workflow_tester.py',
            'comprehensive_form_validator.py',
            'security_permission_tester.py',
            'performance_load_tester.py',
            'comprehensive_testing_summary.py'
        ]
        
        # Test reports to clean up
        test_report_patterns = [
            'function_discovery_report.json',
            'comprehensive_test_report.json',
            'view_url_test_report.json',
            'api_integration_test_report.json',
            'business_workflow_test_report.json',
            'form_validation_test_report.json',
            'security_permission_test_report.json',
            'performance_load_test_report.json',
            'final_comprehensive_test_report.json'
        ]
        
        # Find existing test scripts
        for pattern in test_script_patterns:
            file_path = self.root_dir / pattern
            if file_path.exists():
                self.test_scripts.append(file_path)
        
        # Find existing test reports
        for pattern in test_report_patterns:
            file_path = self.root_dir / pattern
            if file_path.exists():
                self.test_reports.append(file_path)
        
        print(f"✅ Found {len(self.test_scripts)} test scripts and {len(self.test_reports)} test reports")
    
    def create_backup(self):
        """Create backup of test files before cleanup"""
        print("💾 Creating backup of test files...")
        
        try:
            # Create backup directory
            self.backup_dir.mkdir(exist_ok=True)
            
            # Create timestamped backup subdirectory
            timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_subdir = self.backup_dir / f"test_backup_{timestamp}"
            backup_subdir.mkdir(exist_ok=True)
            
            # Backup test scripts
            scripts_backup = backup_subdir / "scripts"
            scripts_backup.mkdir(exist_ok=True)
            
            for script in self.test_scripts:
                shutil.copy2(script, scripts_backup / script.name)
            
            # Backup test reports
            reports_backup = backup_subdir / "reports"
            reports_backup.mkdir(exist_ok=True)
            
            for report in self.test_reports:
                shutil.copy2(report, reports_backup / report.name)
            
            # Create backup manifest
            manifest = {
                'backup_timestamp': timestamp,
                'scripts_backed_up': [str(s) for s in self.test_scripts],
                'reports_backed_up': [str(r) for r in self.test_reports],
                'backup_location': str(backup_subdir)
            }
            
            with open(backup_subdir / 'backup_manifest.json', 'w') as f:
                json.dump(manifest, f, indent=2)
            
            self.log_cleanup_result("Backup-Creation", "BACKUP", "PASS", 
                                  f"Backup created at {backup_subdir}")
            
            return backup_subdir
            
        except Exception as e:
            self.log_cleanup_result("Backup-Creation", "BACKUP", "FAIL", 
                                  "Failed to create backup", e)
            return None
    
    def analyze_dependencies(self):
        """Analyze if any test scripts are imported by the main system"""
        print("🔗 Analyzing dependencies...")
        
        # Check if any test scripts are imported in the main codebase
        main_apps = ['accounts', 'patients', 'doctors', 'appointments', 'pharmacy', 
                    'laboratory', 'billing', 'inpatient', 'hr', 'consultations',
                    'radiology', 'theatre', 'nhia', 'retainership', 'reporting', 'core']
        
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
            self.log_cleanup_result("Dependency-Analysis", "ANALYSIS", "WARN", 
                                  f"Found {len(dependencies_found)} dependencies", 
                                  details=dependencies_found)
        else:
            self.log_cleanup_result("Dependency-Analysis", "ANALYSIS", "PASS", 
                                  "No dependencies found in main codebase")
        
        return dependencies_found
    
    def preserve_essential_files(self):
        """Identify and preserve essential files that should not be deleted"""
        print("🛡️  Identifying essential files to preserve...")
        
        # Files that should be preserved (not test-related but might be confused)
        essential_patterns = [
            'manage.py',
            'requirements.txt',
            'user_isolation_middleware.py',
            'user_isolation_examples.py',
            'test_script_cleanup.py'  # This script itself
        ]
        
        preserved_files = []
        
        for pattern in essential_patterns:
            file_path = self.root_dir / pattern
            if file_path.exists():
                preserved_files.append(file_path)
        
        # Remove preserved files from cleanup lists
        self.test_scripts = [s for s in self.test_scripts if s not in preserved_files]
        
        self.log_cleanup_result("Essential-Files-Preservation", "PRESERVATION", "PASS", 
                              f"Preserved {len(preserved_files)} essential files")
        
        return preserved_files
    
    def clean_test_scripts(self):
        """Clean up test scripts"""
        print("🧹 Cleaning up test scripts...")
        
        cleaned_scripts = []
        failed_cleanups = []
        
        for script in self.test_scripts:
            try:
                script.unlink()  # Delete the file
                cleaned_scripts.append(script)
                self.log_cleanup_result(f"Clean-{script.name}", "CLEANUP", "PASS", 
                                      "Test script removed successfully")
            except Exception as e:
                failed_cleanups.append((script, e))
                self.log_cleanup_result(f"Clean-{script.name}", "CLEANUP", "FAIL", 
                                      "Failed to remove test script", e)
        
        return cleaned_scripts, failed_cleanups
    
    def clean_test_reports(self):
        """Clean up test reports"""
        print("📄 Cleaning up test reports...")
        
        cleaned_reports = []
        failed_cleanups = []
        
        for report in self.test_reports:
            try:
                report.unlink()  # Delete the file
                cleaned_reports.append(report)
                self.log_cleanup_result(f"Clean-{report.name}", "CLEANUP", "PASS", 
                                      "Test report removed successfully")
            except Exception as e:
                failed_cleanups.append((report, e))
                self.log_cleanup_result(f"Clean-{report.name}", "CLEANUP", "FAIL", 
                                      "Failed to remove test report", e)
        
        return cleaned_reports, failed_cleanups
    
    def verify_system_functionality(self):
        """Verify that the main system functionality is still intact"""
        print("✅ Verifying system functionality...")
        
        try:
            # Test Django setup
            from django.conf import settings
            self.log_cleanup_result("Django-Setup", "VERIFICATION", "PASS", 
                                  "Django configuration intact")
            
            # Test model imports
            from accounts.models import CustomUser
            from patients.models import Patient
            from pharmacy.models import Medication
            self.log_cleanup_result("Model-Imports", "VERIFICATION", "PASS", 
                                  "Core models importable")
            
            # Test basic database operations
            user_count = CustomUser.objects.count()
            patient_count = Patient.objects.count()
            self.log_cleanup_result("Database-Operations", "VERIFICATION", "PASS", 
                                  f"Database accessible (Users: {user_count}, Patients: {patient_count})")
            
            # Test URL configuration
            from django.urls import reverse
            try:
                login_url = reverse('accounts:login')
                self.log_cleanup_result("URL-Configuration", "VERIFICATION", "PASS", 
                                      "URL routing functional")
            except Exception as e:
                self.log_cleanup_result("URL-Configuration", "VERIFICATION", "WARN", 
                                      "Some URL issues detected", e)
            
        except Exception as e:
            self.log_cleanup_result("System-Verification", "VERIFICATION", "FAIL", 
                                  "System functionality verification failed", e)
    
    def log_cleanup_result(self, operation, category, status, message="", error=None, details=None):
        """Log cleanup results"""
        result = {
            'operation': operation,
            'category': category,
            'status': status,
            'message': message,
            'error': str(error) if error else None,
            'details': details,
            'timestamp': dt.datetime.now().isoformat()
        }
        self.cleanup_results.append(result)
        
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_symbol} {operation} ({category}): {status}")
        if message:
            print(f"   📝 {message}")
        if error:
            print(f"   🔥 Error: {error}")
    
    def run_cleanup(self):
        """Run the complete cleanup process"""
        print("\n" + "="*80)
        print("🎯 TEST SCRIPT CLEANUP - HMS")
        print("="*80)
        
        # Step 1: Discover test files
        self.discover_test_files()
        
        # Step 2: Create backup
        backup_location = self.create_backup()
        
        # Step 3: Analyze dependencies
        dependencies = self.analyze_dependencies()
        
        # Step 4: Preserve essential files
        preserved_files = self.preserve_essential_files()
        
        # Step 5: Clean test scripts
        cleaned_scripts, failed_script_cleanups = self.clean_test_scripts()
        
        # Step 6: Clean test reports
        cleaned_reports, failed_report_cleanups = self.clean_test_reports()
        
        # Step 7: Verify system functionality
        self.verify_system_functionality()
        
        # Generate final report
        self.generate_cleanup_report(backup_location, dependencies, preserved_files, 
                                   cleaned_scripts, cleaned_reports, 
                                   failed_script_cleanups, failed_report_cleanups)
    
    def generate_cleanup_report(self, backup_location, dependencies, preserved_files, 
                              cleaned_scripts, cleaned_reports, failed_script_cleanups, 
                              failed_report_cleanups):
        """Generate comprehensive cleanup report"""
        print("\n" + "="*80)
        print("📋 TEST SCRIPT CLEANUP REPORT")
        print("="*80)
        
        total_operations = len(self.cleanup_results)
        passed = len([r for r in self.cleanup_results if r['status'] == 'PASS'])
        failed = len([r for r in self.cleanup_results if r['status'] == 'FAIL'])
        warnings = len([r for r in self.cleanup_results if r['status'] == 'WARN'])
        
        print(f"📊 Total Operations: {total_operations}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"📈 Success Rate: {(passed/total_operations*100):.1f}%" if total_operations > 0 else "N/A")
        
        print(f"\n📁 Backup Location: {backup_location}")
        print(f"🧹 Cleaned Scripts: {len(cleaned_scripts)}")
        print(f"📄 Cleaned Reports: {len(cleaned_reports)}")
        print(f"🛡️  Preserved Files: {len(preserved_files)}")
        
        if failed_script_cleanups or failed_report_cleanups:
            print(f"⚠️  Failed Cleanups: {len(failed_script_cleanups + failed_report_cleanups)}")
        
        # Save detailed report
        cleanup_summary = {
            'summary': {
                'total_operations': total_operations,
                'passed': passed,
                'failed': failed,
                'warnings': warnings,
                'success_rate': (passed/total_operations*100) if total_operations > 0 else 0
            },
            'backup_location': str(backup_location) if backup_location else None,
            'cleaned_scripts': [str(s) for s in cleaned_scripts],
            'cleaned_reports': [str(r) for r in cleaned_reports],
            'preserved_files': [str(f) for f in preserved_files],
            'dependencies_found': dependencies,
            'failed_cleanups': {
                'scripts': [(str(s), str(e)) for s, e in failed_script_cleanups],
                'reports': [(str(r), str(e)) for r, e in failed_report_cleanups]
            },
            'operations': self.cleanup_results
        }
        
        with open('test_cleanup_report.json', 'w') as f:
            json.dump(cleanup_summary, f, indent=2)
        
        print(f"📄 Detailed cleanup report saved to: test_cleanup_report.json")

if __name__ == "__main__":
    cleanup = TestScriptCleanup()
    cleanup.run_cleanup()
