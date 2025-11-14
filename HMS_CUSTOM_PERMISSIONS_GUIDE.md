# HMS Custom Permissions System - Complete Guide

## Overview

The HMS (Hospital Management System) uses a **two-tier permission system** combining Django's built-in permissions with custom HMS permissions for fine-grained access control.

---

## Architecture

### Two Permission Layers

1. **Django Permissions** (Database Layer)
   - Stored in database as Permission objects
   - Format: `{module}_{action}` (e.g., `patients_view`, `consultations_create`)
   - Assigned to roles in the database
   - Low-level technical permissions

2. **HMS Custom Permissions** (Application Layer)
   - Defined in `core/permissions.py` → `APP_PERMISSIONS`
   - Format: `{action}_{object}` (e.g., `view_patients`, `create_invoice`)
   - Human-readable, feature-level permissions
   - Used in templates and views for access control

### Permission Mapping

The `ROLE_TO_CORE_PERMISSION_MAPPING` in `core/permissions.py` maps:
- **Django role permissions** (e.g., `patients.view`)
- **TO HMS custom permissions** (e.g., `view_patients`)

```python
'nurse': {
    'patients.view': 'view_patients',      # Django → HMS Custom
    'patients.edit': 'edit_patient',
    'vitals.create': 'manage_vitals',
    ...
}
```

---

## HMS Custom Permission Categories

### 1. USER_MANAGEMENT (9 permissions)
Administrative user and role management

| Custom Permission | Description | Typical Roles |
|-------------------|-------------|---------------|
| `view_dashboard` | Main dashboard access | All |
| `view_user_management` | User admin area | Admin |
| `view_admin_tools` | Admin tools access | Admin |
| `create_user` | Create new users | Admin |
| `edit_user` | Edit user accounts | Admin |
| `delete_user` | Delete users | Admin |
| `view_users` | View user list | Admin |
| `manage_roles` | Assign/modify roles | Admin |
| `reset_password` | Reset user passwords | Admin |

### 2. PATIENT_MANAGEMENT (7 permissions)
Patient registration and information management

| Custom Permission | Description | Typical Roles |
|-------------------|-------------|---------------|
| `create_patient` | Register new patients | Receptionist, Admin, HRO |
| `edit_patient` | Edit patient info | Nurse, Doctor, Admin, HRO |
| `delete_patient` | Delete patient records | Admin, HRO |
| `view_patients` | View patient details | Nurse, Doctor, Receptionist, Admin |
| `access_sensitive_data` | Medical history access | Doctor, Nurse, Admin |
| `manage_patient_admission` | Admit patients | Doctor, Nurse, Admin |
| `manage_patient_discharge` | Discharge patients | Doctor, Admin |

### 3. BILLING_MANAGEMENT (7 permissions)
Financial and billing operations

| Custom Permission | Description | Typical Roles |
|-------------------|-------------|---------------|
| `create_invoice` | Create invoices | Accountant, Receptionist, Admin |
| `edit_invoice` | Edit invoices | Accountant, Admin |
| `delete_invoice` | Delete invoices | Admin |
| `view_invoices` | View billing data | Accountant, Admin |
| `process_payments` | Process payments | Accountant, Admin |
| `manage_wallet` | Patient wallet ops | Accountant, Receptionist, Admin |
| `view_financial_reports` | View revenue reports | Accountant, Admin |

### 4. PHARMACY_MANAGEMENT (9 permissions)
Medication and inventory management

| Custom Permission | Description | Typical Roles |
|-------------------|-------------|---------------|
| `manage_inventory` | Inventory control | Pharmacist, Admin |
| `dispense_medication` | Dispense drugs | Pharmacist, Admin |
| `create_prescription` | Create prescriptions | Doctor, Admin |
| `edit_prescription` | Edit prescriptions | Doctor, Pharmacist, Admin |
| `view_prescriptions` | View Rx history | Nurse, Doctor, Pharmacist, Admin |
| `manage_dispensary` | Dispensary ops | Pharmacist, Admin |
| `transfer_medication` | Inter-dispensary transfers | Pharmacist, Admin |
| `can_approve_purchases` | Approve POs | Pharmacist, Admin |
| `can_process_payments` | Purchase payments | Pharmacist, Admin |

### 5. LABORATORY_MANAGEMENT (5 permissions)
Lab test and results management

| Custom Permission | Description | Typical Roles |
|-------------------|-------------|---------------|
| `create_test_request` | Order lab tests | Doctor, Admin |
| `enter_results` | Enter test results | Lab Technician, Admin |
| `edit_results` | Modify results | Lab Technician, Admin |
| `view_tests` | View test data | Lab Technician, Doctor, Admin |
| `manage_lab_equipment` | Equipment management | Lab Technician, Admin |

### 6. RADIOLOGY_MANAGEMENT (4 permissions)
Imaging services management

