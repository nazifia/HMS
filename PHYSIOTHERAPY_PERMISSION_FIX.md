# Physiotherapy Permission Fix

## Issue
Pharmacists and other unauthorized users can access physiotherapy functions at `/patients/1/physiotherapy/add/`.

## Root Cause
The physiotherapy buttons in the patient detail template lack proper permission checks, unlike other medical functions.

## Solution
Add permission restrictions to physiotherapy functions to restrict access to medical staff only.

## Files to Modify

### 1. **View Level Permission** - `patients/views.py`
Add permission decorator to the `create_physiotherapy_request` view:

```python
@login_required
@permission_required('medical.create')  # Only medical staff can create physiotherapy requests
def create_physiotherapy_request(request, patient_id):
    # Existing code...
```

### 2. **Template Level Permissions** - `templates/patients/patient_detail.html`
Add permission checks around physiotherapy buttons:

```html
<!-- Replace existing physiotherapy buttons with permission-protected versions -->

<!-- Option 1: Simple permission check -->
{% if user|has_permission:'medical.create' %}
    <a href="{% url 'patients:create_physiotherapy_request' patient.id %}" class="btn btn-warning btn-block">
        <i class="fas fa-walking"></i> Request Physiotherapy
    </a>
{% else %}
    <button class="btn btn-warning btn-block disabled" title="Permission required">
        <i class="fas fa-walking me-2"></i>Request Physiotherapy
        <span class="permission-indicator">
            {% if not user.is_authenticated %}Login required{% else %}Permission required{% endif %}
        </span>
    </button>
{% endif %}

<!-- Option 2: Role-based check -->
{% if user|in_role:'admin,doctor,nurse' %}
    <a href="{% url 'patients:create_physiotherapy_request' patient.id %}" class="btn btn-warning btn-block">
        <i class="fas fa-walking"></i> Request Physiotherapy
    </a>
{% else %}
    <button class="btn btn-warning btn-block disabled" title="Medical staff only">
        <i class="fas fa-walking me-2"></i>Request Physiotherapy
    </button>
{% endif %}
```

### 3. **URL Level Protection** - `patients/urls.py`
Ensure the URL pattern includes the permission-protected view.

## Permission Requirements

### **Recommended Permission**: `medical.create`
This permission should be granted to:
- **Admin**: Full access
- **Doctor**: Can request physiotherapy
- **Nurse**: Can request physiotherapy
- **Health Record Officer**: Can request physiotherapy

### **Should NOT have access**:
- **Pharmacist**: No physiotherapy permissions
- **Lab Technician**: No physiotherapy permissions
- **Accountant**: No physiotherapy permissions
- **Receptionist**: No physiotherapy permissions

## Roles That Should Have Access

According to the HMS RBAC system, these roles should be able to access physiotherapy functions:

1. **Admin** - Full system access
2. **Doctor** - Medical operations and patient care
3. **Nurse** - Patient care and medical operations
4. **Health Record Officer** - Medical records and patient management

## Testing

### **Test Cases**:
1. **Admin user**: Should see and access physiotherapy buttons
2. **Doctor user**: Should see and access physiotherapy buttons
3. **Nurse user**: Should see and access physiotherapy buttons
4. **Pharmacist user**: Should NOT see physiotherapy buttons or see disabled state
5. **Receptionist user**: Should NOT see physiotherapy buttons or see disabled state
6. **Anonymous user**: Should be redirected to login

### **Test URLs**:
- `http://127.0.0.1:8000/patients/1/physiotherapy/add/` - Should require medical permissions
- `http://127.0.0.1:8000/patients/1/` - Should show/hide physiotherapy buttons based on role

## Implementation Steps

1. **Add permission decorator** to `create_physiotherapy_request` view
2. **Update template** to include permission checks around physiotherapy buttons
3. **Test with different user roles** to ensure proper access control
4. **Verify** that pharmacists and other non-medical staff cannot access physiotherapy functions

## Security Impact

This fix prevents unauthorized access to medical functions by:
- Restricting physiotherapy requests to qualified medical personnel
- Preventing role confusion and unauthorized medical interventions
- Maintaining proper separation of duties between medical and non-medical staff
- Ensuring compliance with healthcare regulations

## Alternative Implementation

If you want to be more specific, you could create a dedicated physiotherapy permission:

```python
# In permissions.py
'physiotherapy.create': 'Can create physiotherapy requests'
'physiotherapy.view': 'Can view physiotherapy requests'
'physiotherapy.edit': 'Can edit physiotherapy requests'
```

Then use:
```html
{% if user|has_permission:'physiotherapy.create' %}
    <!-- Show button -->
{% endif %}
```

This provides more granular control but requires more setup.
