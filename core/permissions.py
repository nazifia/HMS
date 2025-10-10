"""
Role-based permission system for HMS
Defines granular permissions and privilege checking utilities
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpRequest
from accounts.models import CustomUser, Role
import logging

logger = logging.getLogger(__name__)

# Define application-specific permissions
APP_PERMISSIONS = {
    'user_management': {
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

class RolePermissionChecker:
    """
    Utility class for role-based permission checking
    """
    
    def __init__(self, user: CustomUser):
        self.user = user
        self._permissions_cache = {}
    
    def has_permission(self, permission_name: str) -> bool:
        """
        Check if user has a specific permission
        
        Args:
            permission_name: Name of the permission to check (e.g., 'create_patient')
            
        Returns:
            bool: True if user has the permission
        """
        # Superusers have all permissions
        if self.user.is_superuser:
            return True
        
        # Check cache first
        if permission_name in self._permissions_cache:
            return self._permissions_cache[permission_name]
        
        # Get all permissions from user's roles
        user_permissions = set()
        for role in self.user.roles.all():
            # Get permissions from role and its parent roles
            role_permissions = role.get_all_permissions()
            user_permissions.update(role_permissions)
        
        # Check if permission exists
        has_perm = permission_name in user_permissions
        self._permissions_cache[permission_name] = has_perm
        
        return has_perm
    
    def has_any_permission(self, *permission_names) -> bool:
        """
        Check if user has any of the specified permissions
        
        Args:
            *permission_names: Variable number of permission names
            
        Returns:
            bool: True if user has any of the permissions
        """
        return any(self.has_permission(perm) for perm in permission_names)
    
    def has_all_permissions(self, *permission_names) -> bool:
        """
        Check if user has all of the specified permissions
        
        Args:
            *permission_names: Variable number of permission names
            
        Returns:
            bool: True if user has all permissions
        """
        return all(self.has_permission(perm) for perm in permission_names)
    
    def get_user_permissions(self) -> set:
        """
        Get all permissions available to the user
        
        Returns:
            set: Set of permission names
        """
        if self.user.is_superuser:
            return {perm_name for category_perms in APP_PERMISSIONS.values() for perm_name in category_perms.keys()}
        
        user_permissions = set()
        for role in self.user.roles.all():
            role_permissions = role.get_all_permissions()
            user_permissions.update(role_permissions)
        
        return user_permissions
    
    def get_permissions_by_category(self, category: str) -> set:
        """
        Get user permissions for a specific category
        
        Args:
            category: Category name (e.g., 'patient_management')
            
        Returns:
            set: Set of permission names for that category
        """
        if category not in APP_PERMISSIONS:
            return set()
        
        category_perms = set(APP_PERMISSIONS[category].keys())
        user_perms = self.get_user_permissions()
        return category_perms.intersection(user_perms)

def permission_required(permission_names: list, category: str = None, redirect_url: str = None):
    """
    Decorator to require specific permissions for a view
    
    Args:
        permission_names: List of permission names required
        category: Optional category for permissions (for validation)
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
            
            # Create permission checker
            checker = RolePermissionChecker(request.user)
            
            # Check permissions
            if isinstance(permission_names, str):
                # Single permission
                has_permission = checker.has_permission(permission_names)
            else:
                # Multiple permissions - require all
                has_permission = checker.has_all_permissions(*permission_names)
            
            if not has_permission:
                messages.error(request, "You don't have permission to access this page.")
                redirect_target = redirect_url or 'dashboard:dashboard'
                return redirect(redirect_target)
            
            # Log the access
            logger.info(f"User {request.user.username} accessed {request.path} with required permissions")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def any_permission_required(permission_names: list, redirect_url: str = None):
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
            
            checker = RolePermissionChecker(request.user)
            has_permission = checker.has_any_permission(*permission_names)
            
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
    
    checker = RolePermissionChecker(request.user)
    
    if isinstance(permission_names, str):
        return checker.has_permission(permission_names)
    else:
        return checker.has_all_permissions(*permission_names)
