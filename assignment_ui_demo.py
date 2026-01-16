#!/usr/bin/env python
"""
Setup script to demonstrate the complete pharmacist-dispensary assignment UI system.
Includes creating test data and showing how to access the UI.
"""

import os
import sys
import django
from django.db import transaction

# Add the project directory to sys.path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from accounts.models import CustomUser, CustomUserProfile, Role
from pharmacy.models import Dispensary, PharmacistDispensaryAssignment
from django.contrib.auth.models import Permission
from django.utils import timezone
from datetime import timedelta

def create_test_dispensaries():
    """Create additional test dispensaries if they don't exist."""
    dispensaries = [
        {'name': 'Main Pharmacy', 'location': 'Building A, Ground Floor'},
        {'name': 'Emergency Pharmacy', 'location': 'Emergency Department'},
        {'name': 'Outpatient Pharmacy', 'location': 'Clinic Complex'},
    ]
    
    created_dispensaries = []
    for disp_data in dispensaries:
        dispensary, disp_created = Dispensary.objects.get_or_create(
            name=disp_data['name'],
            defaults=disp_data
        )
        if disp_created:
            created_dispensaries.append(dispensary)
    
    return created_dispensaries

def create_pharmacist_users():
    """Create multiple pharmacist test users."""
    pharmacist_role, _ = Role.objects.get_or_create(
        name='pharmacist',
        defaults={'description': 'Pharmacist'}
    )
    
    usernames = [
        {'username': 'pharma_jane', 'phone': '1111111111', 'first': 'Jane', 'last': 'Smith'},
        {'username': 'pharma_mike', 'phone': '2222222222', 'first': 'Mike', 'last': 'Johnson'},
        {'username': 'pharma_sarah', 'phone': '3333333333', 'first': 'Sarah', 'last': 'Williams'},
    ]
    
    created = []
    for user_data in usernames:
        try:
            user = CustomUser.objects.get(username=user_data['username'])
        except CustomUser.DoesNotExist:
            user = CustomUser.objects.create_user(
                username=user_data['username'],
                phone_number=user_data['phone'],
                password='pharma123',
                first_name=user_data['first'],
                last_name=user_data['last'],
                email=f"{user_data['username']}@hospital.com",
                is_active=True
            )
            # Assign pharmacist role
            user.roles.add(pharmacist_role)
            
            # Create and update profile
            profile = user.profile
            profile.role = 'pharmacist'
            profile.save()
        
        created.append(user)
    
    return created

def create_assignments():
    """Create sample assignments."""
    pharmacies = Dispensary.objects.filter(is_active=True)
    pharmacists = CustomUser.objects.filter(profile__role='pharmacist', is_active=True)
    
    assignments = []
    
    # Assign first pharmacist to Main Pharmacy (active)
    if pharmacists.exists() and pharmacies.exists():
        assignment, created = PharmacistDispensaryAssignment.objects.get_or_create(
            pharmacist=pharmacists[0],
            dispensary=pharmacies[0],
            defaults={
                'start_date': timezone.now().date() - timedelta(days=5),
                'is_active': True,
                'notes': 'Primary assignment'
            }
        )
        if created:
            assignments.append(assignment)
    
    # Assign second pharmacist to Emergency Pharmacy (active)
    if pharmacists.count() >= 2 and pharmacies.count() >= 2:
        assignment, created = PharmacistDispensaryAssignment.objects.get_or_create(
            pharmacist=pharmacists[1],
            dispensary=pharmacies[1],
            defaults={
                'start_date': timezone.now().date() - timedelta(days=2),
                'is_active': True,
                'notes': 'Emergency shift'
            }
        )
        if created:
            assignments.append(assignment)
    
    # Assign third pharmacist to Main Pharmacy (inactive - ended)
    if pharmacists.count() >= 3 and pharmacies.exists():
        from django.utils.timezone import make_aware
        assignment, created = PharmacistDispensaryAssignment.objects.get_or_create(
            pharmacist=pharmacists[2],
            dispensary=pharmacies[0],
            defaults={
                'start_date': timezone.now().date() - timedelta(days=20),
                'end_date': timezone.now().date() - timedelta(days=5),
                'is_active': False,
                'notes': 'Temporary assignment ended'
            }
        )
        if created:
            assignments.append(assignment)
    
    return assignments

