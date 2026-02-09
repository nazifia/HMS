"""
Context processors for accounts app.

Provides user permissions and role information to all templates.
"""

from django.conf import settings
from accounts.permissions import (
    get_user_roles,
    get_user_accessible_modules,
)

def user_permissions(request):
    """
    Add user permissions and role info to all templates.

    This context processor adds:
    - user_roles: List of user's role names
    - user_permissions: Dict of permission keys with True values
    - user_role_list: Alias for user_roles
    - is_admin_user: Boolean indicating admin or superuser status
    - accessible_modules: List of module names user can access

    Usage in templates:
        {% if user_permissions.patients.view %}
            <!-- Show patient data -->
        {% endif %}

        {% if 'doctor' in user_roles %}
            <!-- Doctor-specific content -->
        {% endif %}

        {% if is_admin_user %}
            <!-- Admin-only content -->
        {% endif %}
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {
            'user_roles': [],
            'user_permissions': {},
            'user_role_list': [],
            'is_admin_user': False,
            'accessible_modules': [],
        }

    user = request.user
    user_roles = get_user_roles(user)
    user_permissions = {}

    # Build permission dictionary from all roles (including inheritance)
    for role_name in user_roles:
        from accounts.permissions import ROLE_PERMISSIONS
        if role_name in ROLE_PERMISSIONS:
            for perm_key in ROLE_PERMISSIONS[role_name]['permissions']:
                user_permissions[perm_key] = True

    # Determine admin status
    is_admin = 'admin' in user_roles or user.is_superuser

    # Get accessible modules
    accessible_modules = get_user_accessible_modules(user)

    return {
        'user_roles': user_roles,
        'user_role_list': user_roles,  # Backward compatibility
        'user_permissions': user_permissions,
        'is_admin_user': is_admin,
        'accessible_modules': accessible_modules,
    }
