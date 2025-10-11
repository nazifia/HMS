#!/usr/bin/env python
"""
Script to apply activity monitoring setup
"""
import os
import sys
import django

# Setup Django environment first, without Django's logging
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

# Disable Django logging to avoid the error
os.environ.setdefault('DJANGO_LOGGING_CONFIG', 'logging.disable')

import django
from django.core.management import execute_from_command_line

# Disable all logging
import logging
logging.disable(logging.CRITICAL)

django.setup()

def apply_activity_monitoring():
    """Apply activity monitoring setup"""
    
    print("🚀 Setting up User Activity Monitoring System")
    print("=" * 50)
    
    try:
        # Apply migrations
        print("📋 Applying database migrations...")
        execute_from_command_line(['manage.py', 'migrate', 'accounts', '0007'])
        print("✅ Migrations applied successfully!")
        
        print("\n🎯 Activity Monitoring System is now ACTIVE!")
        print("\n📍 Access Points:")
        print("   • User Management → Activity Monitor")
        print("   • User Management → Activity Alerts") 
        print("   • User Management → User Sessions")
        print("   • User Management → Live Monitor")
        print("   • User Management → Activity Statistics")
        
        print("\n💡 The system will start tracking all user activities automatically!")
        print("   📊 Activity Dashboard: Real-time monitoring")
        print("   🔔 Activity Alerts: Security notifications")
        print("   👥 User Sessions: Session tracking")
        print("   🎮 Live Monitor: Live activity stream")
        print("   📈 Activity Statistics: Analytics & reports")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up activity monitoring: {e}")
        return False


if __name__ == '__main__':
    apply_activity_monitoring()
