"""
Comprehensive permission template tags for HMS RBAC system.

This module provides a wide range of template tags for checking permissions,
roles, and access control in templates. It serves as the single source for
all permission-related template functionality.
"""

from django import template
from django.contrib.auth.models import AnonymousUser
from accounts.permissions import (
    user_has_permission,
    user_has_any_permission,
    user_has_all_permissions,
    user_in_role,
    user_in_all_roles,
    get_user_roles,
    get_role_badge_class,
    get_role_display_name,
    get_user_accessible_modules,
    PERMISSION_DEFINITIONS,
    get_permission_info,
    can_perform_action,
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


# ============================================================================
# Additional comprehensive template tags (new in reorganization)
# ============================================================================

@register.simple_tag
def has_permission(user, permission_key):
    """
    Check if user has a specific permission.

    Usage:
        {% has_permission user 'patients.view' as can_view_patient %}
        {% if can_view_patient %}
            <!-- Show patient data -->
        {% endif %}
    """
    if not user or isinstance(user, AnonymousUser):
        return False
    return user_has_permission(user, permission_key)


@register.simple_tag
def in_role(user, role_name):
    """
    Check if user has a specific role (or any of multiple roles).

    Usage:
        {% in_role user 'doctor' as is_doctor %}
        {% if is_doctor %}
            <!-- Doctor-specific content -->
        {% endif %}

    Multiple roles:
        {% in_role user 'admin,doctor' as is_medical_staff %}
    """
    if not user or isinstance(user, AnonymousUser):
        return False
    if isinstance(role_name, str) and ',' in role_name:
        role_names = [r.strip() for r in role_name.split(',')]
    else:
        role_names = role_name
    return user_in_role(user, role_names)


@register.simple_tag(takes_context=True)
def can_edit_object(context, obj):
    """
    Check if user can edit a specific object based on model and permissions.

    Usage:
        {% can_edit_object patient as can_edit %}
        {% if can_edit %}
            <a href="{% url 'patients:edit' patient.id %}">Edit</a>
        {% endif %}
    """
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return False

    user = request.user
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    # Get model name from object
    model_name = obj.__class__.__name__

    # Map models to required permission
    permission_map = {
        'Patient': 'patients.edit',
        'MedicalHistory': 'medical.edit',
        'VitalSign': 'vitals.edit',
        'Consultation': 'consultations.edit',
        'Referral': 'referrals.edit',
        'Prescription': 'prescriptions.edit',
        'Invoice': 'billing.edit',
        'Admission': 'inpatient.edit',
        'Appointment': 'appointments.edit',
        'LabTest': 'lab.edit',
    }

    required_perm = permission_map.get(model_name)
    if required_perm:
        return user_has_permission(user, required_perm)

    return False


@register.simple_tag(takes_context=True)
def can_view_object(context, obj):
    """
    Check if user can view a specific object.

    Usage:
        {% can_view_object patient as can_view %}
    """
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return False

    user = request.user
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    model_name = obj.__class__.__name__

    permission_map = {
        'Patient': 'patients.view',
        'MedicalHistory': 'medical.view',
        'VitalSign': 'vitals.view',
        'Consultation': 'consultations.view',
        'Referral': 'referrals.view',
        'Prescription': 'prescriptions.view',
        'Invoice': 'billing.view',
        'Admission': 'inpatient.view',
        'Appointment': 'appointments.view',
        'LabTest': 'lab.view',
    }

    required_perm = permission_map.get(model_name)
    if required_perm:
        return user_has_permission(user, required_perm)

    return False


@register.simple_tag(takes_context=True)
def can_delete_object(context, obj):
    """
    Check if user can delete a specific object.

    Usage:
        {% can_delete_object patient as can_delete %}
    """
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return False

    user = request.user
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    model_name = obj.__class__.__name__

    permission_map = {
        'Patient': 'patients.delete',
        'MedicalHistory': 'medical.delete',
        'VitalSign': 'vitals.delete',
        'Consultation': 'consultations.delete',
        'Referral': 'referrals.delete',
        'Prescription': 'prescriptions.delete',
        'Invoice': 'billing.delete',
        'Admission': 'inpatient.delete',
    }

    required_perm = permission_map.get(model_name)
    if required_perm:
        return user_has_permission(user, required_perm)

    return False


@register.filter
def role_badge(role_name, size=''):
    """
    Return HTML for a role badge with appropriate Bootstrap styling.

    Usage:
        {{ role_name|role_badge }}
        {{ role_name|role_badge:"sm" }}
    """
    badge_class = get_role_badge_class(role_name)

    size_classes = {
        'sm': 'badge-sm',
        'lg': 'badge-lg',
        '': ''
    }
    size_class = size_classes.get(size, '')

    display_name = get_role_display_name(role_name)

    return f'<span class="badge {badge_class} {size_class}">{display_name}</span>'


@register.simple_tag(takes_context=True)
def permission_info(context, permission_key):
    """
    Get metadata for a permission.

    Usage:
        {% permission_info 'patients.view' as perm_info %}
        {{ perm_info.description }}
    """
    info = get_permission_info(permission_key)
    if info:
        return info
    return {}


@register.simple_tag
def get_permission_categories():
    """
    Get all permission categories.

    Usage:
        {% get_permission_categories as categories %}
        {% for category in categories %}
            <h3>{{ category|title }}</h3>
        {% endfor %}
    """
    from accounts.permissions import get_all_categories
    return get_all_categories()


@register.simple_tag
def get_category_permissions(category_name):
    """
    Get all permissions in a category.

    Usage:
        {% get_category_permissions 'patient_management' as perms %}
        {% for perm in perms %}
            {{ perm }}
        {% endfor %}
    """
    from accounts.permissions import get_permissions_by_category
    return get_permissions_by_category(category_name)


@register.simple_tag(takes_context=True)
def user_can(context, action):
    """
    Check if user can perform a high-level action.

    Usage:
        {% user_can request.user 'view_patient' as can_view %}
    """
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return False

    user = request.user
    if not user.is_authenticated:
        return False

    return can_perform_action(user, action)


@register.filter
def permission_description(permission_key):
    """
    Get description for a permission.

    Usage:
        {{ 'patients.view'|permission_description }}
    """
    info = get_permission_info(permission_key)
    if info:
        return info.get('description', '')
    return ''


@register.simple_tag
def has_multiple_roles(user):
    """
    Check if user has multiple roles (more than one).

    Usage:
        {% has_multiple_roles request.user as multi_roles %}
    """
    if not user or isinstance(user, AnonymousUser):
        return False
    roles = get_user_roles(user)
    return len(roles) > 1


@register.simple_tag(takes_context=True)
def visible_modules(context):
    """
    Get list of modules visible to the current user.

    Usage:
        {% visible_modules as modules %}
        {% for module in modules %}
            <a href="{% url module ':dashboard' %}">{{ module|title }}</a>
        {% endfor %}
    """
    request = context.get('request')
    if not request or not hasattr(request, 'user'):
        return []

    user = request.user
    if not user.is_authenticated:
        return []

    return get_user_accessible_modules(user)
