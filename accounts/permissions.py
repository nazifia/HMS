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

# Debug flag for verbose logging (set to True for debugging)
DEBUG_PERMISSIONS = False

# Permission mapping from custom names to Django permission codenames
# This maps the permission strings used in ROLE_PERMISSIONS to actual Django Permission codenames
# Values are now FULL permission strings in the format 'app_label.codename'
PERMISSION_MAPPING = {
    # Patients (app: patients)
    'patients.view': 'patients.view_patient',
    'patients.create': 'patients.add_patient',
    'patients.edit': 'patients.change_patient',
    'patients.delete': 'patients.delete_patient',
    'patients.toggle_status': 'patients.toggle_patientstatus',  # custom permission
    'patients.wallet_manage': 'patients.manage_wallet',  # custom permission
    'patients.nhia_manage': 'patients.manage_nhiastatus',  # custom permission

    # Medical Records (app: patients or consultations? Assuming patients for now)
    'medical.view': 'patients.view_medicalrecord',
    'medical.create': 'patients.add_medicalrecord',
    'medical.edit': 'patients.change_medicalrecord',
    'medical.delete': 'patients.delete_medicalrecord',
    'vitals.view': 'patients.view_vital',
    'vitals.create': 'patients.add_vital',
    'vitals.edit': 'patients.change_vital',
    'vitals.delete': 'patients.delete_vital',

    # Consultations (app: consultations)
    'consultations.view': 'consultations.view_consultation',
    'consultations.create': 'consultations.add_consultation',
    'consultations.edit': 'consultations.change_consultation',
    'referrals.view': 'consultations.view_referral',
    'referrals.create': 'consultations.add_referral',
    'referrals.edit': 'consultations.change_referral',

    # Pharmacy (app: pharmacy)
    'pharmacy.view': 'pharmacy.view_pharmacy',
    'pharmacy.create': 'pharmacy.add_pharmacy',
    'pharmacy.edit': 'pharmacy.change_pharmacy',
    'pharmacy.dispense': 'pharmacy.dispense_medication',  # custom permission
    'prescriptions.view': 'pharmacy.view_prescription',
    'prescriptions.create': 'pharmacy.add_prescription',
    'prescriptions.edit': 'pharmacy.change_prescription',

    # Laboratory (app: laboratory)
    'lab.view': 'laboratory.view_labtest',
    'lab.create': 'laboratory.add_labtest',
    'lab.edit': 'laboratory.change_labtest',
    'lab.results': 'laboratory.enter_labresults',  # custom permission

    # Billing (app: billing)
    'billing.view': 'billing.view_invoice',
    'billing.create': 'billing.add_invoice',
    'billing.edit': 'billing.change_invoice',
    'billing.process_payment': 'billing.process_payment',  # custom permission
    'wallet.view': 'billing.view_wallet',
    'wallet.create': 'billing.add_wallet',
    'wallet.edit': 'billing.change_wallet',
    'wallet.transactions': 'billing.view_wallettransaction',
    'wallet.manage': 'billing.manage_wallet',  # custom permission

    # Appointments (app: appointments)
    'appointments.view': 'appointments.view_appointment',
    'appointments.create': 'appointments.add_appointment',
    'appointments.edit': 'appointments.change_appointment',

    # Inpatient (app: inpatient)
    'inpatient.view': 'inpatient.view_admission',
    'inpatient.create': 'inpatient.add_admission',
    'inpatient.edit': 'inpatient.change_admission',
    'inpatient.discharge': 'inpatient.discharge_patient',  # custom permission

    # User Management (app: accounts)
    'users.view': 'accounts.view_customuser',
    'users.create': 'accounts.add_customuser',
    'users.edit': 'accounts.change_customuser',
    'users.delete': 'accounts.delete_customuser',
    'roles.view': 'accounts.view_role',
    'roles.create': 'accounts.add_role',
    'roles.edit': 'accounts.change_role',

    # Reports (app: ? Could be core or accounts)
    'reports.view': 'core.view_report',  # Assuming report model in core
    'reports.generate': 'core.generate_report',  # custom permission
}

