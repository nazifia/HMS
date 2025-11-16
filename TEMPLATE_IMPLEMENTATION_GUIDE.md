# UI Permission System - Template Implementation Guide

## Overview

All template implementations for the UI Permission Management system have been created. This guide provides an overview of all templates and how to use them.

---

## Templates Created

### 1. **Dashboard** (`templates/core/ui_permission_dashboard.html`)

**URL**: `/core/ui-permissions/`

**Purpose**: Main dashboard showing statistics and overview of UI permissions

**Features**:
- Total, active, and inactive permission counts
- Permissions grouped by module
- Permissions grouped by type
- Recently created permissions
- Quick action buttons

**Usage**:
```python
# View
from core.ui_permission_views import ui_permission_dashboard

# Access
http://localhost:8000/core/ui-permissions/
```

---

### 2. **Permissions List** (`templates/core/ui_permission_list.html`)

**URL**: `/core/ui-permissions/list/`

**Purpose**: List all UI permissions with filtering and pagination

**Features**:
- Filter by module, type, and status
- Search by element ID or label
- Card-based layout showing permission details
- Quick actions (view, edit, toggle, delete)
- Pagination support
- AJAX toggle for active/inactive status

**Filters**:
- Module dropdown
- Element type dropdown
- Active/Inactive status
- Search box

**Usage**:
```django
<!-- Link to list -->
<a href="{% url 'core:ui_permission_list' %}">View All Permissions</a>

<!-- Link with filter -->
<a href="{% url 'core:ui_permission_list' %}?module=pharmacy">Pharmacy Permissions</a>
```

---

### 3. **Create/Edit Form** (`templates/core/ui_permission_form.html`)

**URLs**:
- Create: `/core/ui-permissions/create/`
- Edit: `/core/ui-permissions/<id>/edit/`

**Purpose**: Form for creating and editing UI permissions

**Features**:
- Organized into sections (Basic Info, Access Control, Configuration)
- Live preview panel showing element as you type
- Select2 for multi-select dropdowns
- Icon preview
- Usage example code generation
- Form validation
- Helpful tooltips and descriptions

**Sections**:
1. **Basic Information**
   - Element ID
   - Element Label
   - Element Type
   - Module

2. **Access Control**
   - Required Roles (multi-select)
   - Required Permissions (multi-select)

3. **Configuration**
   - Description
   - URL Pattern
   - Icon Class
   - Display Order
   - Active Status

**Preview Features**:
- Icon preview
- Element label preview
- Type and module badges
- Auto-generated usage example

**Usage**:
```django
<!-- Create new permission -->
<a href="{% url 'core:ui_permission_create' %}">Create Permission</a>

<!-- Edit existing permission -->
<a href="{% url 'core:ui_permission_edit' permission.pk %}">Edit</a>
```

---

### 4. **Permission Detail** (`templates/core/ui_permission_detail.html`)

**URL**: `/core/ui-permissions/<id>/`

**Purpose**: View full details of a single UI permission

**Features**:
- Complete permission information table
- Access control details (roles and permissions)
- Usage examples for templates and views
- Quick action sidebar
- List of roles with access
- Toggle active/inactive
- Edit and delete buttons

**Sections**:
1. **Permission Details**: All fields in a table
2. **Access Control**: Required roles and permissions
3. **Usage Examples**: Code snippets for implementation
4. **Sidebar**: Quick actions and role information

**Usage**:
```django
<a href="{% url 'core:ui_permission_detail' permission.pk %}">View Details</a>
```

---

### 5. **Delete Confirmation** (`templates/core/ui_permission_delete.html`)

**URL**: `/core/ui-permissions/<id>/delete/`

**Purpose**: Confirm deletion of a UI permission

**Features**:
- Warning alerts
- Impact summary
- Permission details display
- Confirmation form
- Cancel option

**Safety Features**:
- Shows impact of deletion
- Lists affected roles
- Requires explicit confirmation
- Cannot delete system permissions

**Usage**:
```django
<a href="{% url 'core:ui_permission_delete' permission.pk %}"
   onclick="return confirm('Are you sure?');">
    Delete
</a>
```

