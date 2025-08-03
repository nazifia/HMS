#!/usr/bin/env python3
"""
Script to set up cron job for daily admission charges.
This script helps configure the automated daily admission fee deduction.

Usage:
    python scripts/setup_daily_charges_cron.py

This will create a cron job that runs daily at 12:00 AM to deduct admission charges.
"""

import os
import sys
import subprocess
from pathlib import Path

def get_project_root():
    """Get the HMS project root directory."""
    current_dir = Path(__file__).parent.parent
    return current_dir.absolute()

def get_python_path():
    """Get the Python executable path."""
    return sys.executable

def create_cron_entry():
    """Create the cron job entry for daily admission charges."""
    project_root = get_project_root()
    python_path = get_python_path()
    
    # Cron job command
    cron_command = f"0 0 * * * cd {project_root} && {python_path} manage.py daily_admission_charges >> /var/log/hms_daily_charges.log 2>&1"
    
    return cron_command

def setup_cron_job():
    """Set up the cron job for daily admission charges."""
    print("Setting up daily admission charges cron job...")
    
    cron_entry = create_cron_entry()
    
    print(f"\nCron job entry to add:")
    print(f"{cron_entry}")
    
    print(f"\nTo manually add this cron job, run:")
    print(f"crontab -e")
    print(f"Then add the following line:")
    print(f"{cron_entry}")
    
    # For Windows users
    if os.name == 'nt':
        print(f"\nFor Windows users:")
        print(f"You can use Windows Task Scheduler instead of cron.")
        print(f"Create a daily task that runs at 12:00 AM with this command:")
        print(f"{get_python_path()} {get_project_root()}/manage.py daily_admission_charges")
        return
    
    # Try to add automatically (Linux/Mac)
    try:
        # Get current crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        current_crontab = result.stdout if result.returncode == 0 else ""
        
        # Check if our job already exists
        if "daily_admission_charges" in current_crontab:
            print("\nDaily admission charges cron job already exists!")
            return
        
        # Add our job
        new_crontab = current_crontab + "\n" + cron_entry + "\n"
        
        # Write new crontab
        process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
        process.communicate(input=new_crontab)
        
        if process.returncode == 0:
            print("\n✓ Cron job added successfully!")
            print("Daily admission charges will run automatically at 12:00 AM every day.")
        else:
            print("\n✗ Failed to add cron job automatically.")
            print("Please add it manually using the instructions above.")
            
    except FileNotFoundError:
        print("\nCrontab not found. Please add the cron job manually:")
        print("1. Open terminal")
        print("2. Run: crontab -e")
        print(f"3. Add this line: {cron_entry}")
    except Exception as e:
        print(f"\nError setting up cron job: {e}")
        print("Please add the cron job manually using the instructions above.")

def create_log_directory():
    """Create log directory for cron job output."""
    log_dir = "/var/log"
    if os.name == 'nt':  # Windows
        log_dir = get_project_root() / "logs"
        log_dir.mkdir(exist_ok=True)
        print(f"Created log directory: {log_dir}")
    else:  # Linux/Mac
        if os.access(log_dir, os.W_OK):
            print(f"Log directory {log_dir} is writable.")
        else:
            print(f"Warning: {log_dir} may not be writable. Consider using a different log location.")

def main():
    """Main function to set up daily admission charges automation."""
    print("HMS Daily Admission Charges Setup")
    print("=" * 40)
    
    # Create log directory
    create_log_directory()
    
    # Set up cron job
    setup_cron_job()
    
    print("\n" + "=" * 40)
    print("Setup completed!")
    print("\nTo test the command manually, run:")
    print(f"python manage.py daily_admission_charges --dry-run")
    
    print("\nTo view logs (Linux/Mac):")
    print("tail -f /var/log/hms_daily_charges.log")
    
    if os.name == 'nt':
        print("\nTo view logs (Windows):")
        print(f"type {get_project_root()}\\logs\\hms_daily_charges.log")

if __name__ == "__main__":
    main()
