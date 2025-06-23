# fix_invalid_department_ids.py
"""
This script will fix any invalid department_id values in the accounts_customuserprofile table.
It will set department_id to NULL for any row where it is not a valid integer (i.e., still a string like 'Cardiology').
Run this with: python fix_invalid_department_ids.py
"""
import os
import django
import sys
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Fix invalid department IDs')
parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
args = parser.parse_args()

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Import the management command
from django.core.management import call_command

class DepartmentIdFixer:
    def fix_invalid_department_ids(self):
        """Fix any invalid department_id values in the database."""
        print("Starting to fix invalid department IDs...")
        try:
            # Call the management command with appropriate options
            options = {'dry_run': args.dry_run}
            # We'll use the same command but only focus on the ID fixing part
            call_command('fix_departments', **options)
            print("Invalid department IDs fixed successfully!")
        except Exception as e:
            print(f"Error: {e}")
            print("Failed to fix invalid department IDs. See error message above.")
            sys.exit(1)

if __name__ == "__main__":
    fixer = DepartmentIdFixer()
    fixer.fix_invalid_department_ids()
    print("Script completed.")