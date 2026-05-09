"""
Context processors for HMS permissions
"""

from accounts.permissions import user_permissions_context


def hms_permissions(request):
    """Add HMS permission context to all templates."""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return user_permissions_context(request)
    from django.core.cache import cache
    cache_key = f'hms_perms_ctx_{request.user.pk}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    result = user_permissions_context(request)
    cache.set(cache_key, result, 300)
    return result


def hms_user_roles(request):
    """Add user roles information to template context."""
    empty = {
        'user_roles': [],
        'user_is_admin': False,
        'user_is_superuser': False,
        'user_has_medical_roles': False,
        'user_has_management_roles': False,
        'user_can_manage_patients': False,
        'user_can_manage_pharmacy': False,
        'user_can_manage_billing': False,
        'user_can_manage_laboratory': False,
    }
    if not (hasattr(request, 'user') and request.user.is_authenticated):
        return empty

    from django.core.cache import cache
    cache_key = f'hms_roles_ctx_{request.user.pk}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    from accounts.permissions import get_user_roles
    user_roles = get_user_roles(request.user)

    result = {
        'user_roles': user_roles,
        'user_is_admin': 'admin' in user_roles,
        'user_is_superuser': request.user.is_superuser,
        'user_has_medical_roles': any(role in user_roles for role in ['doctor', 'nurse']),
        'user_has_management_roles': any(role in user_roles for role in ['admin', 'accountant', 'health_record_officer', 'receptionist']),
        'user_can_manage_patients': any(role in user_roles for role in ['admin', 'receptionist', 'health_record_officer']),
        'user_can_manage_pharmacy': any(role in user_roles for role in ['admin', 'pharmacist']),
        'user_can_manage_billing': any(role in user_roles for role in ['admin', 'accountant', 'receptionist', 'health_record_officer']),
        'user_can_manage_laboratory': any(role in user_roles for role in ['admin', 'lab_technician']),
    }
    cache.set(cache_key, result, 300)
    return result
