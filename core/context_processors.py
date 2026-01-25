"""
Context processors for HMS permissions
"""

from accounts.permissions import user_permissions_context


def hms_permissions(request):
    """Add HMS permission context to all templates."""
    return user_permissions_context(request)


def hms_user_roles(request):
    """Add user roles information to template context."""
    if hasattr(request, 'user') and request.user.is_authenticated:
        from accounts.permissions import get_user_roles
        
        user_roles = get_user_roles(request.user)
        
        return {
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
    
    return {
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
