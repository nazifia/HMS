#!/usr/bin/env python3
"""
Script to fix all custom_profile references to profile
"""

import os
import re

def fix_file(filepath):
    """Fix custom_profile references in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace custom_profile with profile
        original_content = content
        content = content.replace('custom_profile', 'profile')
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {filepath}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Main function to fix all files"""
    files_to_fix = [
        'accounts/management/commands/demo_users.py',
        'consultations/forms.py',
        'doctors/views.py',
        'hr/views.py',
        'theatre/models.py',
        'theatre/forms.py',
        'laboratory/forms.py',
        'inpatient/forms.py',
    ]
    
    updated_count = 0
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            if fix_file(filepath):
                updated_count += 1
        else:
            print(f"File not found: {filepath}")
    
    print(f"\nTotal files updated: {updated_count}")

if __name__ == "__main__":
    main()