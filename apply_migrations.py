#!/usr/bin/env python
"""Simple script to apply theatre migrations without color issues"""
import os
import sys

# Fix for Windows color support issues
if sys.platform == 'win32':
    import django.core.management.color as color_module
    color_module.supports_color = lambda: False

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
os.environ['DJANGO_COLORS'] = 'nocolor'
os.environ['NO_COLOR'] = '1'

import django
django.setup()

from django.core.management import call_command

print("Applying theatre migrations...")
try:
    call_command('migrate', 'theatre', verbosity=1, no_color=True)
    print("\n✓ Theatre migrations applied successfully!")
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
