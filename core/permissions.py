"""
Simplified permission system for HMS
Removed HMS Custom Permissions logic
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpRequest
from accounts.models import CustomUser, Role
from accounts.permissions import ROLE_PERMISSIONS
import logging

logger = logging.getLogger(__name__)

# Define application-specific permissions (simplified)
APP_PERMISSIONS = {
    'user_management': {
        'view_dashboard': 'Can view the main dashboard and system overview',
        'view_user_management': 'Can access user and role management areas',
        'view_admin_tools': 'Can access admin and security tools',
        'create_user': 'Can create new users',
        'edit_user': 'Can edit existing users',
        'delete_user': 'Can delete users',
        'view_users': 'Can view user list and details',
        'manage_roles': 'Can assign and manage user roles',
        'reset_password': 'Can reset user passwords',
    },
    'patient_management': {
        'create_patient': 'Can register new patients',
        'edit_patient': 'Can edit patient information',
        'delete_patient': 'Can delete patient records',
        'view_patients': 'Can view patient list and details',
        'access_sensitive_data': 'Can access sensitive patient data (medical history, etc.)',
        'manage_patient_admission': 'Can manage patient admissions',
        'manage_patient_discharge': 'Can manage patient discharges',
    },
    'billing_management': {
        'create_invoice': 'Can create invoices',
        'edit_invoice': 'Can edit existing invoices',
        'delete_invoice': 'Can delete invoices',
        'view_invoices': 'Can view invoice list and details',
        'process_payments': 'Can process payments and receipts',
        'manage_wallet': 'Can manage patient wallet operations',
        'view_financial_reports': 'Can view financial reports',
    },
    'pharmacy_management': {
        'manage_inventory': 'Can manage pharmacy inventory',
        'dispense_medication': 'Can dispense medications',
        'create_prescription': 'Can create prescription orders',
        'edit_prescription': 'Can edit existing prescriptions',
        'view_prescriptions': 'Can view prescription history',
        'manage_dispensary': 'Can manage dispensary operations',
        'transfer_medication': 'Can transfer medication between dispensaries',
        'can_approve_purchases': 'Can approve purchase orders',
        'can_process_payments': 'Can process purchase payments',
    },
    'laboratory_management': {
        'create_test_request': 'Can create lab test requests',
        'enter_results': 'Can enter lab test results',
        'edit_results': 'Can edit lab test results',
        'view_tests': 'Can view lab test requests and results',
        'manage_lab_equipment': 'Can manage laboratory equipment',
    },
    'radiology_management': {
        'create_radiology_request': 'Can create radiology requests',
        'enter_radiology_results': 'Can enter radiology results',
        'edit_radiology_results': 'Can edit radiology results',
        'view_radiology': 'Can view radiology requests and results',
    },
    'appointment_management': {
        'create_appointment': 'Can create new appointments',
        'edit_appointment': 'Can edit existing appointments',
        'cancel_appointment': 'Can cancel appointments',
        'view_appointments': 'Can view appointment schedules',
        'manage_appointment_types': 'Can manage appointment types and settings',
    },
    'inpatient_management': {
        'manage_admission': 'Can manage patient admissions',
        'manage_vitals': 'Can record patient vitals',
        'manage_medication': 'Can manage inpatient medications',
        'view_inpatient_records': 'Can view inpatient records',
        'manage_discharge': 'Can manage patient discharge',
    },
    'reporting': {
        'view_laboratory_reports': 'Can view laboratory report dashboard',
        'view_reports': 'Can view system reports',
        'generate_reports': 'Can generate custom reports',
        'export_data': 'Can export data from the system',
        'view_analytics': 'Can view system analytics and dashboards',
    },
    'system_administration': {
        'system_configuration': 'Can configure system settings',
        'manage_departments': 'Can manage hospital departments',
        'view_audit_logs': 'Can view system audit logs',
        'backup_data': 'Can perform system backups',
        'system_maintenance': 'Can perform system maintenance tasks',
    }
}

def check_user_permission(user, permission_name):
    """
    Check if user has a specific permission using Django's built-in permission system
    
    Args:
        user: CustomUser instance
        permission_name: Name of the permission to check
        
    Returns:
        bool: True if user has the permission
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

def permission_required(permission_names, redirect_url=None):
    """
    Decorator that requires specific permissions
    
    Args:
        permission_names: Single permission name or list of permission names
        redirect_url: URL to redirect to if permission denied (default: dashboard)
    
    Usage:
        @permission_required(['create_patient', 'edit_patient'])
        def patient_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "You must be logged in to access this page.")
                return redirect('accounts:login')
            
            # Check permissions
            if isinstance(permission_names, str):
                # Single permission
                has_permission = check_user_permission(request.user, permission_names)
            else:
                # Multiple permissions - require all
                has_permission = all(check_user_permission(request.user, perm) for perm in permission_names)
            
            if not has_permission:
                messages.error(request, "You don't have permission to access this page.")
                redirect_target = redirect_url or 'dashboard:dashboard'
                return redirect(redirect_target)
            
            # Log the access
            logger.info(f"User {request.user.username} accessed {request.path} with required permissions")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def any_permission_required(permission_names, redirect_url=None):
    """
    Decorator that requires any of the specified permissions
    
    Args:
        permission_names: List of permission names (user needs at least one)
        redirect_url: URL to redirect to if permission denied
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "You must be logged in to access this page.")
                return redirect('accounts:login')
            
            has_permission = any(check_user_permission(request.user, perm) for perm in permission_names)
            
            if not has_permission:
                messages.error(request, "You don't have permission to access this page.")
                redirect_target = redirect_url or 'dashboard:dashboard'
                return redirect(redirect_target)
            
            logger.info(f"User {request.user.username} accessed {request.path} with permission check")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def get_client_ip(request: HttpRequest) -> str:
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def check_permission_ajax(request: HttpRequest, permission_names: list) -> bool:
    """
    Check permissions for AJAX requests
    
    Args:
        request: HTTP request object
        permission_names: List of permission names to check
        
    Returns:
        bool: True if user has permissions
    """
    if not request.user.is_authenticated:
        return False
    
    if isinstance(permission_names, str):
        return check_user_permission(request.user, permission_names)
    else:
        return any(check_user_permission(request.user, perm) for perm in permission_names)

# Simplified permission checking function for backward compatibility
def has_permission(user, permission_name):
    """Simplified permission check"""
    return check_user_permission(user, permission_name)