| Custom Permission | Description | Typical Roles |
|-------------------|-------------|---------------|
| `create_radiology_request` | Order imaging | Doctor, Admin |
| `enter_radiology_results` | Enter results | Radiology Staff, Admin |
| `edit_radiology_results` | Modify results | Radiology Staff, Admin |
| `view_radiology` | View imaging data | Radiology Staff, Doctor, Admin |

### 7. APPOINTMENT_MANAGEMENT (5 permissions)
Scheduling and appointments

| Custom Permission | Description | Typical Roles |
|-------------------|-------------|---------------|
| `create_appointment` | Schedule appointments | Doctor, Receptionist, Admin |
| `edit_appointment` | Modify appointments | Doctor, Receptionist, Admin |
| `cancel_appointment` | Cancel appointments | Doctor, Receptionist, Admin |
| `view_appointments` | View schedules | Nurse, Doctor, Receptionist, Admin |
| `manage_appointment_types` | Appointment settings | Admin |

### 8. INPATIENT_MANAGEMENT (5 permissions)
Ward and inpatient care

| Custom Permission | Description | Typical Roles |
|-------------------|-------------|---------------|
| `manage_admission` | Admit to ward | Nurse, Doctor, Admin |
| `manage_vitals` | Record vitals | Nurse, Admin |
| `manage_medication` | Inpatient meds | Nurse, Admin |
| `view_inpatient_records` | View ward data | Nurse, Doctor, Admin |
| `manage_discharge` | Discharge from ward | Doctor, Admin |

### 9. REPORTING (5 permissions)
Reports and analytics

| Custom Permission | Description | Typical Roles |
|-------------------|-------------|---------------|
| `view_laboratory_reports` | Lab reports dashboard | Lab Technician, Accountant, Admin |
| `view_reports` | View system reports | All roles |
| `generate_reports` | Generate custom reports | Admin |
| `export_data` | Export system data | Admin |
| `view_analytics` | View analytics dashboard | Admin |

### 10. SYSTEM_ADMINISTRATION (5 permissions)
System configuration

| Custom Permission | Description | Typical Roles |
|-------------------|-------------|---------------|
| `system_configuration` | System settings | Admin |
| `manage_departments` | Manage departments | Admin |
| `view_audit_logs` | View audit logs | Admin |
| `backup_data` | Perform backups | Admin |
| `system_maintenance` | Maintenance tasks | Admin |

---

## Usage in Templates

### Load the Template Tags
```django
{% load core_tags %}
```

### Check Single Permission
```django
{% if user|has_permission:'view_patients' %}
    <a href="{% url 'patients:list' %}">View Patients</a>
{% endif %}
```

### Check Multiple Permissions (OR logic)
```django
{% if user|has_any_permission:'create_patient,edit_patient' %}
    <a href="{% url 'patients:register' %}">Patient Management</a>
{% endif %}
```

### Check Role
```django
{% if user|has_role:'nurse' %}
    <a href="{% url 'inpatient:bed_dashboard' %}">Bed Dashboard</a>
{% endif %}
```

### Combined Checks
```django
{% if user.is_superuser or user|has_permission:'manage_inventory' %}
    <a href="{% url 'pharmacy:inventory' %}">Pharmacy Inventory</a>
{% endif %}
```

---

## Usage in Views

### Decorator-based Protection
```python
from core.permissions import permission_required, any_permission_required

@permission_required('view_patients')
def patient_list(request):
    patients = Patient.objects.all()
    return render(request, 'patients/list.html', {'patients': patients})

@any_permission_required(['create_invoice', 'edit_invoice'])
def invoice_management(request):
    # View logic
    pass
```

### Manual Permission Checking
```python
from core.permissions import RolePermissionChecker

def my_view(request):
    checker = RolePermissionChecker(request.user)

    if checker.has_permission('manage_inventory'):
        # Allow access
        pass
    else:
        return HttpResponseForbidden("No access")
```

---

## Role-to-Permission Mapping

### Nurse Role Example

**Django Permissions** (17 total):
```python
'nurse': [
    'patients.view',
    'patients.edit',
    'medical.view',
    'medical.create',
    'medical.edit',
    'vitals.view',
    'vitals.create',
    'vitals.edit',
    'consultations.view',
    'referrals.view',
    'referrals.create',
    'prescriptions.view',
    'appointments.view',
    'inpatient.view',
    'inpatient.create',
    'inpatient.edit',
    'reports.view',
]
```

**Mapped to HMS Custom Permissions**:
```python
'nurse': {
    'patients.view': 'view_patients',
    'patients.edit': 'edit_patient',
    'medical.view': 'access_sensitive_data',
    'medical.create': 'access_sensitive_data',
    'medical.edit': 'access_sensitive_data',
    'vitals.view': 'manage_vitals',
    'vitals.create': 'manage_vitals',
    'vitals.edit': 'manage_vitals',
    'consultations.view': 'access_sensitive_data',
    'referrals.view': 'view_patients',
    'referrals.create': 'create_appointment',
    'prescriptions.view': 'view_prescriptions',
    'appointments.view': 'view_appointments',
    'inpatient.view': 'view_inpatient_records',
    'inpatient.create': 'manage_admission',
    'inpatient.edit': 'manage_vitals',
    'reports.view': 'view_reports',
}
```

