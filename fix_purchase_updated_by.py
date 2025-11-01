#!/usr/bin/env python
"""
Fix script for Purchase model 'updated_by' AttributeError
"""
import os
import re

def fix_views_file():
    """Fix any remaining references to updated_by in views.py"""
    views_file = 'pharmacy/views.py'
    
    with open(views_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for any remaining updated_by references with Purchase objects
    old_patterns = [
        (r'purchase\.updated_by', 'purchase.current_approver'),
        (r'purchase\.updated_at', 'purchase.approval_updated_at'),
    ]
    
    changes_made = []
    for old, new in old_patterns:
        if old in content:
            content = content.replace(old, new)
            changes_made.append(f"Replaced '{old}' with '{new}'")
    
    if changes_made:
        with open(views_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Fixed views.py:")
        for change in changes_made:
            print(f"  - {change}")
    else:
        print("No fixes needed in views.py")
    
    return len(changes_made) > 0

def check_template():
    """Check template for any remaining updated_by references"""
    template_file = 'pharmacy/templates/pharmacy/purchase_detail.html'
    
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for problematic patterns
    problematic = []
    if 'purchase.updated_by' in content:
        problematic.append("purchase.updated_by")
    if 'purchase.updated_at' in content:
        problematic.append("purchase.updated_at")
    
    if problematic:
        print(f"Found remaining issues in template: {', '.join(problematic)}")
        return False
    else:
        print("Template looks good!")
        return True

if __name__ == '__main__':
    print("Checking and fixing Purchase 'updated_by' AttributeError...")
    
    views_fixed = fix_views_file()
    template_ok = check_template()
    
    if views_fixed or not template_ok:
        print("\n⚠️  Changes were made. Please restart the Django server.")
    else:
        print("\n✅ All files look good. Try clearing Python cache and restarting server.")
