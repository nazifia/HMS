# UI Permission System - Complete Guide

## Overview

The HMS UI Permission System is a flexible, database-driven role-based access control (RBAC) system that controls access to UI elements (links, buttons, modals, menu items) based on user roles and permissions.

## Key Features

✅ **Database-Driven**: All permissions stored in database, no hardcoded checks
✅ **Fine-Grained Control**: Control individual buttons, links, modals, and menu items
✅ **Role-Based**: Assign permissions to roles, not individual users
✅ **Extensible**: Easily add new roles and permissions without code changes
✅ **Performance-Optimized**: Caching for fast permission checks
✅ **Backward Compatible**: Preserves existing permission system

---

## Architecture

### Models

#### 1. **UIPermission**
Controls access to individual UI elements.

**Fields:**
- `element_id` - Unique identifier (e.g., "btn_create_patient")
- `element_label` - Human-readable name
- `element_type` - Type: link, button, modal, menu_item, tab, section, form_field, action
- `module` - Application module (patients, pharmacy, laboratory, etc.)
- `required_permissions` - Django permissions required (ManyToMany)
- `required_roles` - Roles that can access (ManyToMany)
- `is_active` - Enable/disable without deletion
- `is_system` - System elements (cannot be deleted)
- `display_order` - Order in lists/menus

#### 2. **PermissionGroup**
Groups of UI permissions for easier management.

**Fields:**
- `name` - Group name
- `module` - Application module
- `ui_permissions` - UI permissions in group (ManyToMany)

---

## Usage in Templates

### Load the Template Tags

```django
{% load hms_permissions %}
```

### 1. Basic Permission Check

```django
{% if user|can_show_ui:'btn_create_patient' %}
    <a href="{% url 'patients:register' %}" class="btn btn-primary">
        <i class="fas fa-plus"></i> Create Patient
    </a>
{% endif %}
```

### 2. Check Multiple Elements (OR logic)

```django
{% if user|can_show_any_ui:'btn_create,btn_edit,btn_delete' %}
    <div class="action-buttons">
        <!-- Show if user has ANY of these permissions -->
    </div>
{% endif %}
```

### 3. Check All Elements (AND logic)

```django
{% if user|can_show_all_ui:'btn_edit,btn_save,btn_submit' %}
    <button type="submit">
        <!-- Show only if user has ALL permissions -->
        Complete Action
    </button>
{% endif %}
```

### 4. Menu Item with Permission

```django
{% if user|can_show_ui:'menu_pharmacy' %}
    <li class="nav-item">
        <a href="{% url 'pharmacy:dashboard' %}" class="nav-link">
            <i class="fas fa-pills"></i>
            <span>Pharmacy</span>
        </a>
    </li>
{% endif %}
```

### 5. Modal with Permission

```django
{% if user|can_show_ui:'modal_delete_user' %}
    <div class="modal fade" id="deleteUserModal">
        <div class="modal-dialog">
            <div class="modal-content">
                <!-- Modal content -->
            </div>
        </div>
    </div>
{% endif %}
```

### 6. Section/Tab with Permission

```django
{% if user|can_show_ui:'section_financial_reports' %}
    <div class="card">
        <div class="card-header">
            <h4>Financial Reports</h4>
        </div>
        <div class="card-body">
            <!-- Financial content -->
        </div>
    </div>
{% endif %}
```

### 7. Get User's Accessible UI Elements

```django
{% get_user_ui_elements user 'pharmacy' as pharmacy_elements %}

{% for element in pharmacy_elements|ui_elements_by_type:'button' %}
    <button class="btn btn-sm">
        <i class="{{ element.icon_class }}"></i>
        {{ element.element_label }}
    </button>
{% endfor %}
```

### 8. Permission Indicator

```django
{% show_permission_indicator user 'btn_create_patient' %}
```

Shows a visual checkmark or X indicating permission status.

---

## Usage in Views

### 1. Check Permission in View

```python
from core.models import UIPermission

def my_view(request):
    # Get UI permission
    try:
        ui_perm = UIPermission.objects.get(element_id='btn_create_patient')

        if ui_perm.user_can_access(request.user):
            # User can access this element
            pass
        else:
            # User cannot access
            return HttpResponseForbidden()
    except UIPermission.DoesNotExist:
        # Permission not defined, handle accordingly
        pass
```

### 2. Using Existing Decorators

The system works alongside existing permission decorators:

