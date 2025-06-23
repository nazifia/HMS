#!/usr/bin/env python
"""
This script fixes department data issues in the accounts_customuserprofile table.
It handles both:
1. Converting string department names to proper foreign key relationships
2. Cleaning up invalid department_id values

Run this with: python fix_department_data.py
"""
import os
import django
import sys
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Fix department data issues')
parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
args = parser.parse_args()

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Import and run the management command
from django.core.management import call_command

if __name__ == "__main__":
    print("Starting department data cleanup...")
    try:
        # Call the management command with appropriate options
        options = {'dry_run': args.dry_run}
        call_command('fix_departments', **options)
        print("Department data cleanup complete!")
    except Exception as e:
        print(f"Error: {e}")
        print("Department data cleanup failed. See error message above.")
        sys.exit(1)