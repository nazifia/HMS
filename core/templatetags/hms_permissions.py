from django import template
from django.contrib.auth.models import User

register = template.Library()

@register.filter
def has_permission(user, permission_name):
    """
    Template filter to check basic permissions using Django's built-in system
    Usage: {% if user|has_permission:'view_dashboard' %}
    """
    if not user.is_authenticated:
        return False
    
    # Superusers have all permissions
    if user.is_superuser:
        return True
    
    # Check direct user permissions
    if user.user_permissions.filter(codename=permission_name).exists():
        return True
    
    # Check permissions from user's roles
    for role in user.roles.all():
        if role.permissions.filter(codename=permission_name).exists():
            return True
    
    return False

@register.filter
def has_any_permission(user, permission_list):
    """
    Template filter to check if user has any of the specified permissions
    Usage: {% if user|has_any_permission:'view_patients,create_patient' %}
    """
    if not user.is_authenticated:
        return False
    
    permissions = [p.strip() for p in permission_list.split(',')]
    
    for permission in permissions:
        if has_permission(user, permission):
            return True
    
    return False

@register.filter
def has_all_permissions(user, permission_list):
    """
    Template filter to check if user has all of the specified permissions
    Usage: {% if user|has_all_permissions:'view_patients,edit_patients' %}
    """
    if not user.is_authenticated:
        return False
    
    permissions = [p.strip() for p in permission_list.split(',')]
    
    for permission in permissions:
        if not has_permission(user, permission):
            return False
    
    return True

@register.filter
def get_user_roles(user):
    """
    Get all roles for a user
    """
    if not user.is_authenticated:
        return []
    
    roles = []
    for role_relation in user.roles.all():
        roles.append(role_relation.name)
        parent = role_relation.parent
        while parent:
            roles.append(parent.name)
            parent = parent.parent
    
    return list(set(roles))

@register.filter
def can_access_module(user, module_name):
    """
    Check if user can access a specific module
    """
    if not user.is_authenticated:
        return False
    
    # Module permission mappings
    module_permissions = {
        'dashboard': ['view_dashboard'],
        'patients': ['view_patients', 'create_patient'],
        'consultations': ['access_sensitive_data', 'create_consultation'],
        'appointments': ['view_appointments', 'create_appointment'],
        'pharmacy': ['view_pharmacy', 'manage_pharmacy_inventory'],
        'laboratory': ['view_laboratory', 'create_lab_test'],
        'radiology': ['view_radiology', 'create_radiology_request'],
        'billing': ['view_invoices', 'create_invoice'],
        'reports': ['view_reports', 'view_analytics'],
        'administration': ['view_user_management', 'manage_roles'],
    }
    
    if module_name not in module_permissions:
        return False
    
    permissions = module_permissions[module_name]
    
    return any(has_permission(user, perm) for perm in permissions)

# Legacy aliases for backward compatibility
@register.filter
def has_hms_permission(user, permission_name):
    """
    Legacy alias for has_permission - maintained for backward compatibility
    Usage: {% if user|has_hms_permission:'view_dashboard' %}
    """
    return has_permission(user, permission_name)

@register.filter
def has_any_hms_permission(user, permission_list):
    """
    Legacy alias for has_any_permission - maintained for backward compatibility
    Usage: {% if user|has_any_hms_permission:'view_patients,create_patient' %}
    """
    return has_any_permission(user, permission_list)

@register.filter
def has_all_hms_permission(user, permission_list):
    """
    Legacy alias for has_all_permissions - maintained for backward compatibility
    Usage: {% if user|has_all_hms_permission:'view_patients,edit_patients' %}
    """
    return has_all_permissions(user, permission_list)

@register.filter
def is_feature_enabled(feature_name, user):
    """
    Legacy feature flag check - always returns True for backward compatibility
    Usage: {% if 'enhanced_pharmacy_workflow'|is_feature_enabled:user %}
    """
    # Since we removed feature flags, always return True
    return True
