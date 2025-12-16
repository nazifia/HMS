"""
Script to update the superuser with a phone number for authentication.

This script sets up the Django environment and runs the update_superuser_phone management command.
"""

import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Import the management command
from django.core.management import call_command

def main():
    """Run the update_superuser_phone management command"""
    
    # Default phone number (can be changed)
    default_phone = "9876543210"
    
    # Get phone number from command line arguments if provided
    if len(sys.argv) > 1:
        phone_number = sys.argv[1]
    else:
        phone_number = default_phone
        
    print(f"Updating superuser with phone number: {phone_number}")
    
    # Call the management command
    call_command('update_superuser_phone', phone_number)
    
if __name__ == "__main__":
    main()
