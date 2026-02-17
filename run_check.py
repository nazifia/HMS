"""Run Django system checks"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.core import checks
from django.core.checks.registry import registry

# Run all system checks
errors = registry.run_checks()

if errors:
    print("SYSTEM CHECK FAILED")
    for error in errors:
        print(f"  {error.msg}")
    sys.exit(1)
else:
    print("SYSTEM CHECK PASSED - No errors found!")
    sys.exit(0)