---

### 6. **Role UI Permissions** (`templates/core/role_ui_permissions.html`)

**URL**: `/core/roles/<role_id>/ui-permissions/`

**Purpose**: Manage all UI permissions for a specific role

**Features**:
- Permissions organized by module
- Checkboxes for each permission
- Select all / deselect all buttons
- Module sections with visual grouping
- Role information sidebar
- Current permission count

**Usage**:
```django
<a href="{% url 'core:role_ui_permissions' role.pk %}">
    Manage UI Permissions
</a>
```

**JavaScript Functions**:
- `selectAll()` - Select all checkboxes
- `deselectAll()` - Deselect all checkboxes
- Auto-count of selected permissions

---

### 7. **Permission Groups List** (`templates/core/permission_group_list.html`)

**URL**: `/core/permission-groups/`

**Purpose**: View and manage permission groups

**Features**:
- Card-based layout
- Group information (name, module, count)
- Active/inactive status
- Quick actions (view, edit)

**Usage**:
```django
<a href="{% url 'core:permission_group_list' %}">Permission Groups</a>
```

---

### 8. **Permission Group Form** (`templates/core/permission_group_form.html`)

**URL**: `/core/permission-groups/create/`

**Purpose**: Create/edit permission groups

**Features**:
- Crispy forms integration
- All group fields
- Multi-select for permissions
- Save and cancel buttons

**Usage**:
```django
<a href="{% url 'core:permission_group_create' %}">Create Group</a>
```

---

### 9. **Bulk Assign Permissions** (`templates/core/bulk_assign_permissions.html`)

**URL**: `/core/ui-permissions/bulk-assign/`

**Purpose**: Assign multiple permissions to multiple roles at once

**Features**:
- Action selection (Add/Remove/Replace)
- Multi-select roles
- Multi-select permissions
- Select all / deselect all buttons
- Help section explaining each action
- Scrollable permission list

**Actions**:
- **Add**: Add permissions to roles (keep existing)
- **Remove**: Remove permissions from roles
- **Replace**: Replace all role permissions

**Usage**:
```django
<a href="{% url 'core:bulk_assign_permissions' %}">Bulk Assign</a>
```

---

## Template Hierarchy

```
base.html
├── ui_permission_dashboard.html
├── ui_permission_list.html
├── ui_permission_form.html (create/edit)
├── ui_permission_detail.html
├── ui_permission_delete.html
├── role_ui_permissions.html
├── permission_group_list.html
├── permission_group_form.html
└── bulk_assign_permissions.html
```

---

## Common Template Patterns

### 1. **Page Header Pattern**

```django
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h1 class="h3 mb-0">
            <i class="fas fa-icon"></i>
            Page Title
        </h1>
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb mb-0">
                <li class="breadcrumb-item"><a href="...">Parent</a></li>
                <li class="breadcrumb-item active">Current</li>
            </ol>
        </nav>
    </div>
    <div>
        <!-- Action buttons -->
    </div>
</div>
```

### 2. **Card Pattern**

```django
<div class="card">
    <div class="card-header bg-white">
        <h5 class="mb-0"><i class="fas fa-icon"></i> Title</h5>
    </div>
    <div class="card-body">
        <!-- Content -->
    </div>
    <div class="card-footer bg-white">
        <!-- Actions -->
    </div>
</div>
```

### 3. **Filter Form Pattern**

```django
<div class="card filter-card mb-4">
    <div class="card-body">
        <form method="get">
            <div class="row g-3">
                <!-- Filter fields -->
            </div>
            <div class="row mt-3">
                <div class="col-12">
                    <button type="submit" class="btn btn-primary">
                        Apply Filters
                    </button>
                    <a href="..." class="btn btn-outline-secondary">
                        Clear
                    </a>
                </div>
            </div>
        </form>
    </div>
</div>
```

---

## JavaScript Features

### 1. **Toggle Active Status (AJAX)**

