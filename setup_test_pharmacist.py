#!/usr/bin/env python
"""
Setup script to create a test pharmacist and assign them to a dispensary.
This demonstrates the pharmacist-dispensary assignment system in action.
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
from django.contrib.auth import get_user_model
from django.utils import timezone

def setup_pharmacist():
    """Create a test pharmacist and assign to dispensary."""
    
    # Check if pharmacist role exists
    pharmacist_role, created = Role.objects.get_or_create(
        name='pharmacist',
        defaults={
            'description': 'Pharmacist with access to pharmacy module'
        }
    )
    
    if created:
        print(f"✓ Created pharmacist role: {pharmacist_role.name}")
    else:
        print(f"✓ Pharmacist role already exists: {pharmacist_role.name}")
    
    # Check if we have at least one dispensary
    dispensary = Dispensary.objects.first()
    if not dispensary:
        print("✗ No dispensary found in database. Please create at least one dispensary first.")
        return False
    print(f"✓ Using dispensary: {dispensary.name}")
    
    # Check if test pharmacist user exists
    try:
        user = CustomUser.objects.get(username='test_pharmacist')
        print(f"✓ Test pharmacist user already exists: {user.username}")
    except CustomUser.DoesNotExist:
        # Create test pharmacist user
        user = CustomUser.objects.create_user(
            username='test_pharmacist',
            phone_number='1122334455',
            password='test123',
            first_name='Test',
            last_name='Pharmacist',
            email='pharmacist@test.com',
            is_active=True
        )
        print(f"✓ Created test pharmacist user: {user.username}")
    
    # Assign pharmacist role to user
    user.roles.add(pharmacist_role)
    print(f"✓ Assigned pharmacist role to {user.username}")
    
    # Ensure user profile has correct role
    profile, created = CustomUserProfile.objects.get_or_create(user=user)
    profile.role = 'pharmacist'
    profile.save()
    
    # Check existing assignment
    existing_assignment = PharmacistDispensaryAssignment.objects.filter(
        pharmacist=user,
        dispensary=dispensary,
        end_date__isnull=True
    ).first()
    
    if existing_assignment:
        print(f"✓ User already assigned to {existing_assignment.dispensary.name}")
        return True
    
    # Create assignment
    assignment = PharmacistDispensaryAssignment.objects.create(
        pharmacist=user,
        dispensary=dispensary,
        start_date=timezone.now().date(),
        is_active=True,
        notes="Test assignment created automatically"
    )
    print(f"✓ Created assignment: {user.username} → {dispensary.name}")
    return True

def show_instructions():
    """Show instructions for testing the pharmacist login."""
    print("\n" + "="*60)
    print("TEST INSTRUCTIONS")
    print("="*60)
    print("1. Login to the pharmacy system with:")
    print(f"   Username: test_pharmacist")
    print(f"   Password: test123")
    print("\n2. You will be:")
    print("   - Auto-redirected to pharmacy dashboard")
    print("   - Assigned to Dispensary 1")
    print("   - Able to see only their assigned dispensary data\n")
    
    print("3. Test Functions:")
    print("   - View pharmacy dashboard at /pharmacy/")
    print("   - See test pharmacist in assignment list")
    print("   - View menu options\n")
    
    print("4. Admin Functions:")
    print("   - Manage assignments via /admin/pharmacy/pharmacistdispensaryassignment/")
    print("   - Use command: python manage.py assign_pharmacist_to_dispensary --list\n")
    
    print("5. Cleanup (optional):")
    print("   - Delete test user from admin")
    print("   - Delete assignments from admin")

if __name__ == '__main__':
    print("Setting up test pharmacist with dispensary assignment...")
    
    try:
        with transaction.atomic():
            success = setup_pharmacist()
            
            if success:
                show_instructions()
                print("\n✓ Setup completed successfully!")
            else:
                print("\n✗ Setup failed. Please check the database.")
                
    except Exception as e:
        print(f"\n✗ Error during setup: {e}")
        sys.exit(1)
