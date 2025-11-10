# HMS Permission System - Complete Guide

## Overview

The HMS permission system has been enhanced to bridge the gap between UI-granted permissions and sidebar access control. This guide explains how the system works and how to use it effectively.

## Problem Solved

### Before
- **Sidebar** checked for custom permissions like `view_dashboard`, `manage_inventory`, etc.
- **Permission UI** only showed Django's auto-generated model permissions
- **Result**: Granting permissions via UI didn't give users access to sidebar items

### After
- Custom HMS permissions are now stored in the database as Permission objects
- Permission UI shows custom permissions FIRST, organized by category
- Granting custom permissions via UI now works with sidebar access control
- All existing functionality is preserved

## System Architecture

### 1. Permission Definition (`core/permissions.py`)

Custom permissions are defined in `APP_PERMISSIONS` dictionary with 9 categories:

```python
APP_PERMISSIONS = {
    'user_management': {
        'view_dashboard': 'Can view the main dashboard',
        'create_user': 'Can create new users',
        # ... more permissions
    },
    'patient_management': { ... },
    'billing_management': { ... },
    'pharmacy_management': { ... },
    'laboratory_management': { ... },
    'radiology_management': { ... },
    'appointment_management': { ... },
    'inpatient_management': { ... },
    'reporting': { ... },
    'system_administration': { ... }
}
```

### 2. Permission Checking (`core/permissions.py` & `core/templatetags/core_tags.py`)

The `RolePermissionChecker` class checks permissions in this order:

1. **Superuser** → Always has all permissions
2. **User-specific permissions** → Checks `user.user_permissions` (Django auth)
3. **Role-based permissions** → Checks permissions from assigned roles

Template tags for sidebar:
- `{% if user|has_permission:'view_dashboard' %}` - Single permission
- `{% if user|has_any_permission:'permission1,permission2' %}` - Any of multiple

### 3. Sidebar Access Control (`templates/includes/sidebar.html`)

Each sidebar item checks permissions before displaying:

```django
{% if user|has_permission:'view_dashboard' %}
<li class="nav-item">
    <a class="nav-link" href="{% url 'dashboard:dashboard' %}">
        <span>Dashboard</span>
    </a>
</li>
{% endif %}
```

### 4. Permission Management UI (`accounts/views.py` & templates)

**View Enhancement** (`superuser_manage_user_permissions`):
- Separates custom HMS permissions from model permissions
- Orders custom permissions first
- Provides `app_permissions` context for category grouping

**Template Enhancement** (`manage_user_permissions.html`):
- Shows custom permissions in their categories with icons
- Clearly distinguishes custom vs model permissions
- Better UX with search and bulk operations

## Setup & Usage

### Initial Setup (One-time)

1. **Create Custom Permissions in Database**
   ```bash
   python manage.py create_custom_permissions
   ```

   This creates 58+ custom permission objects from `APP_PERMISSIONS`

   Options:
   - `--dry-run` - Preview what would be created
   - `--force` - Update existing permissions

2. **Verify Permissions Created**
   ```bash
   python manage.py shell
   >>> from django.contrib.auth.models import Permission
   >>> Permission.objects.filter(content_type__model='custompermission').count()
   58  # Should show number of custom permissions
   ```

### Granting Permissions to Users

#### Via UI (Recommended)

1. Navigate to: `http://127.0.0.1:8000/accounts/superuser/user-permissions/`

2. Click "Manage Permissions" for a user

3. You'll see two sections:
   - **HMS Custom Permissions** (for sidebar/feature access)
     - user_management
     - patient_management
     - billing_management
     - pharmacy_management
     - laboratory_management
     - radiology_management
     - appointment_management
     - inpatient_management
     - reporting
     - system_administration

   - **Django Model Permissions** (for CRUD operations)

4. Check permissions you want to grant

5. Click "Save Permissions"

6. **User immediately gets sidebar access** based on granted permissions

#### Via Django Admin

1. Go to Admin → Users → Select user → User permissions
2. Search for custom permissions (they have content_type: custompermission)
3. Add to "Chosen permissions"
4. Save

#### Programmatically

```python
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

User = get_user_model()
user = User.objects.get(username='doctor_john')

# Grant specific permission
perm = Permission.objects.get(codename='view_dashboard')
user.user_permissions.add(perm)

# Grant multiple permissions
perms = Permission.objects.filter(codename__in=[
    'view_patients',
    'create_consultation',
    'view_prescriptions'
])
user.user_permissions.add(*perms)
```

## Permission Categories & Codenames

### User Management
- `view_dashboard` - Dashboard access
- `create_user`, `edit_user`, `delete_user`, `view_users`
- `manage_roles`, `reset_password`

### Patient Management
- `view_patients`, `create_patient`, `edit_patient`, `delete_patient`
- `access_sensitive_data`
- `manage_patient_admission`, `manage_patient_discharge`

### Billing Management
- `view_invoices`, `create_invoice`, `edit_invoice`, `delete_invoice`
- `process_payments`, `manage_wallet`
- `view_financial_reports`

### Pharmacy Management
- `manage_inventory`, `dispense_medication`
- `view_prescriptions`, `create_prescription`, `edit_prescription`
- `manage_dispensary`, `transfer_medication`

### Laboratory Management
- `view_tests`, `create_test_request`
- `enter_results`, `edit_results`
- `manage_lab_equipment`

### Radiology Management
- `view_radiology`, `create_radiology_request`
- `enter_radiology_results`, `edit_radiology_results`

