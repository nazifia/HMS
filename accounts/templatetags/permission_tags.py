"""
Template tags for role-based permissions in HMS
"""

from django import template
from django.contrib.auth.models import Permission
from accounts.permissions import (
    user_has_permission, user_in_role, user_has_any_permission, user_has_all_permissions,
    get_user_roles, can_perform_action, get_role_badge_class, get_role_display_name,
    check_patient_access, check_medical_record_access, check_billing_access, 
    check_pharmacy_access, check_user_management_access
)

register = template.Library()


@register.filter
def has_permission(user, permission):
    """Check if user has specific permission."""
    return user_has_permission(user, permission)


@register.filter
def has_any_permission(user, permissions):
    """Check if user has any of the specified permissions."""
    if isinstance(permissions, str):
        permissions = permissions.split(',')
        permissions = [p.strip() for p in permissions]
    return user_has_any_permission(user, permissions)


@register.filter
def has_all_permissions(user, permissions):
    """Check if user has all of the specified permissions."""
    if isinstance(permissions, str):
        permissions = permissions.split(',')
        permissions = [p.strip() for p in permissions]
    return user_has_all_permissions(user, permissions)


@register.filter
def in_role(user, roles):
    """Check if user has specific role(s)."""
    if isinstance(roles, str):
        roles = roles.split(',')
        roles = [r.strip() for r in roles]
    return user_in_role(user, roles)


@register.filter
def get_user_roles_list(user):
    """Get list of user roles."""
    return get_user_roles(user)


@register.filter
def get_role_badge(user_role):
    """Get Bootstrap badge class for role."""
    return get_role_badge_class(user_role)


@register.filter
def get_role_display(user_role):
    """Get display name for role."""
    return get_role_display_name(user_role)


@register.simple_tag
def can_perform(user, action, context=None):
    """Check if user can perform specific action."""
    return can_perform_action(user, action, context)


@register.simple_tag
def check_patient_permission(user):
    """Check patient access permission."""
    return check_patient_access(user)


@register.simple_tag
def check_medical_permission(user):
    """Check medical record access permission."""
    return check_medical_record_access(user)


@register.simple_tag
def check_billing_permission(user):
    """Check billing access permission."""
    return check_billing_access(user)


@register.simple_tag
def check_pharmacy_permission(user):
    """Check pharmacy access permission."""
    return check_pharmacy_access(user)


@register.simple_tag
def check_user_management_permission(user):
    """Check user management permission."""
    return check_user_management_access(user)


@register.filter
def has_module_access(user, module_name):
    """Check if user has access to specific module."""
    from accounts.permissions import get_user_accessible_modules
    accessible_modules = get_user_accessible_modules(user)
    return module_name in accessible_modules


@register.filter
def can_view(user, resource):
    """Check if user can view specific resource."""
    permission_map = {
        'patient': 'patients.view',
        'medical_record': 'medical.view',
        'vitals': 'vitals.view',
        'consultation': 'consultations.view',
        'referral': 'referrals.view',
        'prescription': 'prescriptions.view',
        'pharmacy': 'pharmacy.view',
        'lab': 'lab.view',
        'billing': 'billing.view',
        'wallet': 'wallet.view',
        'appointment': 'appointments.view',
        'inpatient': 'inpatient.view',
        'user': 'users.view',
        'role': 'roles.view',
        'report': 'reports.view',
    }
    
    if resource in permission_map:
        return user_has_permission(user, permission_map[resource])
    return False


@register.filter
def can_edit(user, resource):
    """Check if user can edit specific resource."""
    permission_map = {
        'patient': 'patients.edit',
        'medical_record': 'medical.edit',
        'vitals': 'vitals.edit',
        'consultation': 'consultations.edit',
        'referral': 'referrals.edit',
        'prescription': 'prescriptions.edit',
        'pharmacy': 'pharmacy.edit',
        'lab': 'lab.edit',
        'billing': 'billing.edit',
        'wallet': 'wallet.edit',
        'appointment': 'appointments.edit',
        'inpatient': 'inpatient.edit',
        'user': 'users.edit',
        'role': 'roles.edit',
    }
    
    if resource in permission_map:
        return user_has_permission(user, permission_map[resource])
    return False


@register.filter
def can_create(user, resource):
    """Check if user can create specific resource."""
    permission_map = {
        'patient': 'patients.create',
        'medical_record': 'medical.create',
        'vitals': 'vitals.create',
        'consultation': 'consultations.create',
        'referral': 'referrals.create',
        'prescription': 'prescriptions.create',
        'pharmacy': 'pharmacy.create',
        'lab': 'lab.create',
        'billing': 'billing.create',
        'wallet': 'wallet.create',
        'appointment': 'appointments.create',
        'inpatient': 'inpatient.create',
        'user': 'users.create',
        'role': 'roles.create',
    }
    
    if resource in permission_map:
        return user_has_permission(user, permission_map[resource])
    return False


@register.filter
def can_delete(user, resource):
    """Check if user can delete specific resource."""
    permission_map = {
        'patient': 'patients.delete',
        'medical_record': 'medical.delete',
        'vitals': 'vitals.delete',
        'consultation': 'consultations.delete',
        'referral': 'referrals.delete',
        'prescription': 'prescriptions.delete',
        'pharmacy': 'pharmacy.delete',
        'lab': 'lab.delete',
        'billing': 'billing.delete',
        'wallet': 'wallet.delete',
        'appointment': 'appointments.delete',
        'inpatient': 'inpatient.delete',
        'user': 'users.delete',
        'role': 'roles.delete',
    }
    
    if resource in permission_map:
        return user_has_permission(user, permission_map[resource])
    return False


@register.filter
def can_process(user, action):
    """Check if user can perform specific processing action."""
    permission_map = {
        'payment': 'billing.process_payment',
        'dispense': 'pharmacy.dispense',
        'discharge': 'inpatient.discharge',
        'generate_report': 'reports.generate',
        'toggle_status': 'patients.toggle_status',
        'manage_wallet': 'patients.wallet_manage',
        'manage_nhia': 'patients.nhia_manage',
    }
    
    if action in permission_map:
        return user_has_permission(user, permission_map[action])
    return False


@register.inclusion_tag('includes/permission_denied.html')
def permission_denied_message(user, required_permission):
    """Display permission denied message."""
    return {
        'user': user,
        'required_permission': required_permission,
    }


@register.filter
def is_super_admin(user):
    """Check if user is super admin."""
    return user.is_superuser


@register.filter
def is_role(user, role_name):
    """Check if user has specific role."""
    return user_in_role(user, [role_name])


@register.filter
def has_any_role(user, roles):
    """Check if user has any of the specified roles."""
    return user_in_role(user, roles)


@register.filter
def has_all_roles(user, roles):
    """Check if user has all of the specified roles."""
    return user_in_all_roles(user, roles)


def user_in_all_roles(user, role_names):
    """Check if user has all of the specified roles."""
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    if isinstance(role_names, str):
        role_names = [role_names]
    
    user_roles = get_user_roles(user)
    return all(role in user_roles for role in role_names)
