# Comprehensive Role-Based Access Control (RBAC) System for HMS

## Overview

The Hospital Management System now includes a comprehensive role-based access control system that provides granular permission management across all modules. This system replaces the previous simple role checking with a robust, scalable permission framework.

## Key Features

### 1. **Centralized Permission Management**
- All permissions are defined in `accounts/permissions.py`
- Role-based access control with inheritance
- Module-specific permission categories
- Context-aware permission checking

### 2. **Predefined Roles**
- **Admin**: Full system access
- **Doctor**: Medical operations and patient care
- **Nurse**: Patient care and vitals monitoring
- **Receptionist**: Patient registration and appointments
- **Pharmacist**: Medication management and dispensing
- **Lab Technician**: Laboratory operations
- **Accountant**: Financial management
- **Health Record Officer**: Medical records management
- **Radiology Staff**: Imaging services

### 3. **Permission Categories**
- Patient Management (view, create, edit, delete, toggle_status, wallet_manage, nhia_manage)
- Medical Records (view, create, edit, delete)
- Consultations (view, create, edit)
- Referrals (view, create, edit)
- Pharmacy (view, create, edit, dispense)
- Laboratory (view, create, edit, results)
- Billing (view, create, edit, process_payment)
- Wallet (view, create, edit, transactions)
- Appointments (view, create, edit)
- Inpatient (view, create, edit, discharge)
- User Management (view, create, edit, delete)
- Reports (view, generate)

## Usage

### 1. **View-Level Permissions**

#### Using Decorators
```python
from accounts.permissions import permission_required, role_required

@login_required
@permission_required('patients.view')
def patient_list(request):
    # View logic here
    pass

@role_required(['admin', 'doctor'])
def medical_records_view(request):
    # Only admins and doctors can access this
    pass
```

#### Permission Checks in Views
```python
from accounts.permissions import user_has_permission, user_in_role

def some_view(request):
    if not user_has_permission(request.user, 'patients.edit'):
        return HttpResponseForbidden("You don't have permission")
    
    if user_in_role(request.user, 'admin'):
        # Admin-specific logic
        pass
```

### 2. **Template-Level Permissions**

#### Using Template Tags
```html
{% load permission_tags %}

<!-- Check single permission -->
{% if user|has_permission:'patients.view' %}
    <a href="{% url 'patients:list' %}">View Patients</a>
{% endif %}

<!-- Check role -->
{% if user|in_role:'admin,doctor' %}
    <button class="btn btn-primary">Edit Patient</button>
{% endif %}

<!-- Check multiple permissions -->
{% if user|has_any_permission:'patients.create,patients.edit' %}
    <a href="{% url 'patients:create' %}">Add Patient</a>
{% endif %}

<!-- Module access check -->
{% if user|has_module_access:'pharmacy' %}
    <a href="{% url 'pharmacy:dashboard' %}">Pharmacy</a>
{% endif %}
```

#### Using Context Variables
```html
<!-- Permissions are automatically available in templates via context processors -->
{% if user_can_manage_patients %}
    <div class="patient-management-section">
        <!-- Patient management interface -->
    </div>
{% endif %}

{% if user_has_medical_roles %}
    <div class="medical-section">
        <!-- Medical interface -->
    </div>
{% endif %}
```

### 3. **Permission Categories in Templates**
```html
<!-- Check action permissions -->
{% if user|can_view:'patient' %}
    <a href="#">View Patient</a>
{% endif %}

{% if user|can_edit:'patient' %}
    <a href="#">Edit Patient</a>
{% endif %}

{% if user|can_create:'prescription' %}
    <a href="#">Create Prescription</a>
{% endif %}

{% if user|can_process:'payment' %}
    <a href="#">Process Payment</a>
{% endif %}
```

### 4. **API Permission Checks**
```python
from accounts.permissions import can_perform_action

def api_view(request):
    if not can_perform_action(request.user, 'create_consultation'):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # API logic here
    pass
```

## Implementation Examples

### 1. **Patient Detail Template with Permissions**
```html
<!-- Only show edit button to authorized users -->
{% if user|has_permission:'patients.edit' %}
    <a href="{% url 'patients:edit' patient.id %}" class="btn btn-primary">
        Edit Patient
    </a>
{% endif %}

<!-- Only show medical records to medical staff -->
{% if user|has_permission:'medical.view' %}
    <div class="medical-records">
        <!-- Medical records content -->
    </div>
{% endif %}

<!-- Only show billing to finance staff -->
{% if user|has_permission:'billing.view' %}
    <div class="billing-section">
        <!-- Billing content -->
    </div>
{% endif %}
```