def get_django_permission(custom_permission):
    """
    Convert a custom permission string to full Django permission string.
    Returns 'app_label.codename' format.

    Now uses complete permission strings from PERMISSION_MAPPING.
    """
    # Return the full permission string directly from mapping
    if custom_permission in PERMISSION_MAPPING:
        return PERMISSION_MAPPING[custom_permission]

    # If not in mapping, log a warning and return as-is
    if DEBUG_PERMISSIONS:
        logger.warning(f"Permission '{custom_permission}' not found in PERMISSION_MAPPING")

    return custom_permission

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
        'description': 'Front Desk Receptionist & Health Records - Patient registration, appointments, and records',
        'permissions': [
            'patients.view', 'patients.create', 'patients.edit', 'patients.delete',
            'medical.view', 'medical.create', 'medical.edit',
            'vitals.view', 'vitals.create', 'vitals.edit',
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
        'description': 'Health Record Officer & Receptionist - Medical records and front desk operations',
        'permissions': [
            'patients.view', 'patients.create', 'patients.edit', 'patients.delete',
            'medical.view', 'medical.create', 'medical.edit',
            'vitals.view', 'vitals.create', 'vitals.edit',
            'consultations.view', 'consultations.create',
            'appointments.view', 'appointments.create', 'appointments.edit',
            'billing.view', 'billing.create', 'billing.edit', 'billing.process_payment',
            'wallet.view', 'wallet.edit', 'wallet.transactions',
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
    user_roles_manager = getattr(user, 'roles', None)
    if user_roles_manager and hasattr(user_roles_manager, 'all'):
        for role_relation in user_roles_manager.all():
            roles.append(role_relation.name)
            parent = getattr(role_relation, 'parent', None)
            while parent:
                roles.append(parent.name)
                parent = parent.parent
    # Legacy profile role
    profile_role = getattr(getattr(user, 'profile', None), 'role', None)
    if profile_role and profile_role not in roles:
        roles.append(profile_role)
    return list(set(roles))


def user_has_permission(user, permission):
    """Check if user has specific permission.

    Priority:
    1. Superuser check
    2. Django's built-in permission system (user.has_perm) which includes RolePermissionBackend
    3. Custom ROLE_PERMISSIONS mapping (for backward compatibility with custom permissions)

    Args:
        user: The user to check
        permission: Permission string (e.g., 'patients.view', 'roles.edit')
    """
    if not user.is_authenticated:
        return False

    # Superuser has all permissions
    if user.is_superuser:
        return True

    # Check via Django permission system (includes RolePermissionBackend)
    # For backward compatibility, accept both custom permission strings and full Django strings
    django_perm = get_django_permission(permission)
    if user.has_perm(django_perm):
        if DEBUG_PERMISSIONS:
            logger.info(f"Permission GRANTED: {permission} -> {django_perm} for user {user}")
        return True

    # If permission is not in mapping, also try direct custom string for backward compatibility
    # This checks against the ROLE_PERMISSIONS dict (custom permission strings)
    if permission != django_perm:
        user_roles = get_user_roles(user)
        for role_name in user_roles:
            if role_name in ROLE_PERMISSIONS:
                if permission in ROLE_PERMISSIONS[role_name]['permissions']:
                    if DEBUG_PERMISSIONS:
                        logger.info(f"Permission GRANTED via ROLE_PERMISSIONS: {permission} for user {user}")
                    return True

    if DEBUG_PERMISSIONS:
        logger.info(f"Permission DENIED: {permission} for user {user}")
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
                # Extract module from custom permission string (e.g., 'patients.view' -> 'patients')
                module = permission.split('.')[0]
                if module not in accessible_modules:
                    accessible_modules.append(module)

    return accessible_modules


def can_perform_action(user, action, context=None):
    """Check if user can perform specific action in context."""
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

    return True