**Result**: Nurse has these HMS custom permissions:
- ✅ `view_patients`
- ✅ `edit_patient`
- ✅ `access_sensitive_data`
- ✅ `manage_vitals`
- ✅ `manage_admission`
- ✅ `view_inpatient_records`
- ✅ `view_appointments`
- ✅ `view_prescriptions`
- ✅ `create_appointment`
- ✅ `view_reports`
- ❌ `create_patient` (NOT assigned)
- ❌ `manage_inventory` (NOT assigned)
- ❌ `create_invoice` (NOT assigned)

---

## Permission Checker Logic

The `RolePermissionChecker` class:

1. **Check if superuser** → Grant all permissions
2. **Check direct user permissions** → Django user_permissions
3. **Check role permissions**:
   - Get user's roles from database
   - For each role, get assigned Django permissions
   - Check if role permission maps to requested HMS custom permission
   - Return True if mapping exists AND user has the Django permission

### Example Flow

User requests: `has_permission('view_patients')`

1. User is nurse (not superuser)
2. Check nurse role Django permissions
3. Find `patients.view` in nurse permissions
4. Check mapping: `'patients.view': 'view_patients'`
5. Mapping matches! Return `True`

User requests: `has_permission('create_invoice')`

1. User is nurse (not superuser)
2. Check nurse role Django permissions
3. No permission maps to `create_invoice`
4. Return `False`

---

## Testing Permissions

### Test Individual User
```python
from accounts.models import CustomUser
from core.permissions import RolePermissionChecker

user = CustomUser.objects.get(username='nurse_jane')
checker = RolePermissionChecker(user)

# Test permissions
print(checker.has_permission('view_patients'))  # True
print(checker.has_permission('create_invoice'))  # False
```

### Test in Django Shell
```bash
python manage.py shell

from accounts.models import CustomUser
from core.permissions import RolePermissionChecker

user = CustomUser.objects.get(id=8)
checker = RolePermissionChecker(user)

# Test multiple permissions
for perm in ['view_patients', 'manage_inventory', 'create_invoice']:
    print(f"{perm}: {checker.has_permission(perm)}")
```

---

## Troubleshooting

### Issue: User has permission in database but checker returns False

**Cause**: No mapping exists from Django permission to HMS custom permission

**Solution**: Add mapping in `ROLE_TO_CORE_PERMISSION_MAPPING`

```python
'your_role': {
    'django_perm.action': 'hms_custom_permission',
}
```

### Issue: Template shows menu item when it shouldn't

**Cause**: Using broad permission check (e.g., `has_any_permission`)

**Solution**: Use specific permission or role check

```django
<!-- Bad: Shows to anyone with ANY pharmacy permission -->
{% if user|has_any_permission:'manage_inventory,dispense_medication,view_prescriptions' %}

<!-- Good: Shows only to pharmacists -->
{% if user.is_superuser or user|has_role:'pharmacist' %}
```

### Issue: Permission works in shell but not in templates

**Cause**: Template tag cache or incorrect filter

**Solution**:
1. Restart Django server
2. Clear browser cache
3. Verify template loads `{% load core_tags %}`

---

## Best Practices

### 1. Use HMS Custom Permissions in Templates
```django
✅ {% if user|has_permission:'view_patients' %}
❌ {% if user.has_perm('patients.view_patient') %}
```

### 2. Use Role Checks for Module Access
```django
✅ {% if user.is_superuser or user|has_role:'pharmacist' %}
❌ {% if user|has_any_permission:'all,pharmacy,permissions' %}
```

### 3. Be Specific with Permissions
```django
✅ {% if user|has_permission:'create_invoice' %}
❌ {% if user|has_any_permission:'view_invoices,create_invoice,edit_invoice' %}
```

### 4. Combine Superuser Check
```django
✅ {% if user.is_superuser or user|has_permission:'manage_users' %}
❌ {% if user|has_permission:'manage_users' %} <!-- Misses superuser -->
```

---

## Summary

- **61 total HMS custom permissions** across 10 categories
- **Two-tier system**: Django permissions → HMS custom permissions
- **Mapping required**: Define in `ROLE_TO_CORE_PERMISSION_MAPPING`
- **Use in templates**: `{% if user|has_permission:'custom_permission' %}`
- **Use in views**: `@permission_required('custom_permission')`
- **Check logic**: Superuser → Direct perms → Role mapping → False

---

**Last Updated**: 2025-01-14
**Version**: 2.0
**Status**: ✅ Production Ready
