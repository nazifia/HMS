#!/usr/bin/env python
"""
Script to fix dashboard URL patterns for all departments.

This script changes the dashboard URL from 'dashboard/' to '' (root path)
and moves the existing root path view to a different URL (e.g., 'records/').

This fixes the Django URL resolution issue where dashboard URLs at 'dashboard/'
were not being properly registered by the running server.
"""

import os
import re

# Department configurations
DEPARTMENTS = [
    {
        'name': 'laboratory',
        'file': 'laboratory/urls.py',
        'old_dashboard': "path('dashboard/', views.laboratory_dashboard, name='dashboard'),",
        'new_dashboard': "path('', views.laboratory_dashboard, name='dashboard'),",
        'has_root_path': False,  # No existing root path
    },
    {
        'name': 'icu',
        'file': 'icu/urls.py',
        'old_dashboard': "path('dashboard/', views.icu_dashboard, name='dashboard'),",
        'new_dashboard': "path('', views.icu_dashboard, name='dashboard'),",
        'old_root': "path('', views.icu_records_list, name='icu_records_list'),",
        'new_root': "path('records/', views.icu_records_list, name='icu_records_list'),",
        'has_root_path': True,
    },
    {
        'name': 'anc',
        'file': 'anc/urls.py',
        'old_dashboard': "path('dashboard/', views.anc_dashboard, name='dashboard'),",
        'new_dashboard': "path('', views.anc_dashboard, name='dashboard'),",
        'old_root': "path('', views.anc_records_list, name='anc_records_list'),",
        'new_root': "path('records/', views.anc_records_list, name='anc_records_list'),",
        'has_root_path': True,
    },
    {
        'name': 'labor',
        'file': 'labor/urls.py',
        'old_dashboard': "path('dashboard/', views.labor_dashboard, name='dashboard'),",
        'new_dashboard': "path('', views.labor_dashboard, name='dashboard'),",
        'old_root': "path('', views.labor_records_list, name='labor_records_list'),",
        'new_root': "path('records/', views.labor_records_list, name='labor_records_list'),",
        'has_root_path': True,
    },
    {
        'name': 'scbu',
        'file': 'scbu/urls.py',
        'old_dashboard': "path('dashboard/', views.scbu_dashboard, name='dashboard'),",
        'new_dashboard': "path('', views.scbu_dashboard, name='dashboard'),",
        'old_root': "path('', views.scbu_records_list, name='scbu_records_list'),",
        'new_root': "path('records/', views.scbu_records_list, name='scbu_records_list'),",
        'has_root_path': True,
    },
    {
        'name': 'ophthalmic',
        'file': 'ophthalmic/urls.py',
        'old_dashboard': "path('dashboard/', views.ophthalmic_dashboard, name='dashboard'),",
        'new_dashboard': "path('', views.ophthalmic_dashboard, name='dashboard'),",
        'old_root': "path('', views.ophthalmic_records_list, name='ophthalmic_records_list'),",
        'new_root': "path('records/', views.ophthalmic_records_list, name='ophthalmic_records_list'),",
        'has_root_path': True,
    },
    {
        'name': 'ent',
        'file': 'ent/urls.py',
        'old_dashboard': "path('dashboard/', views.ent_dashboard, name='dashboard'),",
        'new_dashboard': "path('', views.ent_dashboard, name='dashboard'),",
        'old_root': "path('', views.ent_records_list, name='ent_records_list'),",
        'new_root': "path('records/', views.ent_records_list, name='records_list'),",
        'has_root_path': True,
    },
    {
        'name': 'oncology',
        'file': 'oncology/urls.py',
        'old_dashboard': "path('dashboard/', views.oncology_dashboard, name='dashboard'),",
        'new_dashboard': "path('', views.oncology_dashboard, name='dashboard'),",
        'old_root': "path('', views.oncology_records_list, name='oncology_records_list'),",
        'new_root': "path('records/', views.oncology_records_list, name='records_list'),",
        'has_root_path': True,
    },
    {
        'name': 'family_planning',
        'file': 'family_planning/urls.py',
        'old_dashboard': "path('dashboard/', views.family_planning_dashboard, name='dashboard'),",
        'new_dashboard': "path('', views.family_planning_dashboard, name='dashboard'),",
        'old_root': "path('', views.family_planning_records_list, name='family_planning_records_list'),",
        'new_root': "path('records/', views.family_planning_records_list, name='records_list'),",
        'has_root_path': True,
    },
    {
        'name': 'gynae_emergency',
        'file': 'gynae_emergency/urls.py',
        'old_dashboard': "path('dashboard/', views.gynae_emergency_dashboard, name='dashboard'),",
        'new_dashboard': "path('', views.gynae_emergency_dashboard, name='dashboard'),",
        'old_root': "path('', views.gynae_emergency_records_list, name='gynae_emergency_records_list'),",
        'new_root': "path('records/', views.gynae_emergency_records_list, name='records_list'),",
        'has_root_path': True,
    },
]

def fix_department_urls(dept_config):
    """Fix URL patterns for a single department."""
    file_path = dept_config['file']
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Replace dashboard URL
    if 'old_dashboard' in dept_config:
        content = content.replace(dept_config['old_dashboard'], dept_config['new_dashboard'])
    
    # Replace root path if it exists
    if dept_config.get('has_root_path') and 'old_root' in dept_config:
        content = content.replace(dept_config['old_root'], dept_config['new_root'])
    
    # Check if anything changed
    if content == original_content:
        print(f"⚠️  No changes needed for {dept_config['name']}")
        return False
    
    # Write the file back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Fixed {dept_config['name']}: {file_path}")
    return True

def main():
    """Main function to fix all departments."""
    print("=" * 80)
    print("DASHBOARD URL FIX SCRIPT")
    print("=" * 80)
    print()
    print("This script will fix dashboard URL patterns for all departments.")
    print("Changes:")
    print("  - Dashboard URL: 'dashboard/' → '' (root path)")
    print("  - Records URL: '' → 'records/' (if applicable)")
    print()
    print("=" * 80)
    print()
    
    fixed_count = 0
    skipped_count = 0
    
    for dept in DEPARTMENTS:
        if fix_department_urls(dept):
            fixed_count += 1
        else:
            skipped_count += 1
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Fixed: {fixed_count} departments")
    print(f"⚠️  Skipped: {skipped_count} departments")
    print(f"📊 Total: {len(DEPARTMENTS)} departments")
    print()
    print("=" * 80)
    print()
    print("NEXT STEPS:")
    print("1. Restart the Django development server")
    print("2. Test each dashboard URL:")
    for dept in DEPARTMENTS:
        dept_name = dept['name'].replace('_', '-')
        print(f"   - http://127.0.0.1:8000/{dept_name}/")
    print()
    print("=" * 80)

if __name__ == '__main__':
    main()

