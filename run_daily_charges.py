#!/usr/bin/env python
"""
Daily Admission Charges - Run this script daily at midnight
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.core.management import call_command
from datetime import date

def run_daily_charges():
    """Run daily admission charges for today"""
    try:
        print(f"Running daily admission charges for {date.today()}")
        call_command('daily_admission_charges')
        print("Daily charges completed successfully")
    except Exception as e:
        print(f"Error running daily charges: {e}")

if __name__ == "__main__":
    run_daily_charges()
