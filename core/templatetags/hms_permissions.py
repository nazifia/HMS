from django import template
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def has_permission(user, permission_name):
    """
    Template filter to check permissions using the HMS RBAC system.
    Supports both custom permission keys (e.g., 'patients.view') and Django codenames.
    Usage: {% if user|has_permission:'consultations.view' %}
    """
    if not user.is_authenticated:
        return False

    # Superusers have all permissions
    if user.is_superuser:
        return True

    # Use the accounts permission system which handles proper permission mapping
    from accounts.permissions import user_has_permission

    return user_has_permission(user, permission_name)


@register.filter
def has_role(user, role_name):
    """
    Check if user has a specific role.
    Usage: {% if user|has_role:'admin' %}
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    # Check ManyToMany roles
    if user.roles.filter(name=role_name).exists():
        return True

    # Check legacy profile role
    profile_role = getattr(getattr(user, "profile", None), "role", None)
    return profile_role == role_name


@register.filter
def has_any_permission(user, permission_list):
    """
    Template filter to check if user has any of the specified permissions
    Usage: {% if user|has_any_permission:'view_patients,create_patient' %}
    """
    if not user.is_authenticated:
        return False

    permissions = [p.strip() for p in permission_list.split(",")]

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

    permissions = [p.strip() for p in permission_list.split(",")]

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
        "dashboard": ["view_dashboard"],
        "patients": ["view_patients", "create_patient"],
        "consultations": ["access_sensitive_data", "create_consultation"],
        "appointments": ["view_appointments", "create_appointment"],
        "pharmacy": ["view_pharmacy", "manage_pharmacy_inventory"],
        "laboratory": ["view_laboratory", "create_lab_test"],
        "radiology": ["view_radiology", "create_radiology_request"],
        "billing": ["view_invoices", "create_invoice"],
        "reports": ["view_reports", "view_analytics"],
        "administration": ["view_user_management", "manage_roles"],
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


# ==================== NEW UI PERMISSION SYSTEM ====================


@register.filter
def can_show_ui(user, element_id):
    """
    Check if a UI element should be shown to the user.
    Usage: {% if user|can_show_ui:'btn_create_patient' %}

    Args:
        user: The user object
        element_id: The unique identifier of the UI element

    Returns:
        bool: True if user can access the UI element
    """
    if not user or not user.is_authenticated:
        return False

    # Superusers can see everything
    if user.is_superuser:
        return True

    # Try to get from cache first for performance
    cache_key = f"ui_perm_{user.id}_{element_id}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    # Import here to avoid circular imports
    from core.models import UIPermission

    try:
        ui_perm = UIPermission.objects.prefetch_related(
            "required_permissions", "required_roles"
        ).get(element_id=element_id, is_active=True)

        result = ui_perm.user_can_access(user)

        # Cache the result for 5 minutes
        cache.set(cache_key, result, 300)

        return result
    except UIPermission.DoesNotExist:
        # If no UI permission defined, allow access by default (backward compatibility)
        cache.set(cache_key, True, 300)
        return True


@register.filter
def can_show_any_ui(user, element_ids):
    """
    Check if user can access ANY of the specified UI elements.
    Usage: {% if user|can_show_any_ui:'btn_create,btn_edit,btn_delete' %}

    Args:
        user: The user object
        element_ids: Comma-separated list of element IDs

    Returns:
        bool: True if user can access at least one element
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    element_list = [e.strip() for e in element_ids.split(",")]

    for element_id in element_list:
        if can_show_ui(user, element_id):
            return True

    return False


@register.filter
def can_show_all_ui(user, element_ids):
    """
    Check if user can access ALL of the specified UI elements.
    Usage: {% if user|can_show_all_ui:'btn_create,btn_edit,btn_delete' %}

    Args:
        user: The user object
        element_ids: Comma-separated list of element IDs

    Returns:
        bool: True if user can access all elements
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    element_list = [e.strip() for e in element_ids.split(",")]

    for element_id in element_list:
        if not can_show_ui(user, element_id):
            return False

    return True


@register.simple_tag
def ui_element_visible(user, element_id):
    """
    Simple tag version of can_show_ui for more complex usage.
    Usage: {% ui_element_visible user 'btn_create_patient' as can_create %}
    """
    return can_show_ui(user, element_id)


@register.simple_tag(takes_context=True)
def render_ui_if_allowed(context, element_id, content=""):
    """
    Render content only if user has permission for the UI element.
    Usage: {% render_ui_if_allowed 'btn_create' 'Button HTML here' %}
    """
    user = context.get("user")

    if can_show_ui(user, element_id):
        return mark_safe(content)

    return ""


@register.inclusion_tag("core/ui_permission_indicator.html")
def show_permission_indicator(user, element_id):
    """
    Display a visual indicator of permission status.
    Usage: {% show_permission_indicator user 'btn_create_patient' %}
    """
    can_access = can_show_ui(user, element_id)

    return {
        "can_access": can_access,
        "element_id": element_id,
        "user": user,
    }


@register.simple_tag
def get_user_ui_elements(user, module=None):
    """
    Get all UI elements accessible to the user, optionally filtered by module.
    Usage: {% get_user_ui_elements user 'patients' as patient_ui_elements %}

    Args:
        user: The user object
        module: Optional module filter

    Returns:
        QuerySet of UIPermission objects user can access
    """
    if not user or not user.is_authenticated:
        return []

    from core.models import UIPermission

    # Superusers get all active elements
    if user.is_superuser:
        queryset = UIPermission.objects.filter(is_active=True)
        if module:
            queryset = queryset.filter(module=module)
        return queryset.order_by("display_order", "element_label")

    # Filter elements user can access
    accessible_elements = []

    queryset = UIPermission.objects.filter(is_active=True).prefetch_related(
        "required_permissions", "required_roles"
    )

    if module:
        queryset = queryset.filter(module=module)

    for ui_element in queryset:
        if ui_element.user_can_access(user):
            accessible_elements.append(ui_element)

    return accessible_elements


@register.filter
def ui_elements_by_type(ui_elements, element_type):
    """
    Filter UI elements by type.
    Usage: {{ user_ui_elements|ui_elements_by_type:'menu_item' }}
    """
    return [elem for elem in ui_elements if elem.element_type == element_type]


@register.filter
def has_ui_access(user, element_id):
    """
    Alias for can_show_ui for backward compatibility.
    Usage: {% if user|has_ui_access:'btn_create_patient' %}
    """
    return can_show_ui(user, element_id)
