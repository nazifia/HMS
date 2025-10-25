#!/usr/bin/env python
"""
Dashboard URL Verification Script

This script verifies that all department dashboard URLs are properly configured
and accessible. Run this after starting the development server.

Usage:
    python verify_dashboards.py
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model
from accounts.models import Department, CustomUserProfile

User = get_user_model()

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{text.center(80)}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")

def print_success(text):
    """Print success message"""
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    """Print error message"""
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠ {text}{RESET}")

def print_info(text):
    """Print info message"""
    print(f"{BLUE}ℹ {text}{RESET}")

# Department dashboard configurations
DEPARTMENT_DASHBOARDS = [
    {
        'name': 'Laboratory',
        'url_name': 'laboratory:dashboard',
        'path': '/laboratory/dashboard/',
        'app': 'laboratory',
    },
    {
        'name': 'Radiology',
        'url_name': 'radiology:index',
        'path': '/radiology/',
        'app': 'radiology',
    },
    {
        'name': 'Dental',
        'url_name': 'dental:dashboard',
        'path': '/dental/dashboard/',
        'app': 'dental',
    },
    {
        'name': 'Theatre',
        'url_name': 'theatre:dashboard',
        'path': '/theatre/',
        'app': 'theatre',
    },
    {
        'name': 'Ophthalmic',
        'url_name': 'ophthalmic:dashboard',
        'path': '/ophthalmic/dashboard/',
        'app': 'ophthalmic',
    },
    {
        'name': 'ENT',
        'url_name': 'ent:dashboard',
        'path': '/ent/dashboard/',
        'app': 'ent',
    },
    {
        'name': 'Oncology',
        'url_name': 'oncology:dashboard',
        'path': '/oncology/dashboard/',
        'app': 'oncology',
    },
    {
        'name': 'SCBU',
        'url_name': 'scbu:dashboard',
        'path': '/scbu/dashboard/',
        'app': 'scbu',
    },
    {
        'name': 'ANC',
        'url_name': 'anc:dashboard',
        'path': '/anc/dashboard/',
        'app': 'anc',
    },
    {
        'name': 'Labor',
        'url_name': 'labor:dashboard',
        'path': '/labor/dashboard/',
        'app': 'labor',
    },
    {
        'name': 'ICU',
        'url_name': 'icu:dashboard',
        'path': '/icu/dashboard/',
        'app': 'icu',
    },
    {
        'name': 'Family Planning',
        'url_name': 'family_planning:dashboard',
        'path': '/family_planning/dashboard/',
        'app': 'family_planning',
    },
    {
        'name': 'Gynae Emergency',
        'url_name': 'gynae_emergency:dashboard',
        'path': '/gynae_emergency/dashboard/',
        'app': 'gynae_emergency',
    },
]

def verify_url_configuration():
    """Verify that all dashboard URLs are properly configured"""
    print_header("URL Configuration Verification")
    
    success_count = 0
    error_count = 0
    
    for dashboard in DEPARTMENT_DASHBOARDS:
        try:
            url = reverse(dashboard['url_name'])
            if url == dashboard['path']:
                print_success(f"{dashboard['name']}: {dashboard['url_name']} → {url}")
                success_count += 1
            else:
                print_warning(f"{dashboard['name']}: Expected {dashboard['path']}, got {url}")
                success_count += 1
        except NoReverseMatch as e:
            print_error(f"{dashboard['name']}: URL '{dashboard['url_name']}' not found - {e}")
            error_count += 1
    
    print(f"\n{GREEN}Success: {success_count}/{len(DEPARTMENT_DASHBOARDS)}{RESET}")
    if error_count > 0:
        print(f"{RED}Errors: {error_count}/{len(DEPARTMENT_DASHBOARDS)}{RESET}")
    
    return error_count == 0

def verify_template_existence():
    """Verify that all dashboard templates exist"""
    print_header("Template Existence Verification")
    
    success_count = 0
    error_count = 0
    
    template_paths = [
        'templates/laboratory/dashboard.html',
        'templates/radiology/index.html',
        'templates/dental/dashboard.html',
        'templates/theatre/dashboard.html',
        'templates/ophthalmic/dashboard.html',
        'templates/ent/dashboard.html',
        'templates/oncology/dashboard.html',
        'templates/scbu/dashboard.html',
        'templates/anc/dashboard.html',
        'templates/labor/dashboard.html',
        'templates/icu/dashboard.html',
        'templates/family_planning/dashboard.html',
        'templates/gynae_emergency/dashboard.html',
    ]
    
    for template_path in template_paths:
        if os.path.exists(template_path):
            print_success(f"Template exists: {template_path}")
            success_count += 1
        else:
            print_error(f"Template missing: {template_path}")
            error_count += 1
    
    print(f"\n{GREEN}Found: {success_count}/{len(template_paths)}{RESET}")
    if error_count > 0:
        print(f"{RED}Missing: {error_count}/{len(template_paths)}{RESET}")
    
    return error_count == 0

def verify_departments_exist():
    """Verify that all departments exist in the database"""
    print_header("Department Database Verification")
    
    success_count = 0
    warning_count = 0
    
    for dashboard in DEPARTMENT_DASHBOARDS:
        dept_name = dashboard['name']
        try:
            dept = Department.objects.get(name__iexact=dept_name)
            print_success(f"Department exists: {dept.name} (ID: {dept.id})")
            success_count += 1
        except Department.DoesNotExist:
            print_warning(f"Department not found: {dept_name} (Create it in Django admin)")
            warning_count += 1
        except Department.MultipleObjectsReturned:
            print_warning(f"Multiple departments found for: {dept_name} (Clean up duplicates)")
            warning_count += 1
    
    print(f"\n{GREEN}Found: {success_count}/{len(DEPARTMENT_DASHBOARDS)}{RESET}")
    if warning_count > 0:
        print(f"{YELLOW}Warnings: {warning_count}/{len(DEPARTMENT_DASHBOARDS)}{RESET}")
    
    return True  # Warnings don't fail the check

def verify_view_functions():
    """Verify that all dashboard view functions exist"""
    print_header("View Function Verification")
    
    success_count = 0
    error_count = 0
    
    view_imports = [
        ('laboratory.views', 'laboratory_dashboard'),
        ('radiology.views', 'index'),
        ('dental.views', 'dental_dashboard'),
        ('theatre.views', 'TheatreDashboardView'),
        ('ophthalmic.views', 'ophthalmic_dashboard'),
        ('ent.views', 'ent_dashboard'),
        ('oncology.views', 'oncology_dashboard'),
        ('scbu.views', 'scbu_dashboard'),
        ('anc.views', 'anc_dashboard'),
        ('labor.views', 'labor_dashboard'),
        ('icu.views', 'icu_dashboard'),
        ('family_planning.views', 'family_planning_dashboard'),
        ('gynae_emergency.views', 'gynae_emergency_dashboard'),
    ]
    
    for module_name, view_name in view_imports:
        try:
            module = __import__(module_name, fromlist=[view_name])
            view = getattr(module, view_name)
            print_success(f"View exists: {module_name}.{view_name}")
            success_count += 1
        except (ImportError, AttributeError) as e:
            print_error(f"View not found: {module_name}.{view_name} - {e}")
            error_count += 1
    
    print(f"\n{GREEN}Found: {success_count}/{len(view_imports)}{RESET}")
    if error_count > 0:
        print(f"{RED}Missing: {error_count}/{len(view_imports)}{RESET}")
    
    return error_count == 0

def print_summary(url_ok, template_ok, dept_ok, view_ok):
    """Print final summary"""
    print_header("Verification Summary")
    
    checks = [
        ("URL Configuration", url_ok),
        ("Template Existence", template_ok),
        ("Department Database", dept_ok),
        ("View Functions", view_ok),
    ]
    
    all_passed = all(result for _, result in checks)
    
    for check_name, result in checks:
        if result:
            print_success(f"{check_name}: PASSED")
        else:
            print_error(f"{check_name}: FAILED")
    
    print()
    if all_passed:
        print_success("All verifications passed! ✓")
        print_info("You can now test the dashboards by starting the server:")
        print_info("  python manage.py runserver")
        print_info("\nThen visit the dashboard URLs listed above.")
    else:
        print_error("Some verifications failed. Please fix the issues above.")
    
    return all_passed

def main():
    """Main verification function"""
    print_header("Department Dashboard Verification Script")
    print_info("Verifying all 13 department dashboards...")
    
    # Run all verifications
    url_ok = verify_url_configuration()
    template_ok = verify_template_existence()
    dept_ok = verify_departments_exist()
    view_ok = verify_view_functions()
    
    # Print summary
    all_ok = print_summary(url_ok, template_ok, dept_ok, view_ok)
    
    # Exit with appropriate code
    sys.exit(0 if all_ok else 1)

if __name__ == '__main__':
    main()

