# Strict Access Control System

## Overview

The HMS now implements a **Strict Access Control** system that enforces a "deny by default" security policy. This means:

- **All users** are denied access to **all resources** by default
- Users can only access resources they are **explicitly permitted** to access
- Access is granted through **roles** or **individual permissions**
- **No implicit access** is granted based on authentication alone

## Key Features

### 1. Deny by Default
Every URL in the system requires explicit permission. If a user doesn't have the required permission, they are denied access with a clear explanation.

### 2. Role-Based Access Control (RBAC)
Users are assigned roles (e.g., doctor, nurse, pharmacist) that grant them a set of permissions. Roles can be customized and permissions can be assigned individually.

### 3. Permission Inheritance
Roles can inherit permissions from parent roles, creating a hierarchy (e.g., Senior Doctor inherits from Doctor).

### 4. Audit Logging
All permission denials are logged for security monitoring and compliance.

### 5. Specialty Module Support
All medical specialty modules (dental, ophthalmic, ENT, oncology, etc.) have their own permission sets.

## Configuration

### Enable/Disable Strict Mode

In `settings.py`:

```python
# Enable strict access control (recommended for production)
STRICT_ACCESS_CONTROL = True

# Or use environment variable
STRICT_ACCESS_CONTROL = os.environ.get(
    "STRICT_ACCESS_CONTROL", "True" if not DEBUG else "False"
) == "True"
```

### Public URLs

URLs that don't require any permission can be configured:

```python
PUBLIC_URLS = [
    '/custom-public-url/',
    '/api/public/',
]
```

### Default Public URLs

These URLs are always accessible without permission:
- `/accounts/login/`
- `/accounts/logout/`
- `/accounts/password-reset/`
- `/static/`
- `/media/`
- `/admin/login/`
- `/health/`
- `/ping/`

## How It Works

### Access Control Flow

1. **Request received** → Middleware intercepts
2. **Check if public** → Allow if in public list
3. **Check authentication** → Redirect to login if not authenticated
4. **Check permission** → Verify user has required permission
5. **Allow or deny** → Grant access or show permission denied page

### Permission Check Priority

1. **Superusers** → Full access (bypass all checks)
2. **Explicit permission** → User has the specific permission
3. **Role-based access** → User's role grants the permission
4. **Deny** → No permission found, access denied

## Available Permissions

### Core Modules

| Permission | Description |
|------------|-------------|
| `patients.view` | View patient records |
| `patients.create` | Create new patients |
| `patients.edit` | Edit patient records |
| `patients.delete` | Delete patient records |
| `consultations.view` | View consultations |
| `consultations.create` | Create consultations |
| `consultations.edit` | Edit consultations |
| `pharmacy.view` | View pharmacy records |
| `pharmacy.dispense` | Dispense medications |
| `lab.view` | View lab tests |
| `lab.results` | Enter lab results |
| `billing.view` | View invoices |
| `billing.process_payment` | Process payments |
| `appointments.view` | View appointments |
| `inpatient.view` | View admissions |
| `inpatient.discharge` | Discharge patients |
| `users.view` | View user accounts |
| `reports.view` | View reports |

### Specialty Modules

| Permission | Description |
|------------|-------------|
| `dental.view` | View dental records |
| `ophthalmic.view` | View ophthalmic records |
| `ent.view` | View ENT records |
| `oncology.view` | View oncology records |
| `cardiology.view` | View cardiology records |
| `orthopedics.view` | View orthopedics records |
| `neurology.view` | View neurology records |
| `dermatology.view` | View dermatology records |
| `pediatrics.view` | View pediatrics records |
| `emergency.view` | View emergency records |

*(All specialty modules have `.view`, `.create`, and `.edit` permissions)*

## Predefined Roles

### 1. Admin
Full access to all modules and functions.

### 2. Doctor
- View patients
- Create/edit consultations
- Create prescriptions
- View medical records
- View lab results
- Create admissions

### 3. Nurse
- View patients
- Create/edit vitals
- View consultations
- Create referrals
- View admissions

### 4. Pharmacist
- View pharmacy
- Dispense medications
- View prescriptions
- Edit prescriptions

### 5. Lab Technician
- View lab tests
- Create lab tests
- Enter lab results

### 6. Accountant
- View billing
- Create/edit invoices
- Process payments
- Manage wallets

### 7. Receptionist
- View/create patients
- Create appointments
- View billing (create invoices)

### 8. Health Record Officer
- Full patient management
- Medical records
- Billing access
- Appointments

### 9. Radiology Staff
- View radiology tests
- Create/edit radiology records

## Using Permissions in Code

### In Views

```python
from accounts.permissions import permission_required, role_required

@login_required
@permission_required('patients.view')
def patient_list(request):
    # Only users with patients.view permission can access
    pass

@login_required
@role_required(['doctor', 'nurse'])
def medical_records(request):
    # Only doctors and nurses can access
    pass
```