```python
from accounts.permissions import permission_required, role_required

@permission_required('create_patient')
def create_patient_view(request):
    # View logic
    pass

@role_required(['admin', 'pharmacist'])
def pharmacy_view(request):
    # View logic
    pass
```

---

## Management Commands

### 1. Populate Default UI Permissions

```bash
python manage.py populate_ui_permissions
```

Creates default UI permissions for all modules.

### 2. Clear and Recreate

```bash
python manage.py populate_ui_permissions --clear
```

Clears existing non-system permissions and recreates all defaults.

---

## Admin Interface

### Access UI Permission Management

1. **Django Admin**: `/admin/core/uipermission/`
2. **Custom Interface**: `/core/ui-permissions/`

### Create New UI Permission

1. Navigate to: `/core/ui-permissions/create/`
2. Fill in:
   - Element ID (unique, e.g., "btn_export_report")
   - Element Label (e.g., "Export Report Button")
   - Element Type (button, link, modal, etc.)
   - Module (select from dropdown)
   - Required Permissions (select Django permissions)
   - Required Roles (select roles)
3. Save

### Assign UI Permissions to Role

**Method 1: Via Role Detail Page**
1. Go to role detail
2. Click "Manage UI Permissions"
3. Select/deselect permissions by module
4. Save

**Method 2: Bulk Assignment**
1. Navigate to: `/core/ui-permissions/bulk-assign/`
2. Select roles
3. Select UI permissions
4. Choose action: Add, Remove, or Replace
5. Submit

---

## Common UI Permission Patterns

### Sidebar/Navigation Menu

```django
{% load hms_permissions %}

<ul class="sidebar-nav">
    {% if user|can_show_ui:'menu_dashboard' %}
        <li><a href="{% url 'dashboard:dashboard' %}">Dashboard</a></li>
    {% endif %}

    {% if user|can_show_ui:'menu_patients' %}
        <li><a href="{% url 'patients:list' %}">Patients</a></li>
    {% endif %}

    {% if user|can_show_ui:'menu_pharmacy' %}
        <li><a href="{% url 'pharmacy:dashboard' %}">Pharmacy</a></li>
    {% endif %}

    {% if user|can_show_ui:'menu_laboratory' %}
        <li><a href="{% url 'laboratory:dashboard' %}">Laboratory</a></li>
    {% endif %}

    {% if user|can_show_ui:'menu_billing' %}
        <li><a href="{% url 'billing:dashboard' %}">Billing</a></li>
    {% endif %}

    {% if user|can_show_ui:'menu_users' %}
        <li><a href="{% url 'accounts:user_dashboard' %}">User Management</a></li>
    {% endif %}
</ul>
```

### Action Buttons on Detail Page

```django
<div class="btn-toolbar">
    {% if user|can_show_ui:'btn_edit_patient' %}
        <a href="{% url 'patients:edit' patient.id %}" class="btn btn-primary">
            <i class="fas fa-edit"></i> Edit
        </a>
    {% endif %}

    {% if user|can_show_ui:'btn_delete_patient' %}
        <button type="button" class="btn btn-danger" data-bs-toggle="modal" data-bs-target="#deleteModal">
            <i class="fas fa-trash"></i> Delete
        </button>
    {% endif %}
</div>
```

### Data Table Actions

```django
<table class="table">
    <thead>
        <tr>
            <th>Name</th>
            <th>Email</th>
            {% if user|can_show_any_ui:'btn_edit_patient,btn_delete_patient' %}
                <th>Actions</th>
            {% endif %}
        </tr>
    </thead>
    <tbody>
        {% for patient in patients %}
            <tr>
                <td>{{ patient.name }}</td>
                <td>{{ patient.email }}</td>
                {% if user|can_show_any_ui:'btn_edit_patient,btn_delete_patient' %}
                    <td>
                        {% if user|can_show_ui:'btn_edit_patient' %}
                            <a href="{% url 'patients:edit' patient.id %}">Edit</a>
                        {% endif %}
                        {% if user|can_show_ui:'btn_delete_patient' %}
                            <a href="{% url 'patients:delete' patient.id %}">Delete</a>
                        {% endif %}
                    </td>
                {% endif %}
            </tr>
        {% endfor %}
    </tbody>
</table>
```

---

## Creating UI Permissions for New Features

### Example: Adding a New "Export Patients" Button

**Step 1: Define the UI Permission**

