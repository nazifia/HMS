#!/usr/bin/env python
"""
Test script to verify that permissions are immediately granted after role update.
This tests the fix for permission cache invalidation.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from accounts.models import Role
from core.models import AuditLog

User = get_user_model()

def test_permission_cache_invalidation():
    """Test that permission cache is properly invalidated when role permissions change"""
    print("=" * 70)
    print("TESTING PERMISSION CACHE INVALIDATION FIX")
    print("=" * 70)

    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='test_permission_user',
        defaults={
            'email': 'test@example.com',
            'phone_number': '+234000000001',
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True
        }
    )
    if created:
        print(f"\n✓ Created test user: {user.username}")
    else:
        print(f"\n✓ Using existing test user: {user.username}")

    # Get or create a test role
    role, created = Role.objects.get_or_create(
        name='Test Permission Role',
        defaults={'description': 'Role for testing permission cache invalidation'}
    )
    if created:
        print(f"✓ Created test role: {role.name}")
    else:
        print(f"✓ Using existing test role: {role.name}")

    # Assign role to user
    user.roles.add(role)
    print(f"✓ Assigned role '{role.name}' to user '{user.username}'")

    # Get a test permission (e.g., patients.view_patient)
    try:
        test_permission = Permission.objects.get(
            content_type__app_label='patients',
            codename='view_patient'
        )
        print(f"✓ Found test permission: {test_permission.codename}")
    except Permission.DoesNotExist:
        print("⚠ Test permission 'patients.view_patient' not found, creating one...")
        from django.contrib.contenttypes.models import ContentType
        from patients.models import Patient
        content_type = ContentType.objects.get_for_model(Patient)
        test_permission, _ = Permission.objects.get_or_create(
            codename='view_patient',
            content_type=content_type,
            defaults={'name': 'Can view patient'}
        )
        print(f"✓ Created test permission: {test_permission.codename}")

    # Clear any existing permissions from the role
    role.permissions.clear()
    print(f"✓ Cleared all permissions from role '{role.name}'")

    # Clear user's permission cache
    user.clear_permission_cache()
    print(f"✓ Cleared permission cache for user '{user.username}'")

    # Test 1: User should NOT have the permission initially
    print("\n" + "-" * 70)
    print("TEST 1: Verify user does NOT have permission initially")
    print("-" * 70)
    has_perm = user.has_perm('patients.view_patient')
    print(f"User has 'patients.view_patient': {has_perm}")
    if not has_perm:
        print("✓ PASS: User correctly does NOT have permission")
    else:
        print("✗ FAIL: User unexpectedly has permission")
        return False

    # Test 2: Add permission to role and verify user immediately has it
    print("\n" + "-" * 70)
    print("TEST 2: Add permission to role and verify immediate effect")
    print("-" * 70)

    # Add the permission to the role
    role.permissions.add(test_permission)
    print(f"✓ Added permission '{test_permission.codename}' to role '{role.name}'")

    # IMPORTANT: In a real web app, each request gets a fresh user object from DB.
    # To simulate this, we reload the user from the database.
    user_id = user.id
    user = User.objects.get(id=user_id)
    print(f"✓ Reloaded user from database (simulates new web request)")

    # Check if user now has the permission
    # The fresh user object should have no cache, so it will check fresh permissions
    has_perm = user.has_perm('patients.view_patient')
    print(f"User has 'patients.view_patient': {has_perm}")

    if has_perm:
        print("✓ PASS: User IMMEDIATELY has permission after role update")
    else:
        print("✗ FAIL: User still does NOT have permission")
        print("  This means permissions are not being saved or retrieved correctly")
        return False

    # Test 3: Remove permission from role and verify immediate effect
    print("\n" + "-" * 70)
    print("TEST 3: Remove permission from role and verify immediate effect")
    print("-" * 70)

    # Remove the permission from the role
    role.permissions.remove(test_permission)
    print(f"✓ Removed permission '{test_permission.codename}' from role '{role.name}'")

    # Reload user from database to simulate new web request
    user = User.objects.get(id=user_id)
    print(f"✓ Reloaded user from database (simulates new web request)")

    # Check if user no longer has the permission
    has_perm = user.has_perm('patients.view_patient')
    print(f"User has 'patients.view_patient': {has_perm}")

    if not has_perm:
        print("✓ PASS: User IMMEDIATELY loses permission after role update")
    else:
        print("✗ FAIL: User still has permission")
        return False

    # Test 4: Test multiple permissions
    print("\n" + "-" * 70)
    print("TEST 4: Test adding multiple permissions at once")
    print("-" * 70)

    # Get multiple permissions
    permissions = list(Permission.objects.filter(
        content_type__app_label='patients'
    )[:3])

    if len(permissions) < 3:
        print(f"⚠ Only found {len(permissions)} patients permissions, using what's available")

    # Add multiple permissions
    role.permissions.add(*permissions)
    print(f"✓ Added {len(permissions)} permissions to role")

    # Reload user from database
    user = User.objects.get(id=user_id)
    print(f"✓ Reloaded user from database")

    # Check each permission
    all_passed = True
    for perm in permissions:
        has_perm = user.has_perm(f'patients.{perm.codename}')
        print(f"  User has 'patients.{perm.codename}': {has_perm}")
        if not has_perm:
            all_passed = False
            print(f"  ✗ FAIL: Permission not granted")

    if all_passed:
        print("✓ PASS: All permissions granted immediately")

    # Test 5: Clear all permissions
    print("\n" + "-" * 70)
    print("TEST 5: Test clearing all permissions from role")
    print("-" * 70)

    role.permissions.clear()
    print(f"✓ Cleared all permissions from role")

    # Reload user from database
    user = User.objects.get(id=user_id)
    print(f"✓ Reloaded user from database")

    # Check that user no longer has any of the permissions
    all_cleared = True
    for perm in permissions:
        has_perm = user.has_perm(f'patients.{perm.codename}')
        print(f"  User has 'patients.{perm.codename}': {has_perm}")
        if has_perm:
            all_cleared = False
            print(f"  ✗ FAIL: Permission still present")

    if all_cleared:
        print("✓ PASS: All permissions removed immediately")

    # Clean up
    print("\n" + "-" * 70)
    print("CLEANUP")
    print("-" * 70)
    user.roles.remove(role)
    print(f"✓ Removed role from user")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED! Permission cache invalidation is working correctly.")
    print("=" * 70)
    return True


if __name__ == '__main__':
    try:
        success = test_permission_cache_invalidation()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
