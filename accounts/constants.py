"""
Role and Permission Constants for HMS RBAC System

This module provides centralized constants for role names and permissions
to avoid hardcoded strings throughout the codebase.
"""

# Role names (use these instead of hardcoded strings)
ROLE_ADMIN = "admin"
ROLE_DOCTOR = "doctor"
ROLE_NURSE = "nurse"
ROLE_RECEPTIONIST = "receptionist"
ROLE_PHARMACIST = "pharmacist"
ROLE_LAB_TECHNICIAN = "lab_technician"
ROLE_RADIOLOGY_STAFF = "radiology_staff"
ROLE_ACCOUNTANT = "accountant"
ROLE_HEALTH_RECORD_OFFICER = "health_record_officer"
ROLE_DESK_OFFICER = "desk_officer"
ROLE_CASHIER_ACCOUNTANT = "cashier_accountant"

# All role names as tuples for choices
ROLE_CHOICES = (
    (ROLE_ADMIN, "Administrator"),
    (ROLE_DOCTOR, "Doctor"),
    (ROLE_NURSE, "Nurse"),
    (ROLE_RECEPTIONIST, "Receptionist"),
    (ROLE_PHARMACIST, "Pharmacist"),
    (ROLE_LAB_TECHNICIAN, "Lab Technician"),
    (ROLE_RADIOLOGY_STAFF, "Radiology Staff"),
    (ROLE_ACCOUNTANT, "Accountant"),
    (ROLE_HEALTH_RECORD_OFFICER, "Health Record Officer"),
    (ROLE_DESK_OFFICER, "Desk Officer"),
    (ROLE_CASHIER_ACCOUNTANT, "Cashier/Accountant"),
)

# Role groups for permission checks
CLINICAL_ROLES = [
    ROLE_DOCTOR,
    ROLE_NURSE,
    ROLE_LAB_TECHNICIAN,
    ROLE_RADIOLOGY_STAFF,
]

RECEPTION_ROLES = [
    ROLE_RECEPTIONIST,
    ROLE_HEALTH_RECORD_OFFICER,
    ROLE_DESK_OFFICER,
]

FINANCE_ROLES = [
    ROLE_ACCOUNTANT,
    ROLE_CASHIER_ACCOUNTANT,
]

ADMIN_ROLES = [
    ROLE_ADMIN,
]

# Permission namespaces (app actions)
PERMISSION_VIEW = "view"
PERMISSION_ADD = "add"
PERMISSION_CHANGE = "change"
PERMISSION_DELETE = "delete"

# Common permission patterns (use with model names)
# Example: f'pharmacy.{PERMISSION_VIEW}_medication'
# These map to Django's built-in permissions: view, add, change, delete

# Role hierarchy (for inheritance)
ROLE_HIERARCHY = {
    ROLE_ADMIN: [],  # Admin has no parent (top level)
    ROLE_DOCTOR: [ROLE_ADMIN],
    ROLE_NURSE: [ROLE_DOCTOR, ROLE_ADMIN],
    ROLE_RECEPTIONIST: [ROLE_ADMIN],
    ROLE_PHARMACIST: [ROLE_ADMIN],
    ROLE_LAB_TECHNICIAN: [ROLE_ADMIN],
    ROLE_RADIOLOGY_STAFF: [ROLE_ADMIN],
    ROLE_ACCOUNTANT: [ROLE_ADMIN],
    ROLE_HEALTH_RECORD_OFFICER: [ROLE_ADMIN, ROLE_RECEPTIONIST],
}


def get_role_hierarchy(role_name):
    """
    Get all parent roles for a given role (for permission inheritance).

    Args:
        role_name: The role name to get hierarchy for

    Returns:
        List of parent role names including the role itself
    """
    hierarchy = ROLE_HIERARCHY.get(role_name, [])
    return [role_name] + hierarchy


def is_clinical_role(role_name):
    """Check if a role is a clinical role"""
    return role_name in CLINICAL_ROLES


def is_reception_role(role_name):
    """Check if a role is a reception/front desk role"""
    return role_name in RECEPTION_ROLES


def is_finance_role(role_name):
    """Check if a role is a finance role"""
    return role_name in FINANCE_ROLES


def is_admin_role(role_name):
    """Check if a role is an admin role"""
    return role_name in ADMIN_ROLES


def get_all_roles():
    """Get list of all role names"""
    return [choice[0] for choice in ROLE_CHOICES]


def get_role_display_name(role_name):
    """Get human-readable display name for a role"""
    for choice in ROLE_CHOICES:
        if choice[0] == role_name:
            return choice[1]
    return role_name.replace("_", " ").title()