### 2. **View with Multiple Permission Checks**
```python
@login_required
@permission_required('patients.view')
def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Check specific permissions for different actions
    context = {
        'patient': patient,
        'can_edit': user_has_permission(request.user, 'patients.edit'),
        'can_delete': user_has_permission(request.user, 'patients.delete'),
        'can_manage_wallet': user_has_permission(request.user, 'patients.wallet_manage'),
        'can_manage_nhia': user_has_permission(request.user, 'patients.nhia_manage'),
        'is_medical_staff': user_in_role(request.user, ['doctor', 'nurse']),
        'is_admin': user_in_role(request.user, 'admin'),
    }
    
    return render(request, 'patients/patient_detail.html', context)
```

### 3. **Role-Based Navigation**
```html
<!-- Navigation menu with role-based items -->
<ul class="navbar-nav">
    {% if user|has_module_access:'patients' %}
        <li class="nav-item">
            <a class="nav-link" href="{% url 'patients:list' %}">Patients</a>
        </li>
    {% endif %}
    
    {% if user|has_module_access:'pharmacy' %}
        <li class="nav-item">
            <a class="nav-link" href="{% url 'pharmacy:dashboard' %}">Pharmacy</a>
        </li>
    {% endif %}
    
    {% if user|has_module_access:'billing' %}
        <li class="nav-item">
            <a class="nav-link" href="{% url 'billing:dashboard' %}">Billing</a>
        </li>
    {% endif %}
</ul>
```

## Setting Up Default Roles

Run the management command to set up default roles:

```bash
python manage.py setup_hms_roles
```

This creates all predefined roles with their descriptions.

## Migration Guide

### 1. **Updating Existing Views**
Replace old role checking with new permission decorators:
```python
# Old way
@login_required
def some_view(request):
    if not (request.user.is_superuser or request.user.profile.role == 'admin'):
        return HttpResponseForbidden()
    # View logic

# New way
@login_required
@permission_required('some.permission')
def some_view(request):
    # View logic
```

### 2. **Updating Templates**
Replace hardcoded role checks with permission tags:
```html
<!-- Old way -->
{% if user.is_superuser or user.profile.role == 'admin' %}
    <button>Edit</button>
{% endif %}

<!-- New way -->
{% if user|has_permission:'patients.edit' %}
    <button>Edit</button>
{% endif %}
```

### 3. **Adding Context Processors**
Ensure `core/context_processors.py` is included in `TEMPLATES` setting:
```python
'context_processors': [
    # ... other processors
    'core.context_processors.hms_permissions',
    'core.context_processors.hms_user_roles',
]
```

## Security Features

### 1. **Superuser Override**
Superusers automatically have all permissions.

### 2. **Permission Inheritance**
Roles can inherit permissions from parent roles.

### 3. **Context-Aware Checking**
Advanced permission checking considers the context of actions.

### 4. **Audit Trail**
All permission checks and role assignments are logged.

## Troubleshooting

### 1. **Permission Denied Errors**
- Check if user has the required role
- Verify permission is defined in `ROLE_PERMISSIONS`
- Ensure user is logged in

### 2. **Template Tag Errors**
- Make sure `permission_tags` is loaded
- Check template syntax
- Verify context processors are configured

### 3. **View Access Issues**
- Ensure decorators are properly applied
- Check view import statements
- Verify URL patterns

## Best Practices

### 1. **Granular Permissions**
Use specific permissions rather than broad role checks:
```python
# Good
@permission_required('patients.edit')

# Less specific
@role_required('admin')
```

### 2. **Consistent Naming**
Follow the `module.action` pattern for permissions:
```python
'patients.view', 'patients.create', 'patients.edit', 'patients.delete'
```

### 3. **Template Organization**
Use context variables for complex permission logic:
```html
{% if user_can_manage_patients %}
    <!-- Complex patient management interface -->
{% endif %}
```

### 4. **Error Handling**
Provide clear error messages for permission denied scenarios:
```python
if not user_has_permission(request.user, 'some.permission'):
    messages.error(request, "You don't have permission to perform this action.")
    return redirect('some.url')
```

## Future Enhancements

1. **Dynamic Role Management**: Web interface for creating/modifying roles
2. **Permission Groups**: Organize permissions into logical groups
3. **Audit Logging**: Track all permission checks and access attempts
4. **API Permissions**: REST API-specific permission handling
5. **Department-Based Access**: Additional layer of access control by department

This comprehensive RBAC system provides robust, scalable permission management while maintaining backward compatibility and ease of use.
