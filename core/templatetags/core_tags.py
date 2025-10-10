"""
Template tags for core functionality and role-based UI
"""

from django import template
from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe

from core.permissions import RolePermissionChecker

register = template.Library()
User = get_user_model()

@register.filter
def has_role(user, role_name):
    """Check if user has a specific role"""
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    return role_name in user.get_role_list() if hasattr(user, 'get_role_list') else False

@register.filter
def has_permission(user, permission_name):
    """Check if user has a specific permission"""
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    checker = RolePermissionChecker(user)
    return checker.has_permission(permission_name)

@register.filter
def get_user_roles(user):
    """Get user's roles as a comma-separated string"""
    if not user or not user.is_authenticated:
        return ""
    
    if user.is_superuser:
        return "Superuser"
    
    roles = [role.name for role in user.roles.all()] if hasattr(user, 'roles') else []
    return ", ".join(roles) if roles else "No roles assigned"

@register.filter
def get_role_badge_class(role_name):
    """Get appropriate Bootstrap badge class for role"""
    role_badges = {
        'admin': 'bg-danger',
        'doctor': 'bg-success',
        'nurse': 'bg-info',
        'pharmacist': 'bg-warning',
        'lab_technician': 'bg-purple',
        'radiology_staff': 'bg-teal',
        'accountant': 'bg-warning text-dark',
        'receptionist': 'bg-primary',
        'health_record_officer': 'bg-secondary',
    }
    
    return role_badges.get(role_name.lower(), 'bg-secondary')

@register.simple_tag(takes_context=True)
def user_can_access(context, permission_list):
    """Check if current user can access any of the given permissions"""
    user = context['user']
    
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    checker = RolePermissionChecker(user)
    
    if isinstance(permission_list, str):
        permission_list = [permission_list]
    
    return any(checker.has_permission(perm) for perm in permission_list)

@register.simple_tag(takes_context=True)
def get_permission_indicator(context, permission_name):
    """Get UI indicator for permission status"""
    user = context['user']
    
    if has_permission(user, permission_name):
        return mark_safe('<i class="fas fa-check-circle text-success"></i>')
    else:
        return mark_safe('<i class="fas fa-times-circle text-danger"></i>')

@register.simple_tag
def activity_log_level_badge(level):
    """Get Bootstrap badge class for activity log level"""
    level_badges = {
        'debug': 'bg-secondary',
        'info': 'bg-info',
        'warning': 'bg-warning',
        'error': 'bg-danger',
        'critical': 'bg-danger',
    }
    return level_badges.get(level.lower(), 'bg-secondary')

@register.simple_tag
def action_type_icon(action_type):
    """Get icon for action type"""
    action_icons = {
        'create': 'fas fa-plus-circle',
        'update': 'fas fa-edit',
        'delete': 'fas fa-trash',
        'view': 'fas fa-eye',
        'login': 'fas fa-sign-in-alt',
        'logout': 'fas fa-sign-out-alt',
        'failed_login': 'fas fa-exclamation-triangle',
        'permission_denied': 'fas fa-ban',
        'export': 'fas fa-download',
        'import': 'fas fa-upload',
        'print': 'fas fa-print',
        'search': 'fas fa-search',
        'filter': 'fas fa-filter',
        'sort': 'fas fa-sort',
        'download': 'fas fa-download',
        'upload': 'fas fa-upload',
        'authorize': 'fas fa-shield-alt',
        'approve': 'fas fa-check',
        'reject': 'fas fa-times',
        'cancel': 'fas fa-ban',
        'reschedule': 'fas fa-calendar-alt',
        'transfer': 'fas fa-exchange-alt',
        'dispense': 'fas fa-pills',
        'prescribe': 'fas fa-prescription',
        'admit': 'fas fa-bed',
        'discharge': 'fas fa-door-open',
        'settle': 'fas fa-money-bill-wave',
        'refund': 'fas fa-undo',
    }
    return action_icons.get(action_type, 'fas fa-circle')

@register.filter
def truncate_chars(value, arg):
    """Truncate string to specified number of characters"""
    try:
        length = int(arg)
    except ValueError:
        return value
    
    if len(value) <= length:
        return value
    else:
        return value[:length] + '...'

