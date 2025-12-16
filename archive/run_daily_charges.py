#!/usr/bin/env python
"""
Daily Admission Charges Runner
Run this script daily at midnight to process admission charges
"""

import os
import sys
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.core.management import call_command

def run_daily_charges():
    """Run daily admission charges for today"""
    try:
        print(f"[{datetime.now()}] Starting daily admission charges processing...")
        call_command('daily_admission_charges')
        print(f"[{datetime.now()}] Daily charges processing completed successfully")
        return True
    except Exception as e:
        print(f"[{datetime.now()}] ERROR: Daily charges processing failed: {e}")
        return False

if __name__ == "__main__":
    success = run_daily_charges()
    sys.exit(0 if success else 1)
