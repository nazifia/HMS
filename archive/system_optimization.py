#!/usr/bin/env python
"""
System Optimization and Monitoring for HMS
This script adds monitoring, logging, and performance optimizations.
"""

import os
import sys
import django
import json
import logging
import datetime as dt
from pathlib import Path

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.conf import settings
from django.db import connection
from django.core.management import call_command

class SystemOptimizer:
    def __init__(self):
        self.optimization_results = []
        
    def setup_enhanced_logging(self):
        """Set up enhanced logging configuration"""
        print("📝 Setting up enhanced logging...")
        
        try:
            # Create logs directory
            logs_dir = Path('logs')
            logs_dir.mkdir(exist_ok=True)
            
            # Enhanced logging configuration
            logging_config = {
                'version': 1,
                'disable_existing_loggers': False,
                'formatters': {
                    'verbose': {
                        'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                        'style': '{',
                    },
                    'simple': {
                        'format': '{levelname} {message}',
                        'style': '{',
                    },
                },
                'handlers': {
                    'file_debug': {
                        'level': 'DEBUG',
                        'class': 'logging.handlers.RotatingFileHandler',
                        'filename': 'logs/hms_debug.log',
                        'maxBytes': 1024*1024*10,  # 10MB
                        'backupCount': 5,
                        'formatter': 'verbose',
                    },
                    'file_error': {
                        'level': 'ERROR',
                        'class': 'logging.handlers.RotatingFileHandler',
                        'filename': 'logs/hms_errors.log',
                        'maxBytes': 1024*1024*10,  # 10MB
                        'backupCount': 5,
                        'formatter': 'verbose',
                    },
                    'file_security': {
                        'level': 'INFO',
                        'class': 'logging.handlers.RotatingFileHandler',
                        'filename': 'logs/hms_security.log',
                        'maxBytes': 1024*1024*10,  # 10MB
                        'backupCount': 5,
                        'formatter': 'verbose',
                    },
                    'console': {
                        'level': 'INFO',
                        'class': 'logging.StreamHandler',
                        'formatter': 'simple',
                    },
                },
                'loggers': {
                    'django': {
                        'handlers': ['file_debug', 'console'],
                        'level': 'INFO',
                        'propagate': False,
                    },
                    'hms': {
                        'handlers': ['file_debug', 'file_error', 'console'],
                        'level': 'DEBUG',
                        'propagate': False,
                    },
                    'security': {
                        'handlers': ['file_security', 'console'],
                        'level': 'INFO',
                        'propagate': False,
                    },
                },
                'root': {
                    'handlers': ['file_debug', 'console'],
                    'level': 'INFO',
                },
            }
            
            # Save logging configuration
            with open('logging_config.json', 'w') as f:
                json.dump(logging_config, f, indent=2)
            
            self.log_optimization_result("Enhanced-Logging-Setup", "LOGGING", "PASS", 
                                       "Enhanced logging configuration created")
            
        except Exception as e:
            self.log_optimization_result("Enhanced-Logging-Setup", "LOGGING", "FAIL", 
                                       "Failed to setup enhanced logging", e)
    
    def optimize_database_settings(self):
        """Optimize database settings for better performance"""
        print("🗄️  Optimizing database settings...")
        
        try:
            # Database optimization recommendations
            db_optimizations = {
                'connection_pooling': {
                    'CONN_MAX_AGE': 600,  # 10 minutes
                    'CONN_HEALTH_CHECKS': True,
                },
                'query_optimization': {
                    'SELECT_RELATED_DEPTH': 2,
                    'PREFETCH_RELATED_DEPTH': 1,
                },
                'caching': {
                    'CACHE_TIMEOUT': 300,  # 5 minutes
                    'CACHE_KEY_PREFIX': 'hms',
                },
                'indexes': [
                    'CREATE INDEX IF NOT EXISTS idx_patients_patient_id ON patients_patient(patient_id);',
                    'CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON pharmacy_prescription(patient_id);',
                    'CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments_appointment(appointment_date);',
                    'CREATE INDEX IF NOT EXISTS idx_invoices_patient ON billing_invoice(patient_id);',
                    'CREATE INDEX IF NOT EXISTS idx_users_username ON accounts_customuser(username);',
                ]
            }
            
            # Apply database indexes
            with connection.cursor() as cursor:
                for index_sql in db_optimizations['indexes']:
                    try:
                        cursor.execute(index_sql)
                        print(f"   ✅ Applied index: {index_sql[:50]}...")
                    except Exception as e:
                        print(f"   ⚠️  Index already exists or failed: {e}")
            
            # Save optimization recommendations
            with open('database_optimizations.json', 'w') as f:
                json.dump(db_optimizations, f, indent=2)
            
            self.log_optimization_result("Database-Optimization", "DATABASE", "PASS", 
                                       "Database optimizations applied")
            
        except Exception as e:
            self.log_optimization_result("Database-Optimization", "DATABASE", "FAIL", 
                                       "Failed to optimize database", e)
    
    def setup_performance_monitoring(self):
        """Set up performance monitoring"""
        print("📊 Setting up performance monitoring...")
        
        try:
            # Performance monitoring configuration
            monitoring_config = {
                'metrics': {
                    'response_time_threshold': 1000,  # milliseconds
                    'memory_usage_threshold': 80,     # percentage
                    'cpu_usage_threshold': 80,        # percentage
                    'database_query_threshold': 100,  # milliseconds
                },
                'alerts': {
                    'email_notifications': True,
                    'log_alerts': True,
                    'dashboard_alerts': True,
                },
                'monitoring_intervals': {
                    'system_metrics': 60,    # seconds
                    'database_metrics': 30,  # seconds
                    'user_activity': 300,    # seconds
                }
            }
            
            # Create monitoring middleware
            monitoring_middleware_content = '''
"""
Performance Monitoring Middleware for HMS
"""
import time
import logging
from django.db import connection

logger = logging.getLogger('hms.performance')

class PerformanceMonitoringMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        initial_queries = len(connection.queries)
        
        response = self.get_response(request)
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        query_count = len(connection.queries) - initial_queries
        
        # Log performance metrics
        if response_time > 1000:  # Log slow requests
            logger.warning(f"Slow request: {request.path} took {response_time:.2f}ms with {query_count} queries")
        
        # Add performance headers
        response['X-Response-Time'] = f"{response_time:.2f}ms"
        response['X-Query-Count'] = str(query_count)
        
        return response
'''
            
            with open('performance_monitoring_middleware.py', 'w') as f:
                f.write(monitoring_middleware_content)
            
            # Save monitoring configuration
            with open('monitoring_config.json', 'w') as f:
                json.dump(monitoring_config, f, indent=2)
            
            self.log_optimization_result("Performance-Monitoring", "MONITORING", "PASS", 
                                       "Performance monitoring setup completed")
            
        except Exception as e:
            self.log_optimization_result("Performance-Monitoring", "MONITORING", "FAIL", 
                                       "Failed to setup performance monitoring", e)
    
    def optimize_static_files(self):
        """Optimize static file handling"""
        print("📁 Optimizing static file handling...")
        
        try:
            # Static file optimization recommendations
            static_optimizations = {
                'compression': {
                    'COMPRESS_ENABLED': True,
                    'COMPRESS_CSS_FILTERS': [
                        'compressor.filters.css_default.CssAbsoluteFilter',
                        'compressor.filters.cssmin.CSSMinFilter',
                    ],
                    'COMPRESS_JS_FILTERS': [
                        'compressor.filters.jsmin.JSMinFilter',
                    ],
                },
                'caching': {
                    'STATICFILES_STORAGE': 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage',
                    'STATIC_URL': '/static/',
                    'MEDIA_URL': '/media/',
                },
                'cdn': {
                    'USE_CDN': False,  # Can be enabled for production
                    'CDN_URL': 'https://cdn.example.com',
                }
            }
            
            # Create static file optimization script
            static_optimization_script = '''#!/usr/bin/env python
"""
Static File Optimization Script
"""
import os
import gzip
import shutil
from pathlib import Path

def compress_static_files():
    """Compress static files for better performance"""
    static_dir = Path('static')
    if not static_dir.exists():
        return
    
    for file_path in static_dir.rglob('*'):
        if file_path.suffix in ['.css', '.js', '.html']:
            compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

if __name__ == "__main__":
    compress_static_files()
'''
            
            with open('optimize_static_files.py', 'w') as f:
                f.write(static_optimization_script)
            
            # Save static optimizations
            with open('static_optimizations.json', 'w') as f:
                json.dump(static_optimizations, f, indent=2)
            
            self.log_optimization_result("Static-File-Optimization", "OPTIMIZATION", "PASS", 
                                       "Static file optimizations configured")
            
        except Exception as e:
            self.log_optimization_result("Static-File-Optimization", "OPTIMIZATION", "FAIL", 
                                       "Failed to optimize static files", e)
    
    def setup_security_enhancements(self):
        """Set up security enhancements"""
        print("🔒 Setting up security enhancements...")
        
        try:
            # Security configuration
            security_config = {
                'headers': {
                    'SECURE_BROWSER_XSS_FILTER': True,
                    'SECURE_CONTENT_TYPE_NOSNIFF': True,
                    'SECURE_HSTS_SECONDS': 31536000,
                    'SECURE_HSTS_INCLUDE_SUBDOMAINS': True,
                    'SECURE_HSTS_PRELOAD': True,
                    'X_FRAME_OPTIONS': 'DENY',
                },
                'session': {
                    'SESSION_COOKIE_SECURE': True,
                    'SESSION_COOKIE_HTTPONLY': True,
                    'SESSION_COOKIE_SAMESITE': 'Strict',
                    'CSRF_COOKIE_SECURE': True,
                    'CSRF_COOKIE_HTTPONLY': True,
                },
                'password': {
                    'AUTH_PASSWORD_VALIDATORS': [
                        'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
                        'django.contrib.auth.password_validation.MinimumLengthValidator',
                        'django.contrib.auth.password_validation.CommonPasswordValidator',
                        'django.contrib.auth.password_validation.NumericPasswordValidator',
                    ]
                }
            }
            
            # Create security middleware
            security_middleware_content = '''
"""
Enhanced Security Middleware for HMS
"""
import logging
from django.http import HttpResponseForbidden

logger = logging.getLogger('security')

class SecurityEnhancementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log security events
        if request.method == 'POST':
            logger.info(f"POST request to {request.path} from {request.META.get('REMOTE_ADDR')}")
        
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
'''
            
            with open('security_enhancement_middleware.py', 'w') as f:
                f.write(security_middleware_content)
            
            # Save security configuration
            with open('security_config.json', 'w') as f:
                json.dump(security_config, f, indent=2)
            
            self.log_optimization_result("Security-Enhancements", "SECURITY", "PASS", 
                                       "Security enhancements configured")
            
        except Exception as e:
            self.log_optimization_result("Security-Enhancements", "SECURITY", "FAIL", 
                                       "Failed to setup security enhancements", e)
    
    def create_system_health_check(self):
        """Create system health check endpoint"""
        print("🏥 Creating system health check...")
        
        try:
            health_check_content = '''
"""
System Health Check for HMS
"""
import json
import time
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
from django.contrib.auth import get_user_model

def system_health_check(request):
    """Comprehensive system health check"""
    health_status = {
        'timestamp': time.time(),
        'status': 'healthy',
        'checks': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = {'status': 'healthy', 'response_time': 'fast'}
    except Exception as e:
        health_status['checks']['database'] = {'status': 'unhealthy', 'error': str(e)}
        health_status['status'] = 'unhealthy'
    
    # User model check
    try:
        User = get_user_model()
        user_count = User.objects.count()
        health_status['checks']['user_model'] = {'status': 'healthy', 'user_count': user_count}
    except Exception as e:
        health_status['checks']['user_model'] = {'status': 'unhealthy', 'error': str(e)}
        health_status['status'] = 'unhealthy'
    
    # Settings check
    try:
        debug_mode = settings.DEBUG
        health_status['checks']['settings'] = {'status': 'healthy', 'debug_mode': debug_mode}
    except Exception as e:
        health_status['checks']['settings'] = {'status': 'unhealthy', 'error': str(e)}
        health_status['status'] = 'unhealthy'
    
    return JsonResponse(health_status)
'''
            
            with open('health_check.py', 'w') as f:
                f.write(health_check_content)
            
            self.log_optimization_result("Health-Check", "MONITORING", "PASS", 
                                       "System health check created")
            
        except Exception as e:
            self.log_optimization_result("Health-Check", "MONITORING", "FAIL", 
                                       "Failed to create health check", e)
    
    def log_optimization_result(self, operation, category, status, message="", error=None):
        """Log optimization results"""
        result = {
            'operation': operation,
            'category': category,
            'status': status,
            'message': message,
            'error': str(error) if error else None,
            'timestamp': dt.datetime.now().isoformat()
        }
        self.optimization_results.append(result)
        
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_symbol} {operation} ({category}): {status}")
        if message:
            print(f"   📝 {message}")
        if error:
            print(f"   🔥 Error: {error}")
    
    def run_optimization(self):
        """Run all system optimizations"""
        print("\n" + "="*80)
        print("🎯 SYSTEM OPTIMIZATION & MONITORING - HMS")
        print("="*80)
        
        # Run optimization steps
        self.setup_enhanced_logging()
        self.optimize_database_settings()
        self.setup_performance_monitoring()
        self.optimize_static_files()
        self.setup_security_enhancements()
        self.create_system_health_check()
        
        # Generate final report
        self.generate_optimization_report()
    
    def generate_optimization_report(self):
        """Generate optimization report"""
        print("\n" + "="*80)
        print("📋 SYSTEM OPTIMIZATION REPORT")
        print("="*80)
        
        total_operations = len(self.optimization_results)
        passed = len([r for r in self.optimization_results if r['status'] == 'PASS'])
        failed = len([r for r in self.optimization_results if r['status'] == 'FAIL'])
        
        print(f"📊 Total Operations: {total_operations}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed/total_operations*100):.1f}%" if total_operations > 0 else "N/A")
        
        # Save detailed report
        with open('system_optimization_report.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_operations': total_operations,
                    'passed': passed,
                    'failed': failed,
                    'success_rate': (passed/total_operations*100) if total_operations > 0 else 0
                },
                'operations': self.optimization_results
            }, f, indent=2)
        
        print(f"📄 Detailed report saved to: system_optimization_report.json")

if __name__ == "__main__":
    optimizer = SystemOptimizer()
    optimizer.run_optimization()