@register.simple_tag
def format_timestamp(timestamp, format_type='default'):
    """Format timestamp for display"""
    if not timestamp:
        return "N/A"
    
    if format_type == 'short':
        return timestamp.strftime('%b %d, %Y %H:%M')
    elif format_type == 'date_only':
        return timestamp.strftime('%b %d, %Y')
    elif format_type == 'time_only':
        return timestamp.strftime('%H:%M:%S')
    else:
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')

@register.simple_tag
def get_session_status_class(session_info):
    """Get CSS class for session status"""
    if not session_info:
        return ''
    
    time_remaining = session_info.get('time_remaining', 0)
    warning_threshold = session_info.get('warning_threshold', 300)
    
    if time_remaining <= 60:
        return 'session-expired'
    elif time_remaining <= warning_threshold:
        return 'session-warning'
    else:
        return 'session-active'

@register.simple_tag
def format_response_time(response_time_ms):
    """Format response time for display"""
    if not response_time_ms:
        return "N/A"
    
    if response_time_ms < 1000:
        return f"{response_time_ms}ms"
    elif response_time_ms < 60000:
        return f"{response_time_ms/1000:.2f}s"
    else:
        return f"{response_time_ms/60000:.2f}min"

@register.filter
def user_role_display(user):
    """Display user's primary role"""
    if not user or not user.is_authenticated:
        return "Anonymous"
    
    if user.is_superuser:
        return "Superuser"
    
    if hasattr(user, 'profile') and user.profile.role:
        return user.profile.role.replace('_', ' ').title()
    
    if hasattr(user, 'roles'):
        roles = list(user.roles.values_list('name', flat=True))
        if roles:
            return roles[0].replace('_', ' ').title()
    
    return "User"

@register.simple_tag(takes_context=True)
def is_admin_user(context):
    """Check if current user is admin or superuser"""
    user = context.get('user')
    return user.is_authenticated and (user.is_superuser or 
                                    (hasattr(user, 'profile') and user.profile.role == 'admin'))

@register.simple_tag(takes_context=True)
def can_view_sensitive_data(context):
    """Check if user can view sensitive patient data"""
    user = context.get('user')
    if not user or not user.is_authenticated:
        return False
    
    # Superusers can see everything
    if user.is_superuser:
        return True
    
    # Check for roles that should have access to sensitive data
    sensitive_data_roles = ('admin', 'doctor', 'nurse')
    user_roles = [role.name for role in user.roles.all()] if hasattr(user, 'roles') else []
    
    return any(role in user_roles for role in sensitive_data_roles)

@register.filter
def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if not size_bytes:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"

@register.simple_tag
def get_activity_category_display(category):
    """Get display name for activity category"""
    category_names = {
        'authentication': 'Authentication',
        'user_management': 'User Management',
        'patient_management': 'Patient Management',
        'billing': 'Billing',
        'pharmacy': 'Pharmacy',
        'laboratory': 'Laboratory',
        'radiology': 'Radiology',
        'appointment': 'Appointments',
        'inpatient': 'Inpatient',
        'system': 'System',
        'security': 'Security',
        'data_access': 'Data Access',
        'admin_action': 'Admin Action',
    }
    return category_names.get(category, category.replace('_', ' ').title())

@register.simple_tag
def get_action_type_display(action_type):
    """Get display name for action type"""
    action_names = {
        'create': 'Create',
        'update': 'Update',
        'delete': 'Delete',
        'view': 'View',
        'login': 'Login',
        'logout': 'Logout',
        'failed_login': 'Failed Login',
        'permission_denied': 'Permission Denied',
        'export': 'Export',
        'import': 'Import',
        'print': 'Print',
        'search': 'Search',
        'filter': 'Filter',
        'sort': 'Sort',
        'download': 'Download',
        'upload': 'Upload',
        'authorize': 'Authorize',
        'approve': 'Approve',
        'reject': 'Reject',
        'cancel': 'Cancel',
        'reschedule': 'Reschedule',
        'transfer': 'Transfer',
        'dispense': 'Dispense',
        'prescribe': 'Prescribe',
        'admit': 'Admit',
        'discharge': 'Discharge',
        'settle': 'Settle',
        'refund': 'Refund',
    }
    return action_names.get(action_type, action_type.replace('_', ' ').title())
