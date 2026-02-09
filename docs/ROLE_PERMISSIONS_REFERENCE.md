# HMS Role & Permissions Reference

Complete reference for the Hospital Management System's Role-Based Access Control (RBAC) system.

## Table of Contents

1. [Overview](#overview)
2. [Standard Roles](#standard-roles)
3. [Permission Categories](#permission-categories)
4. [Complete Permission Matrix](#complete-permission-matrix)
5. [Role Hierarchy & Inheritance](#role-hierarchy--inheritance)
6. [Adding New Permissions](#adding-new-permissions)
7. [Custom Role Creation](#custom-role-creation)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The HMS RBAC system provides fine-grained access control through:

- **Roles**: Named collections of permissions (e.g., Doctor, Nurse, Admin)
- **Permissions**: Individual access rights (e.g., `patients.view`, `lab.edit`)
- **Role Inheritance**: Parent roles pass permissions to child roles
- **User-Role M2M**: Users can have multiple roles

### Key Concepts

1. **Custom Permission Keys**: Human-friendly identifiers like `'patients.view'`
2. **Django Permissions**: Underlying `app_label.codename` format (e.g., `'patients.view_patient'`)
3. **Single Source of Truth**: `accounts/permissions.py` - `PERMISSION_DEFINITIONS` dict
4. **Automatic Mapping**: Custom keys auto-convert to Django permissions

---

## Standard Roles

### 1. Administrator (admin)
**Description**: System Administrator - Full access to all HMS modules and user management

**Permissions**: All permissions (via superuser status)

**Use Cases**:
- System configuration
- User management
- Emergency override access

**Inheritance**: No parent (top-level)

---

### 2. Doctor (doctor)
**Description**: Medical Doctor - Patient care and medical operations

**Permissions**:
- **Patient Management**: view, edit
- **Medical Records**: view, create, edit
- **Vitals**: view, create, edit
- **Consultations**: view, create, edit
- **Referrals**: view, create
- **Prescriptions**: view, create, edit
- **Laboratory**: view, create
- **Appointments**: view, create
- **Inpatient**: view, create, edit
- **Reports**: view

**Typical Users**: Medical practitioners, consultants

---

### 3. Nurse (nurse)
**Description**: Registered Nurse - Patient care and vitals monitoring

**Permissions**:
- **Patient Management**: view, edit
- **Medical Records**: view, create, edit
- **Vitals**: view, create, edit
- **Consultations**: view
- **Referrals**: view, create
- **Prescriptions**: view
- **Appointments**: view
- **Inpatient**: view, create, edit
- **Reports**: view

**Typical Users**: Registered nurses, nursing staff

---

### 4. Receptionist (receptionist)
**Description**: Front Desk Receptionist & Health Records - Patient registration, appointments, and records

**Permissions**:
- **Patient Management**: view, create, edit, delete
- **Medical Records**: view, create, edit, delete
- **Vitals**: view, create, edit, delete
- **Consultations**: view, create
- **Appointments**: view, create, edit
- **Reports**: view

**Typical Users**: Front desk staff, health records officers

---

### 5. Pharmacist (pharmacist)
**Description**: Licensed Pharmacist - Medication management and dispensing

**Permissions**:
- **Patient Management**: view
- **Pharmacy**: view, create, edit, dispense
- **Prescriptions**: view, edit
- **Reports**: view

**Typical Users**: Pharmacy staff, dispensary managers

---

### 6. Laboratory Technician (lab_technician)
**Description**: Laboratory Technician - Test management and results

**Permissions**:
- **Patient Management**: view
- **Laboratory**: view, create, edit, results
- **Prescriptions**: view
- **Reports**: view

**Typical Users**: Lab techs, pathologists

---

### 7. Accountant (accountant)
**Description**: Hospital Accountant - Financial management and billing

**Permissions**:
- **Patient Management**: view
- **Billing**: view, create, edit, process_payment
- **Wallet**: view, edit, transactions, manage
- **Reports**: view

**Typical Users**: Finance staff, billing officers

---

### 8. Health Record Officer (health_record_officer)
**Description**: Health Record Officer & Receptionist - Medical records and front desk operations

**Permissions**: (Combined nurse + receptionist + billing view)
- **Patient Management**: view, create, edit, delete
- **Medical Records**: view, create, edit, delete
- **Vitals**: view, create, edit, delete
- **Consultations**: view, create
- **Appointments**: view, create, edit
- **Billing**: view, create, edit, process_payment
- **Wallet**: view, edit, transactions
- **Reports**: view

**Typical Users**: Health information managers, senior receptionists

---

### 9. Radiology Staff (radiology_staff)
**Description**: Radiology Technician - Imaging services

**Permissions**:
- **Patient Management**: view
- **Radiology**: view, create, edit
- **Reports**: view

**Typical Users**: Radiographers, imaging techs

---

## Permission Categories

### Patient Management
Core patient data operations on the `Patient` model.
- `patients.view` - View patient records
- `patients.create` - Register new patients
- `patients.edit` - Edit patient information
- `patients.delete` - Delete patient records
- `patients.toggle_status` - Activate/deactivate patients (custom)
- `patients.wallet_manage` - Manage wallet balances (custom)
- `patients.nhia_manage` - Manage NHIA status (custom)

### Medical Records
Medical history and vital signs (models: `MedicalHistory`, `VitalSign`)
- `medical.view/create/edit/delete` - CRUD on medical history
- `vitals.view/create/edit/delete` - CRUD on vital signs

### Consultations
Consultations and referrals (models: `Consultation`, `Referral`)
- `consultations.view/create/edit/delete`
- `referrals.view/create/edit/delete`

### Pharmacy
Medication and prescription management (models: `Pharmacy`, `Prescription`)
- `pharmacy.view/create/edit/dispense`
- `prescriptions.view/create/edit/delete`

### Laboratory
Lab tests and results (model: `LabTest`)
- `lab.view/create/edit/delete`
- `lab.results` - Enter/edit lab results (custom)

### Billing & Finance
Invoices, payments, wallets (models: `Invoice`, `Payment`, `Wallet`)
- `billing.view/create/edit/delete/process_payment`
- `wallet.view/create/edit/delete/transactions/manage`

### Appointments
Appointment scheduling (model: `Appointment`)
- `appointments.view/create/edit/delete`

### Inpatient Management
Admissions and discharges (model: `Admission`)
- `inpatient.view/create/edit/delete`
- `inpatient.discharge` - Discharge patients (custom)

### User & Role Management
User and role administration (models: `CustomUser`, `Role`)
- `users.view/create/edit/delete`
- `roles.view/create/edit/delete`

### Reports
Report generation and viewing
- `reports.view` - View reports
- `reports.generate` - Generate reports (custom)

### Radiology
Imaging services (model: `RadiologyService`)
- `radiology.view/create/edit/delete`

---

## Complete Permission Matrix

### Role × Permission Mapping

| Permission Key | admin | doctor | nurse | receptionist | pharmacist | lab_tech | accountant | hro | radiology |
|----------------|-------|--------|-------|--------------|------------|----------|------------|-----|-----------|
| patients.view | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| patients.create | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| patients.edit | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| patients.delete | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| patients.toggle_status | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| patients.wallet_manage | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| patients.nhia_manage | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **medical.view** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **medical.create** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **medical.edit** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **medical.delete** | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **vitals.view** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **vitals.create** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **vitals.edit** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **vitals.delete** | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **consultations.view** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **consultations.create** | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **consultations.edit** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **consultations.delete** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **referrals.view** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **referrals.create** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **referrals.edit** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **referrals.delete** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **pharmacy.view** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **pharmacy.create** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **pharmacy.edit** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **pharmacy.dispense** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **prescriptions.view** | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **prescriptions.create** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **prescriptions.edit** | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **prescriptions.delete** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **lab.view** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **lab.create** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **lab.edit** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **lab.delete** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **lab.results** | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **billing.view** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **billing.create** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **billing.edit** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **billing.delete** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **billing.process_payment** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **wallet.view** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **wallet.create** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **wallet.edit** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **wallet.delete** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **wallet.transactions** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| **wallet.manage** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **appointments.view** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **appointments.create** | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **appointments.edit** | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **inpatient.view** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **inpatient.create** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **inpatient.edit** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **inpatient.discharge** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **reports.view** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **reports.generate** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **users.view** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **users.create** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **users.edit** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **users.delete** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **roles.view** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **roles.create** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **roles.edit** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Role Hierarchy & Inheritance

### Understanding Inheritance

Roles can have a parent role. Permissions cascade down automatically:

```
admin (no parent)
   ↓ (inherits all admin perms)
 senior_doctor (parent: admin)
   ↓ (inherits senior_doctor perms + admin perms)
 junior_doctor (parent: senior_doctor)
```

**Inheritance Rules**:
- A role with a parent inherits **ALL** parent permissions
- Inheritance is transitive (grandparent → parent → child)
- Circular references are prevented (validated)
- Direct permissions on a role are **added to** inherited permissions (no override)

### Why Inheritance Matters

```python
# Scenario: All medical staff need "patients.view"
# Option 1: Add to every role (redundant)
# Option 2: Create "medical_staff" role with that permission, then inherit

class Scenario:
    medical_staff (permissions: patients.view)
        ├── doctor (inherits patients.view)
        ├── nurse (inherits patients.view)
        └── pharmacist (inherits patients.view)

    # Now updating "medical_staff" auto-updates all children!
```

---

## Adding New Permissions

### Step 1: Define in PERMISSION_DEFINITIONS

Edit `accounts/permissions.py`:

```python
PERMISSION_DEFINITIONS = {
    # ... existing entries ...

    'your_module.action': {
        'django_codename': 'your_app.your_action',
        'category': 'your_category',
        'description': 'Can perform specific action',
        'model': 'YourModel',
        'is_custom': True,  # False if it's a standard Django perm
    },
}
```

**Required Fields**:
- `django_codename`: Must match Django's `app_label.codename` format
- `category`: Grouping for organization (must be unique in CATEGORY_PERMISSIONS)
- `description`: Human-readable explanation
- `model`: The model name this permission applies to
- `is_custom`: `True` for custom permissions, `False` for standard Django

### Step 2: Specify Django Permission

You need to create the Django Permission record. There are two ways:

**A. Via Model Meta (Recommended)**:
```python
class YourModel(models.Model):
    class Meta:
        permissions = [
            ('your_action', 'Can perform specific action'),
        ]
```

**B. Via Migration**:
Create a data migration that adds permissions to `auth_permission` table.

**C. Let Django auto-create**:
Run `python manage.py makemigrations && python manage.py migrate` - Django creates permissions for all models automatically based on `default` permissions (add/change/delete/view) plus any custom ones in Meta.permissions.

### Step 3: Assign to Roles

In `ROLE_PERMISSIONS` (same file):

```python
ROLE_PERMISSIONS = {
    'doctor': {
        'permissions': [
            # ... existing ...
            'your_module.action',  # Add custom key
        ]
    },
}
```

### Step 4: Validate & Sync

```bash
# Validate definitions
python manage.py validate_permissions

# Sync permissions to roles
python manage.py sync_role_permissions --fix
```

---

## Creating Custom Roles

### Via Admin Interface

1. Login as superuser
2. Go to **Roles** admin
3. Click **Add Role**
4. Fill in:
   - Name: `your_role`
   - Description: What it does
   - Parent: (optional) choose parent for inheritance
   - Permissions: Select from list

5. Save

### Via Management Command

Create a script:

```python
from accounts.models import Role
from django.contrib.auth.models import Permission

role = Role.objects.create(
    name='custom_role',
    description='Custom role description'
)

# Assign permissions
perm = Permission.objects.get(codename='view_patient', content_type__app_label='patients')
role.permissions.add(perm)

# Set parent for inheritance
role.parent = Role.objects.get(name='doctor')
role.save()
```

### Best Practices for Custom Roles

1. **Name**: Use snake_case, descriptive (e.g., `ward_supervisor`)
2. **Description**: Clearly state purpose and who it's for
3. **Parent**: Choose a parent role to inherit common permissions
4. **Minimize Duplication**: Rely on inheritance; don't copy parent permissions
5. **Test**: Verify with `validate_permissions` after creation

---

## Template Usage

### Checking Permissions

```django
{% load permission_tags %}

{% if user|has_permission:'patients.view' %}
    <a href="{% url 'patients:list' %}">View Patients</a>
{% endif %}

{% if user|has_any_permission:'patients.view,medical.view' %}
    You can see some patient data
{% endif %}
```

### Checking Roles

```django
{% if user|in_role:'doctor' %}
    Doctor Dashboard
{% endif %}

{% if user|in_role:'admin,doctor' %}
    Admin or Doctor access
{% endif %}

{% for role in user|get_user_roles_list %}
    <span class="badge">{{ role }}</span>
{% endfor %}
```

### Role Badges

```django
{{ role.name|role_badge }}                {# Default size #}
{{ role.name|role_badge:"sm" }}          {# Small #}
{{ role.name|role_badge:"lg" }}          {# Large #}
```

### Object-Level Checks

```django
{% can_edit_object patient as can_edit %}
{% if can_edit %}
    <button>Edit Patient</button>
{% endif %}

{% can_view_object consultation as can_view %}
{% can_delete_object invoice as can_delete %}
```

### Module Access

```django
{% module_available 'pharmacy' as can_access_pharmacy %}
{% if can_access_pharmacy %}
    <li><a href="{% url 'pharmacy:dashboard' %}">Pharmacy</a></li>
{% endif %}

{% visible_modules as modules %}
{% for module in modules %}
    <a href="{% url module ':dashboard' %}">{{ module|title }}</a>
{% endfor %}
```

### Permission Metadata

```django
{% permission_info 'patients.view' as perm_info %}
Description: {{ perm_info.description }}
Model: {{ perm_info.model }}
Category: {{ perm_info.category }}
```

---

## View Decorators

Use in `views.py`:

```python
from accounts.permissions import permission_required, role_required, any_permission_required

@permission_required('patients.view')
def patient_list(request):
    # Only users with patients.view can access
    pass

@role_required('doctor')
def doctor_dashboard(request):
    # Only doctors (or superusers)
    pass

@role_required(['admin', 'doctor'])  # Multiple roles accepted
def medical_staff_view(request):
    pass

@any_permission_required(['patients.view', 'medical.view'])
def data_view(request):
    # User needs at least one of these permissions
    pass
```

---

## Python API

### Core Functions

```python
from accounts.permissions import (
    user_has_permission,
    user_has_any_permission,
    user_has_all_permissions,
    user_in_role,
    user_in_all_roles,
    get_user_roles,
    get_permission_info,
    get_user_accessible_modules,
)

# Check individual permission
if user_has_permission(user, 'patients.view'):
    # Allow access

# Check any of several permissions
if user_has_any_permission(user, ['patients.view', 'medical.view']):
    pass

# Check role membership
if user_in_role(user, 'doctor'):
    pass

# Get all user roles (with inheritance)
roles = get_user_roles(user)  # Returns ['doctor', 'medical_staff', ...]

# Get permission metadata
info = get_permission_info('patients.view')
# {'django_codename': 'patients.view_patient', 'category': 'patient_management', ...}

# Get accessible modules
modules = get_user_accessible_modules(user)  # ['patients', 'appointments', ...]
```

---

## Management Commands

### 1. Populate Roles

```bash
# Create/update all default roles with permissions
python manage.py populate_roles

# Options:
python manage.py populate_roles --validate      # Check definitions only
python manage.py populate_roles --list-permissions  # Show all permissions
python manage.py populate_roles --dry-run      # Preview changes
python manage.py populate_roles --skip-permissions  # Create roles without perms
```

### 2. Validate Permissions

```bash
# Full validation
python manage.py validate_permissions

# With auto-fix for certain issues
python manage.py validate_permissions --fix

# Run specific checks only
python manage.py validate_permissions --checks=circular,users
```

### 3. Sync Role Permissions

```bash
# Sync all roles with canonical definitions
python manage.py sync_role_permissions

# With auto-fix
python manage.py sync_role_permissions --fix

# Dry run
python manage.py sync_role_permissions --dry-run

# Specific roles only
python manage.py sync_role_permissions --role=doctor,nurse

# Verbose output
python manage.py sync_role_permissions --fix --verbose
```

### 4. Migrate Legacy Profile Roles

```bash
# Dry run first!
python manage.py migrate_profile_roles --dry-run

# Actually migrate
python manage.py migrate_profile_roles

# Clear profile.role after verifying
python manage.py migrate_profile_roles --clear-profile-roles

# Use custom role mapping file
python manage.py migrate_profile_roles --role-mapping=mapping.json

# Create missing roles automatically
python manage.py migrate_profile_roles --create-missing-roles
```

---

## Troubleshooting

### Issue: "Permission not found in PERMISSION_DEFINITIONS"

**Cause**: Code uses a custom permission key not defined.

**Fix**:
1. Add entry to `PERMISSION_DEFINITIONS` in `accounts/permissions.py`
2. Or, use an existing key from `PERMISSION_DEFINITIONS`

### Issue: Permission exists in DB but not mapped

**Cause**: Django auto-created permissions (add/change/delete) but not in our definitions.

**Fix**:
```bash
python manage.py populate_roles --validate
```
Shows which permissions are missing.

### Issue: User not getting expected permissions

**Diagnosis**:
```python
# In Django shell
from accounts.permissions import get_user_roles, user_has_permission
user = User.objects.get(username='...')
roles = get_user_roles(user)
print('Roles:', roles)

for role in roles:
    from accounts.permissions import ROLE_PERMISSIONS
    print(f'  {role}:', ROLE_PERMISSIONS.get(role, {}).get('permissions', []))

# Test permission
print(user_has_permission(user, 'patients.view'))
```

**Common causes**:
- Role not assigned to user
- Role hasn't been populated (`populate_roles`)
- Permission key typo in ROLE_PERMISSIONS
- Cache not cleared (if using caching)

### Issue: Circular reference in role hierarchy

**Fix**:
```bash
python manage.py validate_permissions --fix
```
This will detect and optionally fix circular references.

### Issue: migrate_profile_roles doesn't map my custom role

**Fix**: Create custom mapping file `mapping.json`:

```json
{
    "my_custom_old_role": "new_role_name",
    "another_old_role": "another_new_role"
}
```

Then run:
```bash
python manage.py migrate_profile_roles --role-mapping=mapping.json
```

### Issue: Old template filters not working

**Update**: Old `role_tags.py` only had `lookup` filter. New `permission_tags.py` has comprehensive tags.

In templates:
```django
{% load permission_tags %}  {# Changed from role_tags #}

{% if user|has_permission:'patients.view' %}  {# Was: user|has_any_role:allowed_roles #}
{% if user|in_role:'doctor' %}  {# Was: user|has_any_role:allowed_roles #}
```

---

## Support & Further Reading

- **Developer Guide**: See `accounts/PERMISSIONS_README.md`
- **Migration Guide**: See `docs/PERMISSION_MIGRATION_GUIDE.md`
- **Architecture**: See `CLAUDE.md` in project root
- **Admin Interface**: Enhanced admin available at `/admin/`

---

**Last Updated**: 2025-02-08
**HMS Version**: 2.0 (RBAC Refactor)