def show_ui_access_instructions():
    """Show complete UI access instructions."""
    print("\n" + "="*80)
    print("PHARMACIST-ASSIGNMENT UI - COMPLETE ACCESS GUIDE")
    print("="*80)
    
    print("\n1. ADMIN ACCESS (Full Access)")
    print("   - URL: http://localhost:8000/pharmacy/assignments/")
    print("   - Required Permission: superuser or pharmacy.manage_pharmacists")
    print("   - Features:")
    print("     • Add new pharmacist-dispensary assignments")
    print("     • Edit existing assignments")
    print("     • End assignments (with end date)")
    print("     • Delete assignments permanently")
    print("     • View assignment list with filters")
    print("     • Access assignment reports & analytics")
    
    print("\n2. DEMO TEST USERS")
    print("   - Test Pharmacist: test_pharmacist / test123")
    print("     (Has one active assignment to Dispensary 1)")
    print("   - Additional Pharmacists: pharma_jane / pharma123")
    print("     (Created with appropriate roles)")
    
    print("\n3. UI FEATURES DEMONSTRATION")
    print("   A. Assignment Management Form:")
    print("      • Select pharmacist from dropdown")
    print("      • Select dispensary location")
    print("      • Set start date (defaults to today)")
    print("      • Add notes (optional)")
    print("      • Toggle active status")
    print("\n   B. Assignment List View:")
    print("      • Filter: Active only or All assignments")
    print("      • Status indicators: Active/Inactive badges")
    print("      • Action buttons: Edit, End, Delete")
    print("      • Quick filters on sidebar")
    print("\n   C. Reports & Analytics:")
    print("      • Assignment distribution by dispensary")
    print("      • Top pharmacists with most assignments")
    print("      • Recent activity (last 30 days)")
    print("      • Utilization metrics")
    
    print("\n4. TEST SCENARIOS TO VERIFY")
    print("   1. TEST 1: Admin creates new assignment")
    print("      - Login as admin")
    print("      - Go to: /pharmacy/assignments/")
    print("      - Fill form and submit")
    print("      - Verify: Assignment appears in list with status 'Active'")
    
    print("\n   2. TEST 2: End an assignment")
    print("      - Click 'Ban' icon on an active assignment")
    print("      - System sets end_date to today and marks inactive")
    print("      - Verify: Status changes to 'Inactive'")
    
    print("\n   3. TEST 3: Assignment Reports")
    print("      - Go to: /pharmacy/assignments/reports/")
    print("      - Verify: Charts and analytics displayed")
    
    print("\n   4. TEST 4: Pharmacist login with assignment")
    print("      - Login as test_pharmacist")
    print("      - Verify: Auto-redirected to pharmacy dashboard")
    print("      - Check: Main page shows assignment info")
    
    print("\n   5. TEST 5: Pharmacist login without assignment")
    print("      - Login as pharma_jane (add temporary assignment)")
    print("      - Verify: Navigation to 'Select Dispensary' prompts")
    
    print("\n5. QUICK TEST COMMANDS (Django Shell)")
    print("   # Create test assignment:")
    print("   from pharmacy.models import PharmacistDispensaryAssignment, Dispensary")
    print("   from accounts.models import CustomUser")
    print("   user = CustomUser.objects.get(username='pharma_jane')")
    print("   disp = Dispensary.objects.first()")
    print("   PharmacistDispensaryAssignment.objects.create(")
    print("       pharmacist=user, dispensary=disp,")
    print("       start_date='2025-01-16', is_active=True)")
    
    print("\n   # List all assignments:")
    print("   print([(a.pharmacist.username, a.dispensary.name, a.is_active)")
    print("         for a in PharmacistDispensaryAssignment.objects.all()])")
    
    print("\n6. PERMISSION Management")
    print("   To assign pharmacy.manage_pharmacists permission to admin:")
    print("   ")
    print("   Step 1: Login as admin")
    print("   Step 2: Go to: /accounts/superuser/user-permissions/")
    print("   Step 3: Find your username and assign 'pharmacy.manage_pharmacists'")
    print("   ")
    print("   OR via Django Admin:")
    print("   Step 1: Go to /admin/auth/user/")
    print("   Step 2: Select your user")
    print("   Step 3: In User Permissions, find and select 'pharmacy.manage_pharmacists'")
    print("   Step 4: Save")
    
    print("\n7. NAVIGATION SURFACES")
    print("   - Sidebar: Dispensaries → Pharmacist Assignments")
    print("   - Sidebar: Dispensaries → Assignment Reports")
    print("   - Sidebar Node: Pharmacy → Select/Change Dispatch (for pharmacists)")
    print("   - Top Bar: Current dispensary display with change link")
    
    print("\n" + "="*80)
    print("SETUP SUMMARY")
    print("="*80)

def main():
    """Main execution."""
    print("Setting up pharmacist-assignment UI demonstration...")
    
    dispensaries_created = create_test_dispensaries()
    if dispensaries_created:
        print(f"✓ Created {len(dispensaries_created)} new dispensaries")
    
    pharmacists_created = create_pharmacist_users()
    if pharmacists_created:
        print(f"✓ Created {len(pharmacists_created)} pharmacist users")
    
    assignments_created = create_assignments()
    if assignments_created:
        print(f"✓ Created {len(assignments_created)} sample assignments")
    
    # Show what was set up
    print(f"\nSystem now contains:")
    print(f"  - {Dispensary.objects.filter(is_active=True).count()} active dispensaries")
    print(f"  - {CustomUser.objects.filter(profile__role='pharmacist').count()} pharmacist users")
    print(f"  - {PharmacistDispensaryAssignment.objects.count()} assignments")
    
    show_ui_access_instructions()
    
    print("\n✓ Setup completed successfully!")
    print(f"\nNext Steps:")
    print(f"1. Start server: python manage.py runserver")
    print(f"2. Login with admin credentials")
    print(f"3. Navigate to: http://localhost:8000/pharmacy/assignments/")
    print(f"4. Access with: test_pharmacist (test123) or any admin user")

if __name__ == "__main__":
    main()