### In Templates

```html
{% load permission_tags %}

<!-- Check permission -->
{% if user|has_permission:'patients.view' %}
    <a href="{% url 'patients:list' %}">View Patients</a>
{% endif %}

<!-- Check role -->
{% if user|in_role:'doctor' %}
    <span class="badge">Doctor</span>
{% endif %}

<!-- Check any permission -->
{% if user|has_any_permission:'patients.view,consultations.view' %}
    <!-- Show if user has any of these permissions -->
{% endif %}

<!-- Resource-based checks -->
{% if user|can_view:'patient' %}
    <a href="{{ patient.get_absolute_url }}">View</a>
{% endif %}

{% if user|can_edit:'patient' %}
    <a href="{% url 'patients:edit' patient.id %}">Edit</a>
{% endif %}

{% if user|can_process:'payment' %}
    <button>Process Payment</button>
{% endif %}
```

## Managing Roles and Permissions

### Assigning Roles to Users

```python
from accounts.models import CustomUser, Role

# Get user and role
user = CustomUser.objects.get(username='john_doe')
role = Role.objects.get(name='doctor')

# Assign role
user.roles.add(role)

# Remove role
user.roles.remove(role)

# Check role
if user.roles.filter(name='doctor').exists():
    print("User is a doctor")
```

### Creating Custom Roles

```python
from accounts.models import Role
from django.contrib.auth.models import Permission

# Create role
role = Role.objects.create(
    name='senior_doctor',
    description='Senior Doctor with additional permissions'
)

# Add permissions
permission = Permission.objects.get(codename='view_patient')
role.permissions.add(permission)

# Set parent role (inherits permissions)
parent_role = Role.objects.get(name='doctor')
role.parent = parent_role
role.save()
```

### Assigning Individual Permissions

```python
from django.contrib.auth.models import Permission

# Get permission
permission = Permission.objects.get(codename='view_patient')

# Assign to user
user.user_permissions.add(permission)

# Remove from user
user.user_permissions.remove(permission)
```

## URL Permission Mapping

The middleware automatically maps URLs to required permissions:

| URL Namespace | Required Permission |
|---------------|-------------------|
| `patients` | `patients.view` |
| `consultations` | `consultations.view` |
| `pharmacy` | `pharmacy.view` |
| `billing` | `billing.view` |
| `laboratory` | `lab.view` |
| `appointments` | `appointments.view` |
| `inpatient` | `inpatient.view` |
| `reports` | `reports.view` |
| `accounts` | `users.view` |
| `dental` | `dental.view` |
| `cardiology` | `cardiology.view` |
| *(all specialty modules)* | *(module).view` |

## Security Best Practices

### 1. Use Least Privilege
Assign users only the minimum permissions they need to perform their job.

### 2. Regular Audits
Review user permissions regularly and remove unnecessary access.

### 3. Role-Based Over Individual
Prefer assigning roles over individual permissions for easier management.

### 4. Test Permissions
Always test that users can only access what they should:

```python
# Test helper
def test_user_cannot_access_unauthorized_urls(self):
    self.client.login(username='nurse', password='password')
    
    # Nurse should not access billing
    response = self.client.get('/billing/')
    self.assertEqual(response.status_code, 403)
```

### 5. Monitor Denied Access
Check logs for unusual permission denial patterns:

```bash
# View recent permission denials
grep "PERMISSION_DENIED" logs/hms.log
```

## Troubleshooting

### User Can't Access Page They Should

1. Check user's roles: `user.roles.all()`
2. Check user's permissions: `user.get_all_permissions()`
3. Verify role has permission in ROLE_PERMISSIONS
4. Check if middleware is enabled: `STRICT_ACCESS_CONTROL = True`

### Permission Denied Errors

1. Check the error message for required permission
2. Verify the user's roles have that permission
3. Check URL permission mapping in middleware
4. Review logs for details

### Disabling Strict Mode (Not Recommended)

For development or troubleshooting only:

```python
STRICT_ACCESS_CONTROL = False
```

## Migration Guide

### From Legacy System

If upgrading from the old permission system:

1. **Enable strict mode** in development first
2. **Test all user roles** thoroughly
3. **Update any custom views** that relied on implicit access
4. **Add missing permissions** to ROLE_PERMISSIONS
5. **Deploy with logging enabled** to catch issues
6. **Monitor permission denials** after deployment

### Backward Compatibility

The system maintains backward compatibility:
- Old `@login_required` views still work
- Template role checks still function
- Users with legacy profile.role are supported
- Gradual migration path available

## Support

For issues or questions about the strict access control system:

1. Check the logs for detailed error messages
2. Verify user roles and permissions in admin
3. Review this documentation
4. Contact system administrator

---

**Note**: This system is designed to be secure by default. When in doubt, deny access rather than grant it. It's easier to add permissions than to remove unauthorized access.
