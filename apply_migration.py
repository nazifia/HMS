#!/usr/bin/env python
import os
import sys
import django
import io

sys.path.append('C:/Users/Dell/Desktop/MY_PRODUCTS/HMS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.core.management import call_command

# Capture output
out = io.StringIO()
call_command('migrate', 'billing', verbosity=3, stdout=out)
output = out.getvalue()

print("Migration output:")
print(output)
print("\nMigration completed successfully!")
