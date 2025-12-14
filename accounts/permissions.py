"""
Comprehensive Role-Based Access Control (RBAC) System for HMS

This module provides a centralized permission system that works across all modules
in the Hospital Management System. It defines role-based access controls for different
user types and their permissions.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib import messages
from django.shortcuts import redirect, render
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Define role hierarchies and permissions
ROLE_PERMISSIONS = {
    'admin': {
        'description': 'System Administrator - Full access to all modules',
        'permissions': [
            # Patient Management
            'patients.view', 'patients.create', 'patients.edit', 'patients.delete',
            'patients.toggle_status', 'patients.wallet_manage', 'patients.nhia_manage',
            
            # Medical Records
            'medical.view', 'medical.create', 'medical.edit', 'medical.delete',
            'vitals.view', 'vitals.create', 'vitals.edit', 'vitals.delete',
            
            # Consultations & Referrals
            'consultations.view', 'consultations.create', 'consultations.edit',
            'referrals.view', 'referrals.create', 'referrals.edit',
            
            # Pharmacy
            'pharmacy.view', 'pharmacy.create', 'pharmacy.edit', 'pharmacy.dispense',
            'prescriptions.view', 'prescriptions.create', 'prescriptions.edit',
            
            # Laboratory
            'lab.view', 'lab.create', 'lab.edit', 'lab.results',
            
            # Billing & Finance
            'billing.view', 'billing.create', 'billing.edit', 'billing.process_payment',
            'wallet.view', 'wallet.create', 'wallet.edit', 'wallet.transactions', 'wallet.manage',
            
            # Appointments
            'appointments.view', 'appointments.create', 'appointments.edit',
            
            # Inpatient Management
            'inpatient.view', 'inpatient.create', 'inpatient.edit', 'inpatient.discharge',
            
            # User Management
            'users.view', 'users.create', 'users.edit', 'users.delete',
            'roles.view', 'roles.create', 'roles.edit',
            
            # Reports & Analytics
            'reports.view', 'reports.generate',
        ]
    },
    
    'doctor': {
        'description': 'Medical Doctor - Patient care and medical operations',
        'permissions': [
            'patients.view', 'patients.edit',
            'medical.view', 'medical.create', 'medical.edit',
            'vitals.view', 'vitals.create', 'vitals.edit',
            'consultations.view', 'consultations.create', 'consultations.edit',
            'referrals.view', 'referrals.create',
            'prescriptions.view', 'prescriptions.create', 'prescriptions.edit',
            'lab.view', 'lab.create',
            'appointments.view', 'appointments.create',
            'inpatient.view', 'inpatient.create', 'inpatient.edit',
            'reports.view',
        ]
    },
    
    'nurse': {
        'description': 'Registered Nurse - Patient care and vitals monitoring',
        'permissions': [
            'patients.view', 'patients.edit',
            'medical.view', 'medical.create', 'medical.edit',
            'vitals.view', 'vitals.create', 'vitals.edit',
            'consultations.view',
            'referrals.view', 'referrals.create',
            'prescriptions.view',
            'appointments.view',
            'inpatient.view', 'inpatient.create', 'inpatient.edit',
            'reports.view',
        ]
    },
    
    'receptionist': {
        'description': 'Front Desk Receptionist - Patient registration and appointments',
        'permissions': [
            'patients.view', 'patients.create', 'patients.edit',
            'medical.view',
            'consultations.view', 'consultations.create',
            'appointments.view', 'appointments.create', 'appointments.edit',
            'reports.view',
        ]
    },
    
    'pharmacist': {
        'description': 'Licensed Pharmacist - Medication management and dispensing',
        'permissions': [
            'patients.view',
            'pharmacy.view', 'pharmacy.create', 'pharmacy.edit', 'pharmacy.dispense',
            'prescriptions.view', 'prescriptions.edit',
            'reports.view',
        ]
    },
    
    'lab_technician': {
        'description': 'Laboratory Technician - Test management and results',
        'permissions': [
            'patients.view',
            'lab.view', 'lab.create', 'lab.edit', 'lab.results',
            'prescriptions.view',
            'reports.view',
        ]
    },
    
    'accountant': {
        'description': 'Hospital Accountant - Financial management and billing',
        'permissions': [
            'patients.view',
            'billing.view', 'billing.create', 'billing.edit', 'billing.process_payment',
            'wallet.view', 'wallet.edit', 'wallet.transactions', 'wallet.manage',
            'reports.view',
        ]
    },
    
    'health_record_officer': {
        'description': 'Health Record Officer - Medical records management',
        'permissions': [
            'patients.view', 'patients.create', 'patients.edit', 'patients.delete',
            'medical.view', 'medical.create', 'medical.edit',
            'vitals.view', 'vitals.create', 'vitals.edit',
            'reports.view',
        ]
    },
    
    'radiology_staff': {
        'description': 'Radiology Technician - Imaging services',
        'permissions': [
            'patients.view',
            'radiology.view', 'radiology.create', 'radiology.edit',
            'reports.view',
        ]
    }
}

# Permission categories for easier management
CATEGORY_PERMISSIONS = {
    'patient_management': [
        'patients.view', 'patients.create', 'patients.edit', 'patients.delete',
        'patients.toggle_status', 'patients.wallet_manage', 'patients.nhia_manage',
    ],
    'medical_records': [
        'medical.view', 'medical.create', 'medical.edit', 'medical.delete',
        'vitals.view', 'vitals.create', 'vitals.edit', 'vitals.delete',
    ],
    'consultations': [
        'consultations.view', 'consultations.create', 'consultations.edit',
        'referrals.view', 'referrals.create', 'referrals.edit',
    ],
    'pharmacy': [
        'pharmacy.view', 'pharmacy.create', 'pharmacy.edit', 'pharmacy.dispense',
        'prescriptions.view', 'prescriptions.create', 'prescriptions.edit',
    ],
    'laboratory': [
        'lab.view', 'lab.create', 'lab.edit', 'lab.results',
    ],
    'billing': [
        'billing.view', 'billing.create', 'billing.edit', 'billing.process_payment',
        'wallet.view', 'wallet.create', 'wallet.edit', 'wallet.transactions',
    ],
    'appointments': [
        'appointments.view', 'appointments.create', 'appointments.edit',
    ],
    'inpatient': [
        'inpatient.view', 'inpatient.create', 'inpatient.edit', 'inpatient.discharge',
    ],
    'user_management': [
        'users.view', 'users.create', 'users.edit', 'users.delete',
        'roles.view', 'roles.create', 'roles.edit',
    ],
    'reports': [
        'reports.view', 'reports.generate',
    ]
}


def get_user_roles(user):
    """Get all roles for a user including inherited roles."""
    if not user.is_authenticated:
        return []
    
    if user.is_superuser:
        return list(ROLE_PERMISSIONS.keys())
    
    roles = []
    # Many-to-many roles
    for role_relation in getattr(user, 'roles', []).all():
        roles.append(role_relation.name)
        parent = role_relation.parent
        while parent:
            roles.append(parent.name)
            parent = parent.parent
    # Legacy profile role
    profile_role = getattr(getattr(user, 'profile', None), 'role', None)
    if profile_role and profile_role not in roles:
        roles.append(profile_role)
    return list(set(roles))


def user_has_permission(user, permission):
    """Check if user has specific permission."""
    if not user.is_authenticated:
        return False
    
    # Superuser has all permissions
    if user.is_superuser:
        return True
    
    # Check user's roles for the permission
    user_roles = get_user_roles(user)
    for role_name in user_roles:
        if role_name in ROLE_PERMISSIONS:
            if permission in ROLE_PERMISSIONS[role_name]['permissions']:
                return True
    
    # Check direct user permissions
    if user.user_permissions.filter(codename=permission.split('.')[-1]).exists():
        return True
    
    return False


def user_has_any_permission(user, permissions):
    """Check if user has any of the specified permissions."""
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    for permission in permissions:
        if user_has_permission(user, permission):
            return True
    
    return False


def user_has_all_permissions(user, permissions):
    """Check if user has all of the specified permissions."""
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    for permission in permissions:
        if not user_has_permission(user, permission):
            return False
    
    return True


def user_in_role(user, role_names):
    """Check if user has any of the specified roles."""
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    if isinstance(role_names, str):
        role_names = [role_names]
    
    user_roles = get_user_roles(user)
    return any(role in user_roles for role in role_names)


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


# Decorators for views

def permission_required(permission, login_url=None, raise_exception=True):
    """Decorator to check if user has specific permission."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not user_has_permission(request.user, permission):
                if raise_exception:
                    # Render a friendly permission denied page instead of plain 403 text
                    return render(request, 'errors/permission_denied.html', status=403)
                else:
                    messages.error(request, "You don't have permission to access this resource.")
                    return redirect(login_url or 'accounts:login')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def role_required(role_names, login_url=None, raise_exception=True):
    """Decorator to check if user has specific role(s)."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not user_in_role(request.user, role_names):
                if raise_exception:
                    return HttpResponseForbidden("You don't have the required role to access this resource.")
                else:
                    messages.error(request, "You don't have the required role to access this resource.")
                    return redirect(login_url or 'accounts:login')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def any_permission_required(permissions, login_url=None, raise_exception=True):
    """Decorator to check if user has any of the specified permissions."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not user_has_any_permission(request.user, permissions):
                if raise_exception:
                    return HttpResponseForbidden("You don't have permission to access this resource.")
                else:
                    messages.error(request, "You don't have permission to access this resource.")
                    return redirect(login_url or 'accounts:login')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def all_permissions_required(permissions, login_url=None, raise_exception=True):
    """Decorator to check if user has all of the specified permissions."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not user_has_all_permissions(request.user, permissions):
                if raise_exception:
                    return HttpResponseForbidden("You don't have all required permissions to access this resource.")
                else:
                    messages.error(request, "You don't have all required permissions to access this resource.")
                    return redirect(login_url or 'accounts:login')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# Context processors for templates

def user_permissions_context(request):
    """Add user permissions to template context."""
    if hasattr(request, 'user') and request.user.is_authenticated:
        user_roles = get_user_roles(request.user)
        user_permissions = {}
        
        # Build permission dictionary for templates
        for role_name in user_roles:
            if role_name in ROLE_PERMISSIONS:
                for permission in ROLE_PERMISSIONS[role_name]['permissions']:
                    user_permissions[permission] = True
        
        # Add role information
        user_permissions['roles'] = user_roles
        user_permissions['is_admin'] = 'admin' in user_roles
        user_permissions['is_superuser'] = request.user.is_superuser
        
        return user_permissions
    
    return {
        'roles': [],
        'is_admin': False,
        'is_superuser': False
    }


# Utility functions for checking permissions in views

def check_patient_access(user, patient_id=None):
    """Check if user can access patient information."""
    return user_has_permission(user, 'patients.view')


def check_medical_record_access(user):
    """Check if user can access medical records."""
    return user_has_permission(user, 'medical.view')


def check_billing_access(user):
    """Check if user can access billing functions."""
    return user_has_permission(user, 'billing.view')


def check_pharmacy_access(user):
    """Check if user can access pharmacy functions."""
    return user_has_permission(user, 'pharmacy.view')


def check_user_management_access(user):
    """Check if user can manage users."""
    return user_has_permission(user, 'users.view')


# API helpers

def get_user_accessible_modules(user):
    """Get list of modules accessible to user."""
    accessible_modules = []
    user_roles = get_user_roles(user)
    
    for role_name in user_roles:
        if role_name in ROLE_PERMISSIONS:
            for permission in ROLE_PERMISSIONS[role_name]['permissions']:
                module = permission.split('.')[0]
                if module not in accessible_modules:
                    accessible_modules.append(module)
    
    return accessible_modules


def can_perform_action(user, action, context=None):
    """Check if user can perform specific action in context."""
    # This is a more sophisticated permission checker that can consider context
    permission_map = {
        'view_patient': 'patients.view',
        'edit_patient': 'patients.edit',
        'delete_patient': 'patients.delete',
        'toggle_patient_status': 'patients.toggle_status',
        'manage_wallet': 'patients.wallet_manage',
        'manage_nhia': 'patients.nhia_manage',
        'view_medical_records': 'medical.view',
        'edit_medical_records': 'medical.edit',
        'view_vitals': 'vitals.view',
        'edit_vitals': 'vitals.edit',
        'create_consultation': 'consultations.create',
        'edit_consultation': 'consultations.edit',
        'create_referral': 'referrals.create',
        'edit_referral': 'referrals.edit',
        'manage_pharmacy': 'pharmacy.view',
        'dispense_medications': 'pharmacy.dispense',
        'manage_prescriptions': 'prescriptions.view',
        'edit_prescriptions': 'prescriptions.edit',
        'manage_laboratory': 'lab.view',
        'view_lab_results': 'lab.results',
        'manage_billing': 'billing.view',
        'process_payment': 'billing.process_payment',
        'manage_wallet': 'wallet.view',
        'manage_appointments': 'appointments.view',
        'edit_appointments': 'appointments.edit',
        'manage_inpatient': 'inpatient.view',
        'discharge_patient': 'inpatient.discharge',
        'manage_users': 'users.view',
        'manage_roles': 'roles.view',
        'view_reports': 'reports.view',
        'generate_reports': 'reports.generate',
    }
    
    if action in permission_map:
        return user_has_permission(user, permission_map[action])
    
    return False


# Template tags helper functions

def get_role_badge_class(role_name):
    """Get Bootstrap badge class for role."""
    role_classes = {
        'admin': 'bg-danger',
        'doctor': 'bg-primary',
        'nurse': 'bg-info',
        'receptionist': 'bg-success',
        'pharmacist': 'bg-warning',
        'lab_technician': 'bg-secondary',
        'accountant': 'bg-dark',
        'health_record_officer': 'bg-purple',
        'radiology_staff': 'bg-pink',
    }
    return role_classes.get(role_name, 'bg-secondary')


def get_role_display_name(role_name):
    """Get display name for role."""
    role_names = {
        'admin': 'Administrator',
        'doctor': 'Doctor',
        'nurse': 'Nurse',
        'receptionist': 'Receptionist',
        'pharmacist': 'Pharmacist',
        'lab_technician': 'Lab Technician',
        'accountant': 'Accountant',
        'health_record_officer': 'Health Record Officer',
        'radiology_staff': 'Radiology Staff',
    }
    return role_names.get(role_name, role_name.title())


# Migration helper to set up default roles
def create_default_roles():
    """Create default roles with permissions."""
    from django.contrib.auth.models import Permission
    
    for role_name, role_data in ROLE_PERMISSIONS.items():
        role, created = Role.objects.get_or_create(
            name=role_name,
            defaults={'description': role_data['description']}
        )
        
        if created:
            logger.info(f"Created role: {role_name}")
        else:
            logger.info(f"Role already exists: {role_name}")
        
        # Note: In a real implementation, you would also need to map Django permissions
        # to the custom permissions defined above. This is a simplified version.
    
    return True
