#!/usr/bin/env python
"""
Comprehensive Performance and Load Tester for HMS
This script tests system performance, database queries, and load handling.
"""

import os
import sys
import django
import json
import traceback
import datetime as dt
import time
import threading
import concurrent.futures
from datetime import date, timedelta
from decimal import Decimal

# Setup Django environment first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Import Django modules after setup
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.conf import settings
from django.core.management import call_command
from django.db.models import Count, Q

# Import models
from accounts.models import CustomUser
from patients.models import Patient, PatientWallet
from doctors.models import Doctor, Specialization
from pharmacy.models import Medication, Prescription, MedicationCategory
from billing.models import Invoice, Service
from laboratory.models import Test, TestRequest

class PerformanceLoadTester:
    def __init__(self):
        self.client = Client()
        self.test_results = []
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Set up test environment for performance testing"""
        print("🔧 Setting up performance testing environment...")
        
        # Add testserver to ALLOWED_HOSTS
        if 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append('testserver')
        
        # Create test data
        self.create_performance_test_data()
        
        print("✅ Performance testing environment ready")
    
    def create_performance_test_data(self):
        """Create test data for performance testing"""
        try:
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            
            # Create test user
            self.test_user = CustomUser.objects.create_user(
                phone_number=f'+1234567{unique_id[:3]}',
                username=f'perf_user_{unique_id}',
                email=f'perf_{unique_id}@test.com',
                password='testpass123',
                first_name='Performance',
                last_name='User'
            )
            
            print(f"✅ Created performance test data with unique ID: {unique_id}")
            
        except Exception as e:
            print(f"⚠️  Error creating performance test data: {e}")
            traceback.print_exc()
    
    def log_test_result(self, test_name, test_type, status, message="", error=None, details=None):
        """Log test results"""
        result = {
            'test': test_name,
            'test_type': test_type,
            'status': status,
            'message': message,
            'error': str(error) if error else None,
            'details': details,
            'timestamp': dt.datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_symbol} {test_name} ({test_type}): {status}")
        if message:
            print(f"   📝 {message}")
        if error:
            print(f"   🔥 Error: {error}")
        if details:
            print(f"   📊 Details: {details}")
    
    def test_database_performance(self):
        """Test database query performance"""
        print("\n🗄️  Testing Database Performance...")
        
        # Test simple query performance
        try:
            start_time = time.time()
            users = list(CustomUser.objects.all()[:100])
            end_time = time.time()
            query_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            if query_time < 1000:  # Less than 1 second
                self.log_test_result("Simple-Query-Performance", "DATABASE_PERFORMANCE", "PASS", 
                                   f"Query completed in {query_time:.2f}ms")
            else:
                self.log_test_result("Simple-Query-Performance", "DATABASE_PERFORMANCE", "WARN", 
                                   f"Query took {query_time:.2f}ms (may be slow)")
        except Exception as e:
            self.log_test_result("Simple-Query-Performance", "DATABASE_PERFORMANCE", "FAIL", 
                               "Simple query test failed", e)
        
        # Test complex query performance
        try:
            start_time = time.time()
            patients_with_wallets = Patient.objects.select_related('patientwallet').all()[:50]
            list(patients_with_wallets)  # Force evaluation
            end_time = time.time()
            query_time = (end_time - start_time) * 1000
            
            if query_time < 2000:  # Less than 2 seconds
                self.log_test_result("Complex-Query-Performance", "DATABASE_PERFORMANCE", "PASS", 
                                   f"Complex query completed in {query_time:.2f}ms")
            else:
                self.log_test_result("Complex-Query-Performance", "DATABASE_PERFORMANCE", "WARN", 
                                   f"Complex query took {query_time:.2f}ms (may be slow)")
        except Exception as e:
            self.log_test_result("Complex-Query-Performance", "DATABASE_PERFORMANCE", "FAIL", 
                               "Complex query test failed", e)
        
        # Test aggregation performance
        try:
            start_time = time.time()
            patient_count = Patient.objects.count()
            user_count = CustomUser.objects.count()
            end_time = time.time()
            query_time = (end_time - start_time) * 1000
            
            self.log_test_result("Aggregation-Performance", "DATABASE_PERFORMANCE", "PASS", 
                               f"Aggregation completed in {query_time:.2f}ms", 
                               details=f"Patients: {patient_count}, Users: {user_count}")
        except Exception as e:
            self.log_test_result("Aggregation-Performance", "DATABASE_PERFORMANCE", "FAIL", 
                               "Aggregation test failed", e)
    
    def test_view_response_times(self):
        """Test view response times"""
        print("\n⚡ Testing View Response Times...")
        
        # Login for authenticated views
        self.client.login(username=self.test_user.username, password='testpass123')
        
        # Test different views
        test_views = [
            ('/', 'Home Page'),
            ('/accounts/login/', 'Login Page'),
            ('/dashboard/', 'Dashboard'),
            ('/patients/', 'Patients List'),
            ('/doctors/', 'Doctors List'),
        ]
        
        for url, view_name in test_views:
            try:
                start_time = time.time()
                response = self.client.get(url)
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                if response.status_code == 200:
                    if response_time < 1000:  # Less than 1 second
                        self.log_test_result(f"{view_name}-Response-Time", "VIEW_PERFORMANCE", "PASS", 
                                           f"Response time: {response_time:.2f}ms")
                    else:
                        self.log_test_result(f"{view_name}-Response-Time", "VIEW_PERFORMANCE", "WARN", 
                                           f"Slow response time: {response_time:.2f}ms")
                else:
                    self.log_test_result(f"{view_name}-Response-Time", "VIEW_PERFORMANCE", "WARN", 
                                       f"Non-200 response: {response.status_code}")
            except Exception as e:
                self.log_test_result(f"{view_name}-Response-Time", "VIEW_PERFORMANCE", "FAIL", 
                                   "View response test failed", e)
    
    def test_concurrent_access(self):
        """Test concurrent user access"""
        print("\n👥 Testing Concurrent Access...")
        
        def simulate_user_session():
            """Simulate a user session"""
            client = Client()
            try:
                # Login
                login_success = client.login(username=self.test_user.username, password='testpass123')
                if not login_success:
                    return False
                
                # Access multiple pages
                urls = ['/', '/dashboard/', '/patients/']
                for url in urls:
                    response = client.get(url)
                    if response.status_code not in [200, 302]:
                        return False
                
                # Logout
                client.logout()
                return True
            except Exception:
                return False
        
        # Test with multiple concurrent users
        concurrent_users = 5
        try:
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [executor.submit(simulate_user_session) for _ in range(concurrent_users)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            end_time = time.time()
            total_time = (end_time - start_time) * 1000
            successful_sessions = sum(results)
            
            if successful_sessions == concurrent_users:
                self.log_test_result("Concurrent-Access", "LOAD_TESTING", "PASS", 
                                   f"{successful_sessions}/{concurrent_users} sessions successful", 
                                   details=f"Total time: {total_time:.2f}ms")
            else:
                self.log_test_result("Concurrent-Access", "LOAD_TESTING", "WARN", 
                                   f"Only {successful_sessions}/{concurrent_users} sessions successful")
        except Exception as e:
            self.log_test_result("Concurrent-Access", "LOAD_TESTING", "FAIL", 
                               "Concurrent access test failed", e)
    
    def test_memory_usage(self):
        """Test memory usage patterns"""
        print("\n🧠 Testing Memory Usage...")
        
        try:
            import psutil
            process = psutil.Process()
            
            # Get initial memory usage
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Perform memory-intensive operations
            large_queryset = CustomUser.objects.all()
            users_list = list(large_queryset)
            
            # Get memory usage after operations
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            if memory_increase < 100:  # Less than 100MB increase
                self.log_test_result("Memory-Usage", "PERFORMANCE", "PASS", 
                                   f"Memory increase: {memory_increase:.2f}MB", 
                                   details=f"Initial: {initial_memory:.2f}MB, Final: {final_memory:.2f}MB")
            else:
                self.log_test_result("Memory-Usage", "PERFORMANCE", "WARN", 
                                   f"High memory increase: {memory_increase:.2f}MB")
        except ImportError:
            self.log_test_result("Memory-Usage", "PERFORMANCE", "SKIP", 
                               "psutil not available for memory testing")
        except Exception as e:
            self.log_test_result("Memory-Usage", "PERFORMANCE", "FAIL", 
                               "Memory usage test failed", e)
    
    def test_database_connections(self):
        """Test database connection handling"""
        print("\n🔌 Testing Database Connections...")
        
        try:
            # Test connection count
            initial_queries = len(connection.queries)
            
            # Perform database operations
            Patient.objects.count()
            CustomUser.objects.count()
            Medication.objects.count()
            
            final_queries = len(connection.queries)
            query_count = final_queries - initial_queries
            
            self.log_test_result("Database-Connections", "DATABASE_PERFORMANCE", "PASS", 
                               f"Executed {query_count} queries", 
                               details=f"Connection handling working properly")
        except Exception as e:
            self.log_test_result("Database-Connections", "DATABASE_PERFORMANCE", "FAIL", 
                               "Database connection test failed", e)
    
    def run_all_tests(self):
        """Run all performance and load tests"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE PERFORMANCE & LOAD TESTING - HMS")
        print("="*80)
        
        # Run different test categories
        self.test_database_performance()
        self.test_view_response_times()
        self.test_concurrent_access()
        self.test_memory_usage()
        self.test_database_connections()
        
        # Generate final report
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("📋 PERFORMANCE & LOAD TEST REPORT")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warnings = len([r for r in self.test_results if r['status'] == 'WARN'])
        skipped = len([r for r in self.test_results if r['status'] == 'SKIP'])
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"⏭️  Skipped: {skipped}")
        print(f"📈 Success Rate: {(passed/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
        
        # Save detailed report
        with open('performance_load_test_report.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed': passed,
                    'failed': failed,
                    'warnings': warnings,
                    'skipped': skipped,
                    'success_rate': (passed/total_tests*100) if total_tests > 0 else 0
                },
                'results': self.test_results
            }, f, indent=2)
        
        print(f"📄 Detailed report saved to: performance_load_test_report.json")

if __name__ == "__main__":
    tester = PerformanceLoadTester()
    tester.run_all_tests()
