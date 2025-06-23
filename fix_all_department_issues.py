#!/usr/bin/env python
"""
This script is a wrapper to run the fix_departments management command.
It fixes all department-related issues in the accounts_customuserprofile table:
1. Fixes invalid department_id values (setting them to NULL)
2. Migrates string department names to proper foreign key relationships

Run this script directly with: python fix_all_department_issues.py
"""
import os
import django
import sys
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Fix all department data issues')
parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
args = parser.parse_args()

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Import and run the management command
from django.core.management import call_command

if __name__ == "__main__":
    print("Starting comprehensive department data cleanup...")
    try:
        # Call the management command with appropriate options
        options = {'dry_run': args.dry_run}
        call_command('fix_departments', **options)
        print("All department data fixes completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        print("Department data fixes failed. See error message above.")
        sys.exit(1)