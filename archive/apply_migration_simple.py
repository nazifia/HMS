#!/usr/bin/env python
"""
Simple migration application script
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

# Disable logging to avoid the error
import logging
logging.disable(logging.CRITICAL)

django.setup()

def apply_migration():
    """Apply the activity monitoring migration"""
    
    print("🚀 Applying Activity Monitoring Migration")
    print("=" * 50)
    
    try:
        # Apply migrations
        execute_from_command_line(['manage.py', 'migrate', 'accounts', '0007'])
        print("✅ Migration applied successfully!")
        
        print("\n🎯 Activity Monitoring System is ready!")
        print("\n📚 The following features are now available:")
        print("   📊 Activity Dashboard")
        print("   🔔 Activity Alerts") 
        print("   👥 User Sessions")
        print("   🎮 Live Monitor")
        print("   📈 Activity Statistics")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        return False

if __name__ == '__main__':
    apply_migration()
