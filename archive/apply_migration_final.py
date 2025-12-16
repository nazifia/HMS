#!/usr/bin/env python
"""
Apply migration without Django logging issues
"""
import os
import sys

print("🚀 Applying Activity Monitoring Migration")
print("=" * 45)

# Setup without Django logging to avoid Windows stderr issues
import logging
logging.disable(logging.CRITICAL)

# Change to project directory
os.chdir('C:\\Users\\dell\\Desktop\\MY_PRODUCTS\\HMS')

try:
    # Import Django commands directly
    from django.core.management import execute_from_command_line
    
    print("📋 Applying database migration for activity monitoring...")
    
    # Apply the specific migration
    execute_from_command_line(['manage.py', 'migrate', 'accounts', '0007'])
    
    print("✅ Migration applied successfully!")
    print("\n🎯 Activity Monitoring tables created!")
    print("\n📊 You can now:")
    print("   1. Start the server: python manage.py runserver")
    print("   2. Login and access: User Management → Activity Monitor")
    print("   3. All monitoring features will be available!")
    
    print("\n🎉 System Status: ACTIVE")
    
except ImportError as e:
    print(f"❌ Django import error: {e}")
    print("   Please ensure you're running this from the project directory")
except Exception as e:
    print(f"❌ Migration error: {e}")
    print("   Please run: python manage.py migrate --merge")