### Appointment Management
- `view_appointments`, `create_appointment`
- `edit_appointment`, `cancel_appointment`
- `manage_appointment_types`

### Inpatient Management
- `view_inpatient_records`, `manage_admission`, `manage_discharge`
- `manage_vitals`, `manage_medication`

### Reporting
- `view_reports`, `generate_reports`, `export_data`
- `view_analytics`, `view_laboratory_reports`

### System Administration
- `system_configuration`, `manage_departments`
- `view_audit_logs`, `backup_data`, `system_maintenance`

## Testing the System

### Test Scenario 1: Grant Dashboard Access

1. Create a test user (or use existing non-superuser)
2. Go to permission management UI
3. Grant "view_dashboard" permission
4. Login as that user
5. **Result**: Dashboard should now appear in sidebar

### Test Scenario 2: Grant Pharmacy Access

1. Grant these permissions to a user:
   - `manage_inventory`
   - `dispense_medication`
   - `view_prescriptions`

2. Login as that user
3. **Result**: Pharmacy menu appears in sidebar with accessible items

### Test Scenario 3: Remove Permission

1. Uncheck a permission in UI
2. Save
3. Login as that user
4. **Result**: Corresponding sidebar item disappears

## Troubleshooting

### Sidebar Item Not Showing After Granting Permission

**Check:**
1. Permission codename matches exactly (case-sensitive)
   ```bash
   python manage.py shell
   >>> from django.contrib.auth.models import Permission
   >>> Permission.objects.filter(codename='view_dashboard').exists()
   True
   ```

2. Permission is actually assigned
   ```python
   >>> user.user_permissions.filter(codename='view_dashboard').exists()
   True
   ```

3. User has logged out and back in (session refresh)

4. Sidebar template tag is correct
   ```django
   {% if user|has_permission:'view_dashboard' %}
   ```

### "Multiple permissions returned" Error

If you see this during permission creation, it means duplicate permissions exist.

**Fix:**
```bash
python manage.py shell
>>> from django.contrib.auth.models import Permission
>>> duplicates = Permission.objects.filter(codename='delete_invoice')
>>> print(duplicates.count())
2
>>> # Keep the custom one, delete the duplicate
>>> duplicates.filter(content_type__model='invoice').delete()
```

### Permission Not Taking Effect

**Reasons:**
1. User's session is cached - **Solution**: Logout and login
2. Role has conflicting permissions - **Solution**: Check role permissions
3. Permission checking code has typo - **Solution**: Check template/view code

## Best Practices

### 1. Use Custom Permissions for Features
- Sidebar access → Custom permissions
- CRUD operations → Model permissions (auto-generated)

### 2. Grant Permissions by Job Role
Create role templates:
- **Doctor**: view_dashboard, view_patients, create_consultation, view_prescriptions
- **Nurse**: view_dashboard, view_patients, manage_vitals, view_inpatient_records
- **Pharmacist**: view_dashboard, manage_inventory, dispense_medication, view_prescriptions
- **Receptionist**: view_dashboard, create_patient, create_appointment, view_appointments

### 3. Audit Permission Changes
The system logs all permission changes:
```python
# View logs
from core.models import AuditLog
logs = AuditLog.objects.filter(action__icontains='permission').order_by('-timestamp')
```

### 4. Regular Permission Review
```bash
# List users with specific permission
python manage.py shell
>>> from django.contrib.auth.models import Permission
>>> perm = Permission.objects.get(codename='view_dashboard')
>>> users = perm.user_set.all()
>>> for user in users:
...     print(f"{user.username}: {user.email}")
```

## Advanced: Adding New Custom Permissions

### 1. Update APP_PERMISSIONS

Edit `core/permissions.py`:

```python
APP_PERMISSIONS = {
    # ... existing categories
    'new_category': {
        'new_permission': 'Description of new permission',
    }
}
```

### 2. Create Permission in Database

```bash
python manage.py create_custom_permissions --force
```

### 3. Add to Sidebar

Edit `templates/includes/sidebar.html`:

```django
{% if user|has_permission:'new_permission' %}
<li class="nav-item">
    <a class="nav-link" href="{% url 'some:url' %}">
        <i class="fas fa-icon"></i>
        <span>New Feature</span>
    </a>
</li>
{% endif %}
```

### 4. Add to Views (Optional)

Use permission decorators:

```python
from core.permissions import permission_required

@permission_required(['new_permission'])
def my_view(request):
    # View code
    pass
```

## Files Modified

1. **core/management/commands/create_custom_permissions.py** - NEW
   - Management command to create permissions

2. **core/permissions.py** - MODIFIED
   - Enhanced `RolePermissionChecker.has_permission()` to check user_permissions

3. **accounts/views.py** - MODIFIED
   - Updated `superuser_manage_user_permissions` to separate custom/model permissions

4. **templates/accounts/superuser/manage_user_permissions.html** - MODIFIED
   - Enhanced UI to show custom permissions first with categories

5. **templates/includes/sidebar.html** - NO CHANGES
   - Already uses proper permission checks

## Migration Impact

✅ **No database migrations required**
✅ **No breaking changes**
✅ **Existing functionality preserved**
✅ **Backward compatible**

## Summary

The enhanced permission system:
- ✅ Creates custom permissions as database objects
- ✅ Shows custom permissions in UI first
- ✅ Makes UI-granted permissions effective for sidebar access
- ✅ Preserves all existing role-based permissions
- ✅ Maintains backward compatibility
- ✅ Provides clear documentation

Users can now be granted permissions via the UI, and those permissions will immediately control their access to sidebar items and features.