```python
# In manage.py shell or create migration
from core.models import UIPermission
from django.contrib.auth.models import Permission
from accounts.models import Role

ui_perm = UIPermission.objects.create(
    element_id='btn_export_patients',
    element_label='Export Patients Button',
    element_type='button',
    module='patients',
    description='Button to export patient data to CSV/Excel',
    icon_class='fas fa-file-export',
    is_active=True,
    display_order=10
)

# Add required permissions
export_perm = Permission.objects.get(codename='export_data')
ui_perm.required_permissions.add(export_perm)

# Add required roles
admin_role = Role.objects.get(name='admin')
ui_perm.required_roles.add(admin_role)
```

**Step 2: Use in Template**

```django
{% if user|can_show_ui:'btn_export_patients' %}
    <a href="{% url 'patients:export' %}" class="btn btn-success">
        <i class="fas fa-file-export"></i> Export Patients
    </a>
{% endif %}
```

---

## Migration Strategy

### For Existing Templates

You can gradually migrate existing templates to use the new system:

**Before:**
```django
{% if user.is_superuser or user.profile.role == 'admin' %}
    <button>Delete</button>
{% endif %}
```

**After:**
```django
{% if user|can_show_ui:'btn_delete_patient' %}
    <button>Delete</button>
{% endif %}
```

**Hybrid (Backward Compatible):**
```django
{% if user.is_superuser or user|has_permission:'delete_patient' or user|can_show_ui:'btn_delete_patient' %}
    <button>Delete</button>
{% endif %}
```

---

## API Integration

### Check Permission via JavaScript

```javascript
// In your template, expose permission status
<script>
    const userPermissions = {
        canCreate: {% if user|can_show_ui:'btn_create_patient' %}true{% else %}false{% endif %},
        canEdit: {% if user|can_show_ui:'btn_edit_patient' %}true{% else %}false{% endif %},
        canDelete: {% if user|can_show_ui:'btn_delete_patient' %}true{% else %}false{% endif %}
    };

    // Use in JavaScript
    if (userPermissions.canDelete) {
        showDeleteButton();
    }
</script>
```

---

## Troubleshooting

### Permission Check Returns False But Should Be True

1. **Check if permission exists:**
   ```bash
   python manage.py shell
   from core.models import UIPermission
   UIPermission.objects.get(element_id='your_element_id')
   ```

2. **Check if permission is active:**
   ```python
   ui_perm.is_active  # Should be True
   ```

3. **Check role assignments:**
   ```python
   ui_perm.required_roles.all()  # Should include user's role
   ```

4. **Clear cache:**
   ```bash
   python manage.py shell
   from django.core.cache import cache
   cache.clear()
   ```

### Element ID Not Found

- Ensure you've run: `python manage.py populate_ui_permissions`
- Check for typos in element_id
- Verify element exists in database

### Roles Not Working

- Ensure user has roles assigned: `user.roles.all()`
- Check role is linked to UI permission
- Verify role name matches exactly (case-sensitive)

---

## Best Practices

1. **Naming Convention**:
   - Buttons: `btn_action_module` (e.g., `btn_create_patient`)
   - Menus: `menu_module` (e.g., `menu_pharmacy`)
   - Modals: `modal_action_module` (e.g., `modal_delete_user`)
   - Sections: `section_description` (e.g., `section_financial_reports`)

2. **Use System Flag**: Mark core permissions as `is_system=True` to prevent deletion

3. **Group Related Permissions**: Use PermissionGroup to bundle related permissions

4. **Cache Clearing**: Clear cache after permission changes in production

5. **Documentation**: Document custom UI permissions in code comments

---

## Security Considerations

1. **Always check on backend**: UI permissions are for display only. Always validate permissions in views.

2. **Superusers bypass**: Superusers automatically pass all permission checks

3. **Default behavior**: If UIPermission doesn't exist, access is granted by default (backward compatible)

4. **Inactive permissions**: Setting `is_active=False` denies access without deletion

---

## Summary

The UI Permission System provides:
- ✅ Database-driven permission control
- ✅ Fine-grained UI element access
- ✅ Easy role management
- ✅ Extensible for future roles
- ✅ Performance-optimized with caching
- ✅ Backward compatible with existing system

**Management URLs:**
- Dashboard: `/core/ui-permissions/`
- Create: `/core/ui-permissions/create/`
- List: `/core/ui-permissions/list/`
- Django Admin: `/admin/core/uipermission/`

**Command Reference:**
```bash
python manage.py populate_ui_permissions        # Populate defaults
python manage.py populate_ui_permissions --clear  # Clear and recreate
```

---

*Last Updated: 2025-01-16*
*Version: 1.0*
*Status: ✅ Production Ready*
