#!/usr/bin/env python
"""
Test script for RBAC reorganization features
This script validates the implementation without running the server.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from accounts.models import Role, CustomUser
from accounts.forms import RoleForm
from django.contrib.auth.models import Permission

def test_role_model_methods():
    """Test the new Role model methods"""
    print("=" * 60)
    print("Testing Role Model Methods")
    print("=" * 60)

    # Get or create test roles
    try:
        admin_role = Role.objects.get(name='admin')
        doctor_role = Role.objects.get(name='doctor')
    except Role.DoesNotExist:
        print("⚠️  Warning: Standard roles not found. Skipping model method tests.")
        return

    # Test get_all_permissions
    admin_perms = admin_role.get_all_permissions()
    print(f"✓ Admin role effective permissions: {len(admin_perms)}")

    # Test get_inherited_permission_count - this previously caused AttributeError
    try:
        inherited_count = admin_role.get_inherited_permission_count()
        print(f"✓ Admin role inherited permission count: {inherited_count}")
        assert isinstance(inherited_count, int), "Count should be an integer"
        assert inherited_count >= 0, "Count should be non-negative"
    except AttributeError as e:
        print(f"✗ get_inherited_permission_count failed with AttributeError: {e}")
        raise

    # Test get_direct_permission_count
    direct_count = admin_role.get_direct_permission_count()
    print(f"✓ Admin role direct permission count: {direct_count}")

    # Test consistency: total = direct + inherited
    total_count = len(admin_role.get_all_permissions())
    print(f"✓ Consistency check: {direct_count} + {inherited_count} = {total_count}")
    assert direct_count + inherited_count == total_count, "Total should equal direct + inherited"

    # Test get_inheritance_chain
    chain = doctor_role.get_inheritance_chain()
    print(f"✓ Doctor role inheritance chain length: {len(chain)}")

    # Test check_circular_reference
    is_circular = admin_role.check_circular_reference(doctor_role)
    print(f"✓ Circular reference check: {is_circular}")

    print()

def test_role_form_validation():
    """Test form validation including circular reference"""
    print("=" * 60)
    print("Testing Role Form Validation")
    print("=" * 60)

    # Get a role to use for testing
    try:
        role = Role.objects.first()
        if not role:
            print("⚠️  No roles found for testing")
            return
    except Exception as e:
        print(f"⚠️  Error getting role: {e}")
        return

    # Test 1: Self-parenting prevention
    form_data = {
        'name': 'Test Role',
        'parent': role.id,
    }
    # Simulate setting self as parent
    if role.pk:
        form = RoleForm(data={'name': 'Test', 'parent': role.pk}, instance=role)
        if not form.is_valid():
            print("✓ Self-parenting prevented correctly")
        else:
            print("✗ Self-parenting check failed")

    # Test 2: Circular reference detection
    if role.parent:
        parent_role = role.parent
        circular_form = RoleForm(data={'name': 'Test', 'parent': parent_role.pk}, instance=role)
        if not circular_form.is_valid():
            print("✓ Circular reference prevented correctly")
        else:
            print("✗ Circular reference check failed")

    print()

def test_url_patterns():
    """Verify all URL patterns are registered"""
    print("=" * 60)
    print("Testing URL Patterns")
    print("=" * 60)

    from django.urls import resolve, reverse

    urls_to_test = [
        ('accounts:role_management', None, 'role_management'),
        ('accounts:create_role', None, 'create_role'),
        ('accounts:compare_roles', None, 'compare_roles'),
        ('accounts:clone_role', {'role_id': 1}, 'clone_role'),
        ('accounts:edit_role', {'role_id': 1}, 'edit_role'),
        ('accounts:delete_role', {'role_id': 1}, 'delete_role'),
    ]

    for url_name, args, expected_name in urls_to_test:
        try:
            if args:
                url = reverse(url_name, kwargs=args)
            else:
                url = reverse(url_name)
            print(f"✓ {url_name:30} -> {url}")
        except Exception as e:
            print(f"✗ {url_name:30} -> ERROR: {e}")

    print()

def test_template_structure():
    """Verify templates have required blocks and variables"""
    print("=" * 60)
    print("Testing Template Structure")
    print("=" * 60)

    from django.template.loader import get_template

    templates_to_check = [
        'accounts/role_form.html',
        'accounts/compare_roles.html',
        'accounts/role_management.html',
    ]

    for template_name in templates_to_check:
        try:
            template = get_template(template_name)
            print(f"✓ Template loaded: {template_name}")
        except Exception as e:
            print(f"✗ Template error: {template_name} - {e}")

    print()

def main():
    print("\n" + "=" * 60)
    print("RBAC REORGANIZATION IMPLEMENTATION TEST")
    print("=" * 60 + "\n")

    try:
        test_role_model_methods()
        test_role_form_validation()
        test_url_patterns()
        test_template_structure()

        print("=" * 60)
        print("All tests completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Fatal error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
