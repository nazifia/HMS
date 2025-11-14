from django import template
from django.contrib.auth.models import User
from core.models import SidebarMenuItem, FeatureFlag
from core.permissions import RolePermissionChecker

register = template.Library()

@register.filter
def has_hms_permission(user, permission_name):
    """
    Template filter to check HMS custom permissions
    Usage: {% if user|has_hms_permission:'view_dashboard' %}
    """
    if not user.is_authenticated:
        return False
    
    checker = RolePermissionChecker(user)
    return checker.has_permission(permission_name)

@register.filter
def has_any_hms_permission(user, permission_list):
    """
    Template filter to check if user has any of the specified permissions
    Usage: {% if user|has_any_hms_permission:'view_patients,create_patient' %}
    """
    if not user.is_authenticated:
        return False
    
    checker = RolePermissionChecker(user)
    permissions = [p.strip() for p in permission_list.split(',')]
    return checker.has_any_permission(*permissions)

@register.filter
def has_all_hms_permission(user, permission_list):
    """
    Template filter to check if user has all of the specified permissions
    Usage: {% if user|has_all_hms_permission:'view_patients,edit_patients' %}
    """
    if not user.is_authenticated:
        return False
    
    checker = RolePermissionChecker(user)
    permissions = [p.strip() for p in permission_list.split(',')]
    return checker.has_all_permissions(*permissions)

@register.inclusion_tag('includes/sidebar_menu.html', takes_context=True)
def render_sidebar(context):
    """
    Render sidebar menu items with permission checking
    """
    request = context.get('request')
    user = request.user if request else None
    
    if not user or not user.is_authenticated:
        return {'menu_items': []}
    
    # Get all active sidebar menu items
    menu_items = SidebarMenuItem.objects.filter(
        is_active=True
    ).select_related(
        'permission_required',
        'parent'
    ).prefetch_related(
        'children',
        'required_roles'
    ).order_by('category', 'order', 'title')
    
    # Filter items based on user permissions
    accessible_items = []
    for item in menu_items:
        if item.has_permission(user):
            accessible_items.append(item)
    
    return {
        'menu_items': accessible_items,
        'user': user,
    }

@register.simple_tag
def get_sidebar_items(user):
    """
    Get sidebar menu items for a specific user
    """
    if not user.is_authenticated:
        return []
    
    menu_items = SidebarMenuItem.objects.filter(
        is_active=True
    ).select_related(
        'permission_required',
        'parent'
    ).prefetch_related(
        'children',
        'required_roles'
    ).order_by('category', 'order', 'title')
    
    accessible_items = []
    for item in menu_items:
        if item.has_permission(user):
            accessible_items.append(item)
    
    return accessible_items

@register.simple_tag
def is_feature_enabled(feature_name, user):
    """
    Check if a feature flag is enabled and user has access
    Usage: {% if 'enhanced_pharmacy_workflow'|is_feature_enabled:user %}
    """
    if not user.is_authenticated:
        return False
    
    try:
        feature = FeatureFlag.objects.get(name=feature_name)
        return feature.is_accessible(user)
    except FeatureFlag.DoesNotExist:
        return False

@register.inclusion_tag('includes/menu_item.html')
def render_menu_item(item, user):
    """
    Render a single menu item with permission checking
    """
    return {
        'item': item,
        'user': user,
        'can_access': item.has_permission(user) if hasattr(item, 'has_permission') else True,
    }

@register.filter
def get_user_permissions(user):
    """
    Get all permissions for a user (HMS custom permissions + Django permissions)
    """
    if not user.is_authenticated:
        return []
    
    permissions = []
    
    # Add HMS custom permissions
    user_hms_permissions = set(
        user.hms_permissions.values_list('permission__codename', flat=True)
    )
    permissions.extend(user_hms_permissions)
    
    # Add role-based HMS permissions
    for role in user.roles.all():
        role_permissions = role.hms_permissions.values_list('permission__codename', flat=True)
        permissions.extend(role_permissions)
    
    # Add Django permissions
    django_permissions = user.user_permissions.values_list('codename', flat=True)
    permissions.extend(django_permissions)
    
    # Add role Django permissions
    for role in user.roles.all():
        role_permissions = role.permissions.values_list('codename', flat=True)
        permissions.extend(role_permissions)
    
    return list(set(permissions))  # Remove duplicates

@register.filter
def get_user_roles(user):
    """
    Get all roles for a user including inherited roles
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
    
    checker = RolePermissionChecker(user)
    permissions = module_permissions[module_name]
    
    return checker.has_any_permission(*permissions)

@register.filter
def get_sidebar_categories(user):
    """
    Get distinct sidebar categories that user has access to
    """
    if not user.is_authenticated:
        return []
    
    menu_items = SidebarMenuItem.objects.filter(
        is_active=True
    )
    
    accessible_categories = set()
    for item in menu_items:
        if item.has_permission(user):
            accessible_categories.add(item.category)
    
    return list(accessible_categories)