```javascript
function toggleActive(permissionId, currentState) {
    fetch(`/core/ui-permissions/${permissionId}/toggle-active/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': '{{ csrf_token }}',
            'X-Requested-With': 'XMLHttpRequest',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    });
}
```

### 2. **Live Preview Updates**

```javascript
function updatePreview() {
    const elementId = $('#id_element_id').val();
    const label = $('#id_element_label').val();
    // Update preview elements
    $('#elementIdPreview').text(elementId);
    $('#labelPreview').text(label);
}

$('#id_element_id, #id_element_label').on('input', updatePreview);
```

### 3. **Select All / Deselect All**

```javascript
function selectAll() {
    document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.checked = true;
    });
}

function deselectAll() {
    document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });
}
```

---

## CSS Customizations

### Custom Classes Used

```css
.stat-card - Statistics cards with hover effect
.filter-card - Filter form styling
.permission-card - Permission item cards
.element-id-badge - Code-style badges for element IDs
.form-section - Grouped form sections
.preview-box - Live preview container
.module-section - Module grouping in forms
.permission-checkbox - Styled checkboxes
```

---

## Dependencies

### Required Libraries

1. **Bootstrap 5** - UI framework
2. **FontAwesome** - Icons
3. **Select2** - Enhanced multi-select dropdowns
4. **Django Crispy Forms** - Form rendering

### CDN Links

```html
<!-- Select2 -->
<link href="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css" rel="stylesheet" />
<link href="https://cdn.jsdelivr.net/npm/select2-bootstrap-5-theme@1.3.0/dist/select2-bootstrap-5-theme.min.css" rel="stylesheet" />
<script src="https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js"></script>
```

---

## Navigation Integration

### Add to Sidebar

```django
{% load hms_permissions %}

{% if user|can_show_ui:'menu_users' %}
<li class="sidebar-item">
    <a class="sidebar-link" href="#admin-submenu" data-bs-toggle="collapse">
        <i class="fas fa-users"></i>
        <span>Administration</span>
    </a>
    <ul id="admin-submenu" class="sidebar-dropdown list-unstyled collapse">
        <li class="sidebar-item">
            <a class="sidebar-link" href="{% url 'core:ui_permission_dashboard' %}">
                <i class="fas fa-shield-alt"></i> UI Permissions
            </a>
        </li>
    </ul>
</li>
{% endif %}
```

---

## Testing Checklist

- [✅] Dashboard loads with statistics
- [✅] List page shows all permissions
- [✅] Filters work correctly
- [✅] Create form validates properly
- [✅] Edit form pre-populates data
- [✅] Live preview updates in real-time
- [✅] Detail page shows all information
- [✅] Delete confirmation works
- [✅] Role permissions page functional
- [✅] Bulk assign works for all actions
- [✅] Pagination works
- [✅] AJAX toggle works
- [✅] Select2 multi-selects work
- [✅] Responsive design works on mobile

---

## Quick Start

### 1. Access the System

```
http://localhost:8000/core/ui-permissions/
```

### 2. Create Your First Permission

1. Click "Create Permission"
2. Fill in Element ID: `btn_my_action`
3. Fill in Element Label: `My Custom Action`
4. Select Type and Module
5. Choose Required Roles
6. Save

### 3. Use in Template

```django
{% load hms_permissions %}

{% if user|can_show_ui:'btn_my_action' %}
    <button class="btn btn-primary">My Custom Action</button>
{% endif %}
```

### 4. Assign to Role

1. Go to `/core/roles/<role_id>/ui-permissions/`
2. Select permissions
3. Save

---

## Support

**All templates are ready to use!**

- Templates Location: `templates/core/`
- Views: `core/ui_permission_views.py`
- Forms: `core/ui_permission_forms.py`
- URLs: `core/urls.py`
- Models: `core/models.py`

**Documentation**:
- Complete Guide: `UI_PERMISSION_SYSTEM_GUIDE.md`
- Summary: `RBAC_UI_PERMISSIONS_SUMMARY.md`
- This Guide: `TEMPLATE_IMPLEMENTATION_GUIDE.md`

---

**Status**: ✅ All Templates Implemented and Ready
**Date**: 2025-01-16
**Version**: 1.0
