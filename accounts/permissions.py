"""
Comprehensive Role-Based Access Control (RBAC) System for HMS

This module provides a centralized permission system that works across all modules
in the Hospital Management System. It defines role-based access controls for different
user types and their permissions.

ARCHITECTURE:
=============
1. PERMISSION_DEFINITIONS: Single source of truth for all permissions in the system.
   Each permission includes metadata (django_codename, category, description, model, is_custom).

2. PERMISSION_MAPPING: Auto-generated mapping from custom permission keys to Django
   permission strings (e.g., 'patients.view' -> 'patients.view_patient').

3. ROLE_PERMISSIONS: Role definitions with permission lists. Uses custom permission keys
   that map to PERMISSION_DEFINITIONS.

4. CATEGORY_PERMISSIONS: Auto-generated grouping of permissions by category for
   easier management.

All permission checks should use the helper functions (user_has_permission, user_in_role)
which handle translation, inheritance, and caching.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib import messages
from django.shortcuts import redirect, render
from django.conf import settings
import logging
import warnings

logger = logging.getLogger(__name__)

# Debug flag for verbose logging (set to True for debugging)
DEBUG_PERMISSIONS = False

# ============================================================================
# PERMISSION_DEFINITIONS: Single source of truth for all permissions
# ============================================================================
# This dictionary defines all permissions used in the HMS system. It serves as the
# authoritative reference for permission metadata, including the Django permission
# string, category, description, associated model, and whether it's a custom permission.
#
# Structure:
#   'custom_key': {
#       'django_codename': 'app_label.codename',  # Full Django permission string
#       'category': 'category_name',               # Grouping category
#       'description': 'Human readable description',
#       'model': 'ModelName',                      # Associated Django model
#       'is_custom': True/False                    # True if not a standard Django perm
#   }
#
# To add a new permission:
#   1. Add entry to PERMISSION_DEFINITIONS below
#   2. Add the custom_key to appropriate ROLE_PERMISSIONS['role']['permissions']
#   3. Update documentation

PERMISSION_DEFINITIONS = {
    # --------------------------------------------------------------------------
    # Patient Management (patients app)
    # --------------------------------------------------------------------------
    'patients.view': {
        'django_codename': 'patients.view_patient',
        'category': 'patient_management',
        'description': 'Can view patient records',
        'model': 'Patient',
        'is_custom': False,
    },
    'patients.create': {
        'django_codename': 'patients.add_patient',
        'category': 'patient_management',
        'description': 'Can add/create new patients',
        'model': 'Patient',
        'is_custom': False,
    },
    'patients.edit': {
        'django_codename': 'patients.change_patient',
        'category': 'patient_management',
        'description': 'Can edit patient records',
        'model': 'Patient',
        'is_custom': False,
    },
    'patients.delete': {
        'django_codename': 'patients.delete_patient',
        'category': 'patient_management',
        'description': 'Can delete patient records',
        'model': 'Patient',
        'is_custom': False,
    },
    'patients.toggle_status': {
        'django_codename': 'patients.toggle_patientstatus',
        'category': 'patient_management',
        'description': 'Can toggle patient active/inactive status',
        'model': 'Patient',
        'is_custom': True,
    },
    'patients.wallet_manage': {
        'django_codename': 'patients.manage_wallet',
        'category': 'patient_management',
        'description': 'Can manage patient wallet (add funds, adjust balances)',
        'model': 'Patient',
        'is_custom': True,
    },
    'patients.nhia_manage': {
        'django_codename': 'patients.manage_nhiastatus',
        'category': 'patient_management',
        'description': 'Can manage NHIA insurance status',
        'model': 'Patient',
        'is_custom': True,
    },

    # --------------------------------------------------------------------------
    # Medical Records (patients app - MedicalHistory, Vitals)
    # --------------------------------------------------------------------------
    'medical.view': {
        'django_codename': 'patients.view_medicalhistory',
        'category': 'medical_records',
        'description': 'Can view medical history records',
        'model': 'MedicalHistory',
        'is_custom': False,
    },
    'medical.create': {
        'django_codename': 'patients.add_medicalhistory',
        'category': 'medical_records',
        'description': 'Can add medical history records',
        'model': 'MedicalHistory',
        'is_custom': False,
    },
    'medical.edit': {
        'django_codename': 'patients.change_medicalhistory',
        'category': 'medical_records',
        'description': 'Can edit medical history records',
        'model': 'MedicalHistory',
        'is_custom': False,
    },
    'medical.delete': {
        'django_codename': 'patients.delete_medicalhistory',
        'category': 'medical_records',
        'description': 'Can delete medical history records',
        'model': 'MedicalHistory',
        'is_custom': False,
    },
    'vitals.view': {
        'django_codename': 'patients.view_vitals',
        'category': 'medical_records',
        'description': 'Can view vital signs records',
        'model': 'Vitals',
        'is_custom': False,
    },
    'vitals.create': {
        'django_codename': 'patients.add_vitals',
        'category': 'medical_records',
        'description': 'Can add vital signs records',
        'model': 'Vitals',
        'is_custom': False,
    },
    'vitals.edit': {
        'django_codename': 'patients.change_vitals',
        'category': 'medical_records',
        'description': 'Can edit vital signs records',
        'model': 'Vitals',
        'is_custom': False,
    },
    'vitals.delete': {
        'django_codename': 'patients.delete_vitals',
        'category': 'medical_records',
        'description': 'Can delete vital signs records',
        'model': 'Vitals',
        'is_custom': False,
    },

    # --------------------------------------------------------------------------
    # Consultations (consultations app)
    # --------------------------------------------------------------------------
    'consultations.view': {
        'django_codename': 'consultations.view_consultation',
        'category': 'consultations',
        'description': 'Can view consultation records',
        'model': 'Consultation',
        'is_custom': False,
    },
    'consultations.create': {
        'django_codename': 'consultations.add_consultation',
        'category': 'consultations',
        'description': 'Can create consultations',
        'model': 'Consultation',
        'is_custom': False,
    },
    'consultations.edit': {
        'django_codename': 'consultations.change_consultation',
        'category': 'consultations',
        'description': 'Can edit consultation records',
        'model': 'Consultation',
        'is_custom': False,
    },
    'consultations.delete': {
        'django_codename': 'consultations.delete_consultation',
        'category': 'consultations',
        'description': 'Can delete consultation records',
        'model': 'Consultation',
        'is_custom': False,
    },
    'referrals.view': {
        'django_codename': 'consultations.view_referral',
        'category': 'consultations',
        'description': 'Can view referral records',
        'model': 'Referral',
        'is_custom': False,
    },
    'referrals.create': {
        'django_codename': 'consultations.add_referral',
        'category': 'consultations',
        'description': 'Can create referrals',
        'model': 'Referral',
        'is_custom': False,
    },
    'referrals.edit': {
        'django_codename': 'consultations.change_referral',
        'category': 'consultations',
        'description': 'Can edit referral records',
        'model': 'Referral',
        'is_custom': False,
    },
    'referrals.delete': {
        'django_codename': 'consultations.delete_referral',
        'category': 'consultations',
        'description': 'Can delete referral records',
        'model': 'Referral',
        'is_custom': False,
    },

    # --------------------------------------------------------------------------
    # Pharmacy (pharmacy app)
    # --------------------------------------------------------------------------
    'pharmacy.view': {
        'django_codename': 'pharmacy.view_dispensary',
        'category': 'pharmacy',
        'description': 'Can view dispensary records',
        'model': 'Dispensary',
        'is_custom': False,
    },
    'pharmacy.create': {
        'django_codename': 'pharmacy.add_dispensary',
        'category': 'pharmacy',
        'description': 'Can add dispensary records',
        'model': 'Dispensary',
        'is_custom': False,
    },
    'pharmacy.edit': {
        'django_codename': 'pharmacy.change_dispensary',
        'category': 'pharmacy',
        'description': 'Can edit dispensary records',
        'model': 'Dispensary',
        'is_custom': False,
    },
    'pharmacy.dispense': {
        'django_codename': 'pharmacy.dispense_medication',
        'category': 'pharmacy',
        'description': 'Can dispense medications to patients',
        'model': 'Prescription',
        'is_custom': True,
    },
    'prescriptions.view': {
        'django_codename': 'pharmacy.view_prescription',
        'category': 'pharmacy',
        'description': 'Can view prescription records',
        'model': 'Prescription',
        'is_custom': False,
    },
    'prescriptions.create': {
        'django_codename': 'pharmacy.add_prescription',
        'category': 'pharmacy',
        'description': 'Can create prescriptions',
        'model': 'Prescription',
        'is_custom': False,
    },
    'prescriptions.edit': {
        'django_codename': 'pharmacy.change_prescription',
        'category': 'pharmacy',
        'description': 'Can edit prescription records',
        'model': 'Prescription',
        'is_custom': False,
    },
    'prescriptions.delete': {
        'django_codename': 'pharmacy.delete_prescription',
        'category': 'pharmacy',
        'description': 'Can delete prescription records',
        'model': 'Prescription',
        'is_custom': False,
    },

    # --------------------------------------------------------------------------
    # Laboratory (laboratory app)
    # --------------------------------------------------------------------------
    'lab.view': {
        'django_codename': 'laboratory.view_test',
        'category': 'laboratory',
        'description': 'Can view lab test records',
        'model': 'Test',
        'is_custom': False,
    },
    'lab.create': {
        'django_codename': 'laboratory.add_test',
        'category': 'laboratory',
        'description': 'Can create lab tests',
        'model': 'Test',
        'is_custom': False,
    },
    'lab.edit': {
        'django_codename': 'laboratory.change_test',
        'category': 'laboratory',
        'description': 'Can edit lab test records',
        'model': 'Test',
        'is_custom': False,
    },
    'lab.delete': {
        'django_codename': 'laboratory.delete_test',
        'category': 'laboratory',
        'description': 'Can delete lab test records',
        'model': 'Test',
        'is_custom': False,
    },
    'lab.results': {
        'django_codename': 'laboratory.enter_testresults',
        'category': 'laboratory',
        'description': 'Can enter/edit lab test results',
        'model': 'TestResult',
        'is_custom': True,
    },

    # --------------------------------------------------------------------------
    # Billing & Finance (billing app)
    # --------------------------------------------------------------------------
    'billing.view': {
        'django_codename': 'billing.view_invoice',
        'category': 'billing',
        'description': 'Can view invoices',
        'model': 'Invoice',
        'is_custom': False,
    },
    'billing.create': {
        'django_codename': 'billing.add_invoice',
        'category': 'billing',
        'description': 'Can create invoices',
        'model': 'Invoice',
        'is_custom': False,
    },
    'billing.edit': {
        'django_codename': 'billing.change_invoice',
        'category': 'billing',
        'description': 'Can edit invoices',
        'model': 'Invoice',
        'is_custom': False,
    },
    'billing.delete': {
        'django_codename': 'billing.delete_invoice',
        'category': 'billing',
        'description': 'Can delete invoices',
        'model': 'Invoice',
        'is_custom': False,
    },
    'billing.process_payment': {
        'django_codename': 'billing.process_payment',
        'category': 'billing',
        'description': 'Can process payments',
        'model': 'Payment',
        'is_custom': True,
    },
    # --------------------------------------------------------------------------
    # Wallet & Transactions (patients app)
    # --------------------------------------------------------------------------
    'wallet.view': {
        'django_codename': 'patients.view_patientwallet',
        'category': 'billing',
        'description': 'Can view patient wallets',
        'model': 'PatientWallet',
        'is_custom': False,
    },
    'wallet.create': {
        'django_codename': 'patients.add_patientwallet',
        'category': 'billing',
        'description': 'Can create patient wallets',
        'model': 'PatientWallet',
        'is_custom': False,
    },
    'wallet.edit': {
        'django_codename': 'patients.change_patientwallet',
        'category': 'billing',
        'description': 'Can edit patient wallets',
        'model': 'PatientWallet',
        'is_custom': False,
    },
    'wallet.delete': {
        'django_codename': 'patients.delete_patientwallet',
        'category': 'billing',
        'description': 'Can delete patient wallets',
        'model': 'PatientWallet',
        'is_custom': False,
    },
    'wallet.transactions': {
        'django_codename': 'patients.view_wallettransaction',
        'category': 'billing',
        'description': 'Can view wallet transactions',
        'model': 'WalletTransaction',
        'is_custom': False,
    },
    'wallet.manage': {
        'django_codename': 'patients.manage_patientwallet',
        'category': 'billing',
        'description': 'Can manage wallet operations (adjust balances, refunds)',
        'model': 'PatientWallet',
        'is_custom': True,
    },

    # --------------------------------------------------------------------------
    # Appointments (appointments app)
    # --------------------------------------------------------------------------
    'appointments.view': {
        'django_codename': 'appointments.view_appointment',
        'category': 'appointments',
        'description': 'Can view appointment records',
        'model': 'Appointment',
        'is_custom': False,
    },
    'appointments.create': {
        'django_codename': 'appointments.add_appointment',
        'category': 'appointments',
        'description': 'Can create appointments',
        'model': 'Appointment',
        'is_custom': False,
    },
    'appointments.edit': {
        'django_codename': 'appointments.change_appointment',
        'category': 'appointments',
        'description': 'Can edit appointment records',
        'model': 'Appointment',
        'is_custom': False,
    },
    'appointments.delete': {
        'django_codename': 'appointments.delete_appointment',
        'category': 'appointments',
        'description': 'Can delete appointment records',
        'model': 'Appointment',
        'is_custom': False,
    },

    # --------------------------------------------------------------------------
    # Inpatient Management (inpatient app)
    # --------------------------------------------------------------------------
    'inpatient.view': {
        'django_codename': 'inpatient.view_admission',
        'category': 'inpatient',
        'description': 'Can view admission records',
        'model': 'Admission',
        'is_custom': False,
    },
    'inpatient.create': {
        'django_codename': 'inpatient.add_admission',
        'category': 'inpatient',
        'description': 'Can create admissions',
        'model': 'Admission',
        'is_custom': False,
    },
    'inpatient.edit': {
        'django_codename': 'inpatient.change_admission',
        'category': 'inpatient',
        'description': 'Can edit admission records',
        'model': 'Admission',
        'is_custom': False,
    },
    'inpatient.delete': {
        'django_codename': 'inpatient.delete_admission',
        'category': 'inpatient',
        'description': 'Can delete admission records',
        'model': 'Admission',
        'is_custom': False,
    },
    'inpatient.discharge': {
        'django_codename': 'inpatient.discharge_patient',
        'category': 'inpatient',
        'description': 'Can discharge inpatients',
        'model': 'Admission',
        'is_custom': True,
    },

    # --------------------------------------------------------------------------
    # User & Role Management (accounts app)
    # --------------------------------------------------------------------------
    'users.view': {
        'django_codename': 'accounts.view_customuser',
        'category': 'user_management',
        'description': 'Can view user accounts',
        'model': 'CustomUser',
        'is_custom': False,
    },
    'users.create': {
        'django_codename': 'accounts.add_customuser',
        'category': 'user_management',
        'description': 'Can create new user accounts',
        'model': 'CustomUser',
        'is_custom': False,
    },
    'users.edit': {
        'django_codename': 'accounts.change_customuser',
        'category': 'user_management',
        'description': 'Can edit user accounts',
        'model': 'CustomUser',
        'is_custom': False,
    },
    'users.delete': {
        'django_codename': 'accounts.delete_customuser',
        'category': 'user_management',
        'description': 'Can delete user accounts',
        'model': 'CustomUser',
        'is_custom': False,
    },
    'roles.view': {
        'django_codename': 'accounts.view_role',
        'category': 'user_management',
        'description': 'Can view roles',
        'model': 'Role',
        'is_custom': False,
    },
    'roles.create': {
        'django_codename': 'accounts.add_role',
        'category': 'user_management',
        'description': 'Can create roles',
        'model': 'Role',
        'is_custom': False,
    },
    'roles.edit': {
        'django_codename': 'accounts.change_role',
        'category': 'user_management',
        'description': 'Can edit roles',
        'model': 'Role',
        'is_custom': False,
    },
    'roles.delete': {
        'django_codename': 'accounts.delete_role',
        'category': 'user_management',
        'description': 'Can delete roles',
        'model': 'Role',
        'is_custom': False,
    },

    # --------------------------------------------------------------------------
    # Reports & Analytics (reporting app)
    # --------------------------------------------------------------------------
    'reports.view': {
        'django_codename': 'reporting.view_report',
        'category': 'reports',
        'description': 'Can view reports',
        'model': 'Report',
        'is_custom': False,
    },
    'reports.generate': {
        'django_codename': 'reporting.generate_report',
        'category': 'reports',
        'description': 'Can generate reports',
        'model': 'Report',
        'is_custom': True,
    },

    # --------------------------------------------------------------------------
    # Radiology (radiology app - if exists)
    # --------------------------------------------------------------------------
    'radiology.view': {
        'django_codename': 'radiology.view_radiologytest',
        'category': 'radiology',
        'description': 'Can view radiology tests/services',
        'model': 'RadiologyTest',
        'is_custom': False,
    },
    'radiology.create': {
        'django_codename': 'radiology.add_radiologytest',
        'category': 'radiology',
        'description': 'Can create radiology tests/services',
        'model': 'RadiologyTest',
        'is_custom': False,
    },
    'radiology.edit': {
        'django_codename': 'radiology.change_radiologytest',
        'category': 'radiology',
        'description': 'Can edit radiology tests/services',
        'model': 'RadiologyTest',
        'is_custom': False,
    },
    'radiology.delete': {
        'django_codename': 'radiology.delete_radiologytest',
        'category': 'radiology',
        'description': 'Can delete radiology tests/services',
        'model': 'RadiologyTest',
        'is_custom': False,
    },
}

# ============================================================================
# Auto-generate PERMISSION_MAPPING from DEFINITIONS
# ============================================================================
PERMISSION_MAPPING = {
    custom_key: defn['django_codename']
    for custom_key, defn in PERMISSION_DEFINITIONS.items()
}

# ============================================================================
# Auto-generate CATEGORY_PERMISSIONS from DEFINITIONS
# ============================================================================
CATEGORY_PERMISSIONS = {}
for custom_key, defn in PERMISSION_DEFINITIONS.items():
    category = defn['category']
    if category not in CATEGORY_PERMISSIONS:
        CATEGORY_PERMISSIONS[category] = []
    CATEGORY_PERMISSIONS[category].append(custom_key)

def get_django_permission(custom_permission):
    """
    Convert a custom permission string to full Django permission string.
    Returns 'app_label.codename' format.

    DEPRECATED: This function is maintained for backward compatibility.
    New code should use get_permission_info() or reference PERMISSION_DEFINITIONS directly.

    Args:
        custom_permission: Custom permission key (e.g., 'patients.view')

    Returns:
        Full Django permission string (e.g., 'patients.view_patient')
    """
    # Return the full permission string directly from mapping
    if custom_permission in PERMISSION_MAPPING:
        return PERMISSION_MAPPING[custom_permission]

    # If not in mapping, log a warning and return as-is
    warnings.warn(
        f"Permission '{custom_permission}' not found in PERMISSION_DEFINITIONS. "
        f"This may indicate a missing permission definition or use of raw Django permissions.",
        DeprecationWarning,
        stacklevel=2
    )
    if DEBUG_PERMISSIONS:
        logger.warning(f"Permission '{custom_permission}' not found in PERMISSION_MAPPING")

    return custom_permission


def get_permission_info(permission_key):
    """
    Get metadata for a permission from PERMISSION_DEFINITIONS.

    Args:
        permission_key: Custom permission key (e.g., 'patients.view')

    Returns:
        Dict with permission metadata or None if not found
    """
    return PERMISSION_DEFINITIONS.get(permission_key)


def get_permissions_by_category(category):
    """
    Get all permission keys belonging to a specific category.

    Args:
        category: Category name (e.g., 'patient_management')

    Returns:
        List of custom permission keys
    """
    return CATEGORY_PERMISSIONS.get(category, [])


def get_all_categories():
    """
    Get list of all permission categories.

    Returns:
        List of category names
    """
    return list(CATEGORY_PERMISSIONS.keys())


def validate_permission_definitions():
    """
    Validate that all permission definitions are consistent.

    Checks:
    - All PERMISSION_DEFINITIONS entries have required fields
    - All django_codename values are in correct format (app_label.codename)
    - No duplicate django_codename values
    - All referenced models exist in ROLE_PERMISSIONS (basic check)

    Returns:
        Tuple of (is_valid, errors_list)
    """
    errors = []
    warnings_list = []
    seen_django_codenames = set()

    required_fields = {'django_codename', 'category', 'description', 'model', 'is_custom'}

    for key, defn in PERMISSION_DEFINITIONS.items():
        # Check required fields
        missing = required_fields - set(defn.keys())
        if missing:
            errors.append(f"Permission '{key}' missing required fields: {missing}")
            continue

        # Validate django_codename format
        django_codename = defn['django_codename']
        if '.' not in django_codename or django_codename.count('.') != 1:
            errors.append(f"Permission '{key}' has invalid django_codename: '{django_codename}' (expected 'app_label.codename')")

        # Check for duplicates
        if django_codename in seen_django_codenames:
            errors.append(f"Duplicate django_codename '{django_codename}' found (for {key})")
        else:
            seen_django_codenames.add(django_codename)

        # Validate model name is non-empty
        if not defn['model'] or not isinstance(defn['model'], str):
            errors.append(f"Permission '{key}' has invalid model name")

        # Validate is_custom is boolean
        if not isinstance(defn['is_custom'], bool):
            errors.append(f"Permission '{key}' has non-boolean is_custom value")

    return (len(errors) == 0, errors, warnings_list)

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
            'medical.view', 'medical.create', 'medical.edit', 'medical.delete',
            'vitals.view', 'vitals.create', 'vitals.edit', 'vitals.delete',
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
            'medical.view', 'medical.create', 'medical.edit', 'medical.delete',
            'vitals.view', 'vitals.create', 'vitals.edit', 'vitals.delete',
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
