"""
Context processors for accounts app.

Provides user permissions and role information to all templates.
"""

from django.core.cache import cache

from accounts.permissions import (
    ROLE_PERMISSIONS,
    get_user_accessible_modules,
    get_user_roles,
)

# Empty context for anonymous users (no cache lookup, no DB hit).
_EMPTY = {
    # user_permissions (accounts)
    'user_roles': [],
    'user_role_list': [],
    'user_permissions': {},
    'is_admin_user': False,
    'accessible_modules': [],
    # hms_user_roles (core, now merged)
    'user_is_admin': False,
    'user_is_superuser': False,
    'user_has_medical_roles': False,
    'user_has_management_roles': False,
    'user_can_manage_patients': False,
    'user_can_manage_pharmacy': False,
    'user_can_manage_billing': False,
    'user_can_manage_laboratory': False,
    # hms_permissions (core, now merged) — top-level dump
    'roles': [],
    'is_admin': False,
    'is_superuser': False,
}


def page_user_context(request):
    """Single per-request permission/role context.

    Merges what were three separate context processors
    (accounts.user_permissions, core.hms_permissions, core.hms_user_roles)
    into one cache entry, so every page does ONE cache.get instead of three
    (three DB reads per page under the production DatabaseCache backend).

    Invalidated via accounts.signals.clear_user_permission_cache.
    """
    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated):
        return _EMPTY

    cache_key = f'page_user_ctx_{user.pk}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    user_roles = get_user_roles(user)  # request-cached on the user object
    # Role names are compared against lowercase ROLE_PERMISSIONS keys and literals
    # below; a role stored as "Doctor" must still match. Keep user_roles for display.
    roles_lc = {r.lower() for r in user_roles}
    is_super = user.is_superuser

    perms = {}
    for role_name in roles_lc:
        if role_name in ROLE_PERMISSIONS:
            for perm_key in ROLE_PERMISSIONS[role_name]['permissions']:
                perms[perm_key] = True

    result = {
        # --- accounts.user_permissions ---
        'user_roles': user_roles,
        'user_role_list': user_roles,
        'user_permissions': perms,
        'is_admin_user': 'admin' in roles_lc or is_super,
        'accessible_modules': get_user_accessible_modules(user),
        # --- core.hms_user_roles ---
        'user_is_admin': 'admin' in roles_lc,
        'user_is_superuser': is_super,
        'user_has_medical_roles': bool(roles_lc & {'doctor', 'nurse'}),
        'user_has_management_roles': bool(roles_lc & {'admin', 'accountant', 'health_record_officer', 'receptionist'}),
        'user_can_manage_patients': bool(roles_lc & {'admin', 'receptionist', 'health_record_officer'}),
        'user_can_manage_pharmacy': bool(roles_lc & {'admin', 'pharmacist'}),
        'user_can_manage_billing': bool(roles_lc & {'admin', 'accountant', 'receptionist', 'health_record_officer'}),
        'user_can_manage_laboratory': bool(roles_lc & {'admin', 'lab_technician', 'medical_lab_scientist'}),
    }
    # --- core.hms_permissions (top-level dump) ---
    result.update(perms)
    result['roles'] = user_roles
    result['is_admin'] = 'admin' in roles_lc
    result['is_superuser'] = is_super

    cache.set(cache_key, result, 300)
    return result
