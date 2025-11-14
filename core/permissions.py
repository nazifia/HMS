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
from accounts.permissions import ROLE_PERMISSIONS
import logging

logger = logging.getLogger(__name__)

# Define application-specific permissions
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

# Mapping between role-based permissions and core permissions for sidebar access
# This mapping is role-specific to ensure proper access control
ROLE_TO_CORE_PERMISSION_MAPPING = {
    # Admin role - full access
    'admin': {
        # Dashboard access
        'patients.view': 'view_dashboard',
        
        # Patient management
        'patients.create': 'create_patient',
        'patients.edit': 'edit_patient',
        'patients.delete': 'delete_patient',
        'patients.toggle_status': 'manage_patient_admission',
        'patients.wallet_manage': 'manage_wallet',
        'patients.nhia_manage': 'manage_wallet',
        
        # Medical records
        'medical.view': 'access_sensitive_data',
        'medical.create': 'access_sensitive_data',
        'medical.edit': 'access_sensitive_data',
        'medical.delete': 'access_sensitive_data',
        
        # Vitals
        'vitals.view': 'manage_vitals',
        'vitals.create': 'manage_vitals',
        'vitals.edit': 'manage_vitals',
        'vitals.delete': 'manage_vitals',
        
        # Consultations
        'consultations.create': 'create_appointment',
        'consultations.edit': 'create_appointment',
        
        # Referrals
        'referrals.create': 'create_appointment',
        'referrals.edit': 'create_appointment',
        
        # Pharmacy
        'pharmacy.view': 'view_prescriptions',
        'pharmacy.create': 'create_prescription',
        'pharmacy.edit': 'edit_prescription',
        'pharmacy.dispense': 'dispense_medication',
        
        # Laboratory
        'lab.create': 'create_test_request',
        'lab.edit': 'enter_results',
        'lab.results': 'enter_results',
        
        # Billing
        'billing.create': 'create_invoice',
        'billing.edit': 'edit_invoice',
        'billing.process_payment': 'process_payments',
        
        # Appointments
        'appointments.create': 'create_appointment',
        'appointments.edit': 'create_appointment',
        
        # Inpatient
        'inpatient.create': 'manage_admission',
        'inpatient.edit': 'manage_vitals',
        'inpatient.discharge': 'manage_discharge',
        
        # User management
        'users.view': 'view_user_management',
        'users.create': 'create_user',
        'users.edit': 'edit_user',
        'users.delete': 'delete_user',
        'roles.view': 'view_user_management',
        'roles.create': 'manage_roles',
        'roles.edit': 'manage_roles',
        
        # Reports
        'reports.view': 'view_reports',
        'reports.generate': 'generate_reports',
        
        # Department management
        'departments.view': 'manage_departments',
        'departments.create': 'manage_departments',
        'departments.edit': 'manage_departments',
        
        # System administration
        'system_configuration': 'system_configuration',
        'backup_data': 'backup_data',
        'system_maintenance': 'system_maintenance',
        'view_audit_logs': 'view_audit_logs',
        
        # Radiology
        'radiology.create': 'create_radiology_request',
        'radiology.edit': 'enter_radiology_results',
    },
    
    # Doctor role - medical operations
    'doctor': {
        'patients.view': 'view_dashboard',
        'patients.create': 'create_patient',
        'patients.edit': 'edit_patient',
        'medical.view': 'access_sensitive_data',
        'medical.create': 'access_sensitive_data',
        'medical.edit': 'access_sensitive_data',
        'vitals.view': 'manage_vitals',
        'vitals.create': 'manage_vitals',
        'vitals.edit': 'manage_vitals',
        'consultations.view': 'view_patients',
        'consultations.create': 'create_appointment',
        'consultations.edit': 'create_appointment',
        'referrals.view': 'view_patients',
        'referrals.create': 'create_appointment',
        'referrals.edit': 'create_appointment',
        'prescriptions.view': 'view_prescriptions',
        'prescriptions.create': 'create_prescription',
        'prescriptions.edit': 'edit_prescription',
        'lab.view': 'view_tests',
        'lab.create': 'create_test_request',
        'lab.edit': 'enter_results',
        'lab.results': 'enter_results',
        'appointments.view': 'create_appointment',
        'appointments.create': 'create_appointment',
        'inpatient.view': 'view_inpatient_records',
        'inpatient.create': 'manage_admission',
        'inpatient.edit': 'manage_vitals',
        'reports.view': 'view_reports',
    },
    
    # Nurse role - patient care
    'nurse': {
        'patients.view': 'view_dashboard',
        'patients.edit': 'edit_patient',
        'medical.view': 'access_sensitive_data',
        'medical.create': 'access_sensitive_data',
        'medical.edit': 'access_sensitive_data',
        'vitals.view': 'manage_vitals',
        'vitals.create': 'manage_vitals',
        'vitals.edit': 'manage_vitals',
        'consultations.view': 'view_patients',
        'referrals.view': 'view_patients',
        'referrals.create': 'create_appointment',
        'prescriptions.view': 'view_prescriptions',
        'appointments.view': 'create_appointment',
        'inpatient.view': 'view_inpatient_records',
        'inpatient.create': 'manage_admission',
        'inpatient.edit': 'manage_vitals',
        'reports.view': 'view_reports',
    },
    
    # Receptionist role - front desk
    'receptionist': {
        'patients.view': 'view_dashboard',
        'patients.create': 'create_patient',
        'patients.edit': 'edit_patient',
        'medical.view': 'access_sensitive_data',
        'consultations.view': 'view_patients',
        'consultations.create': 'create_appointment',
        'appointments.view': 'create_appointment',
        'appointments.create': 'create_appointment',
        'appointments.edit': 'create_appointment',
        'wallet.view': 'manage_wallet',
        'wallet.create': 'manage_wallet',
        'reports.view': 'view_reports',
    },
    
    # Pharmacist role - medication management
    'pharmacist': {
        'patients.view': 'view_dashboard',
        'pharmacy.view': 'view_prescriptions',
        'pharmacy.create': 'create_prescription',
        'pharmacy.edit': 'edit_prescription',
        'pharmacy.dispense': 'dispense_medication',
        'prescriptions.view': 'view_prescriptions',
        'prescriptions.edit': 'edit_prescription',
        'reports.view': 'view_reports',
    },
    
    # Lab Technician role - laboratory
    'lab_technician': {
        'patients.view': 'view_dashboard',
        'lab.view': 'view_tests',
        'lab.create': 'create_test_request',
        'lab.edit': 'enter_results',
        'lab.results': 'enter_results',
        'prescriptions.view': 'view_prescriptions',
        'reports.view': 'view_laboratory_reports',
    },
    
    # Accountant role - financial management
    'accountant': {
        'patients.view': 'view_dashboard',
        'billing.view': 'view_invoices',
        'billing.create': 'create_invoice',
        'billing.edit': 'edit_invoice',
        'billing.process_payment': 'process_payments',
        'wallet.view': 'view_financial_reports',
        'wallet.edit': 'manage_wallet',
        'wallet.transactions': 'manage_wallet',
        'reports.view': 'view_reports',
    },
    
    # Health Record Officer role - records management
    'health_record_officer': {
        'patients.view': 'view_dashboard',
        'patients.create': 'create_patient',
        'patients.edit': 'edit_patient',
        'patients.delete': 'delete_patient',
        'medical.view': 'access_sensitive_data',
        'medical.create': 'access_sensitive_data',
        'medical.edit': 'access_sensitive_data',
        'medical.delete': 'manage_patient_discharge',
        'vitals.view': 'manage_vitals',
        'vitals.create': 'manage_vitals',
        'vitals.edit': 'manage_vitals',
        'reports.view': 'view_reports',
    },
    
    # Radiology Staff role - imaging services
    'radiology_staff': {
        'patients.view': 'view_dashboard',
        'radiology.view': 'view_radiology',
        'radiology.create': 'create_radiology_request',
        'radiology.edit': 'enter_radiology_results',
        'reports.view': 'view_reports',
    },
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
        
        # Include direct Django auth user_permissions codenames
        if self.user.user_permissions.filter(codename=permission_name).exists():
            self._permissions_cache[permission_name] = True
            return True

        # Get all permissions from user's roles
        user_permissions = set()
        for role in self.user.roles.all():
            # Get permissions from role and its parent roles
            role_permissions = role.get_all_permissions()
            user_permissions.update(role_permissions)
        
        # Check if permission exists
        has_perm = permission_name in user_permissions
        self._permissions_cache[permission_name] = has_perm
        
        # If not found in Django permissions, check role-based permissions
        if not has_perm:
            user_roles = [role.name for role in self.user.roles.all()]
            for role_name in user_roles:
                if role_name in ROLE_PERMISSIONS:
                    role_permissions = ROLE_PERMISSIONS[role_name]['permissions']
                    # Check if any role permission maps to the requested core permission
                    for role_perm in role_permissions:
                        # Convert role permission (e.g., 'patients.view') to Django codename (e.g., 'patients_view')
                        django_codename = role_perm.replace('.', '_')
                        
                        # Check if user has this Django permission directly
                        if self.user.user_permissions.filter(codename=django_codename).exists():
                            self._permissions_cache[permission_name] = True
                            return True
                        
                        # Check if user's roles have this permission
                        for user_role in self.user.roles.all():
                            if user_role.permissions.filter(codename=django_codename).exists():
                                self._permissions_cache[permission_name] = True
                                return True
                        
                        # Check role-specific mapping for this role
                        if (role_name in ROLE_TO_CORE_PERMISSION_MAPPING and 
                            role_perm in ROLE_TO_CORE_PERMISSION_MAPPING[role_name]):
                            mapped_permission = ROLE_TO_CORE_PERMISSION_MAPPING[role_name][role_perm]
                            if mapped_permission == permission_name:
                                self._permissions_cache[permission_name] = True
                                return True
        
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
        
        # Start with direct Django auth user_permissions (codenames)
        user_permissions = set(self.user.user_permissions.values_list('codename', flat=True))

        # Add permissions from all roles (and parent roles)
        for role in self.user.roles.all():
            role_permissions = role.get_all_permissions()
            # role.get_all_permissions() returns Permission objects; use codenames for consistency
            user_permissions.update([perm.codename for perm in role_permissions])

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
