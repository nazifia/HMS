# HMS Permissions System - Developer Guide

Comprehensive guide for developers working with the HMS RBAC system.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [How Permissions Flow](#how-permissions-flow)
4. [Adding New Permissions](#adding-new-permissions)
5. [Testing Permissions](#testing-permissions)
6. [Debugging](#debugging)
7. [Common Pitfalls](#common-pitfalls)
8. [Migration Notes](#migration-notes)

---

## Quick Start

### Key Files

| File | Purpose |
|------|---------|
| `accounts/permissions.py` | **Single source of truth** - PERMISSION_DEFINITIONS, ROLE_PERMISSIONS, helper functions |
| `accounts/templatetags/permission_tags.py` | Template tags for permission checks in templates |
| `accounts/context_processors.py` | Adds `user_permissions`, `user_roles` to all templates |
| `accounts/admin.py` | Enhanced admin with inline role assignment |
| `docs/ROLE_PERMISSIONS_REFERENCE.md` | Complete permission matrix reference |

### Most Used Functions

```python
# Check permissions
from accounts.permissions import user_has_permission, user_in_role

if user_has_permission(request.user, 'patients.view'):
    # Show patient data

if user_in_role(request.user, 'doctor'):
    # Doctor-specific logic

# In templates
{% load permission_tags %}
{% if user|has_permission:'patients.view' %}
    <!-- Show -->
{% endif %}
{% if user|in_role:'doctor' %}
    <!-- Doctor only -->
{% endif %}
```

---

## Architecture

### Design Principles

1. **Single Source of Truth**: All permission metadata stored in `PERMISSION_DEFINITIONS`
2. **Automatic Mapping**: Custom keys (`patients.view`) auto-convert to Django permissions (`patients.view_patient`)
3. **Role-Based**: Users assigned roles; roles have permissions
4. **Inheritance**: Roles can inherit permissions from parent roles
5. **Backward Compatibility**: Old code using `profile.role` still works via integration layer

### Data Model

```python
class Role(models.Model):
    name = models.CharField(unique=True)          # 'admin', 'doctor', etc.
    description = models.TextField()
    parent = models.ForeignKey('self', ...)       # For inheritance
    permissions = models.ManyToManyField(Permission)  # Direct permissions
    # users = M2M via CustomUser.roles

class CustomUser(AbstractUser):
    roles = models.ManyToManyField(Role, blank=True)  # NEW: Primary role assignment
    # ... other fields

class CustomUserProfile(models.Model):
    user = models.OneToOneField(CustomUser)
    role = models.CharField(choices=ROLE_CHOICES)    # LEGACY: Keep for migration
```

### Permission Flow

```
Template/View calls:
    user_has_permission(user, 'patients.view')
        ↓
Lookup in PERMISSION_DEFINITIONS['patients.view']['django_codename']
    → 'patients.view_patient'
        ↓
Convert to Django Permission object
    ↓
Check user.has_perm('patients.view_patient')
    ↓
Returns True/False
```

**Note**: `user.has_perm()` uses Django's `RolePermissionBackend` which knows about `user.roles` M2M and role inheritance.

---

## How Permissions Flow

### User Has Permission

```python
def user_has_permission(user, permission):
    if user.is_superuser:
        return True  # Superusers bypass all checks

    # Step 1: Map custom key to Django permission
    django_perm = get_django_permission(permission)  # 'patients.view' → 'patients.view_patient'

    # Step 2: Ask Django
    return user.has_perm(django_perm)  # Django checks user_permissions + groups + RolePermissionBackend
```

**RolePermissionBackend**: Custom Django auth backend that:
- Collects all user's roles (including inherited via parent roles)
- Gets all permissions from those roles (including parent role permissions)
- Returns union of all permissions

### User Roles

```python
def get_user_roles(user):
    roles = []

    # Direct M2M roles
    for role in user.roles.all():
        roles.append(role.name)
        # Add parent chain
        parent = role.parent
        while parent:
            roles.append(parent.name)
            parent = parent.parent

    # Legacy profile.role (if still set)
    if user.profile.role:
        roles.append(user.profile.role)

    return list(set(roles))  # Deduplicate
```

---

## Adding New Permissions

### Step 1: Add to PERMISSION_DEFINITIONS

`accounts/permissions.py`:

```python
PERMISSION_DEFINITIONS = {
    # ... existing ...

    'your.permission_key': {
        'django_codename': 'your_app.your_action',
        'category': 'your_category',
        'description': 'Human-readable description',
        'model': 'YourModel',
        'is_custom': True,  # False for standard Django perms
    },
}
```

### Step 2: Create Django Permission

**Option A: In Model Meta** (recommended)

```python
class YourModel(models.Model):
    # fields...

    class Meta:
        permissions = [
            ('your_action', 'Can perform specific action'),
        ]
```

**Option B: Data Migration**

```python
# migrations/000X_add_permission.py
from django.db import migrations
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

def add_permission(apps, schema_editor):
    content_type = ContentType.objects.get_for_model(YourModel)
    Permission.objects.get_or_create(
        codename='your_action',
        content_type=content_type,
        defaults={'name': 'Can perform specific action'}
    )

class Migration(migrations.Migration):
    dependencies = [...]
    operations = [migrations.RunPython(add_permission)]
```

### Step 3: Assign to Role

In `ROLE_PERMISSIONS` dict:

```python
ROLE_PERMISSIONS = {
    'doctor': {
        'permissions': [
            # ... existing ...
            'your.permission.key',
        ]
    },
}
```

### Step 4: Sync to Database

```bash
python manage.py sync_role_permissions --fix
```

Or assign via admin at `/admin/accounts/role/`.

---

## Testing Permissions

### Unit Test Template

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.models import Role
from accounts.permissions import user_has_permission, user_in_role

User = get_user_model()

class PermissionTest(TestCase):
    def setUp(self):
        # Create role
        self.doctor_role = Role.objects.create(name='doctor')

        # Create user with role
        self.user = User.objects.create_user(
            username='doctor1',
            phone_number='+1234567890',
            password='testpass'
        )
        self.user.roles.add(self.doctor_role)

    def test_permission(self):
        # Create permission (or use existing)
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from patients.models import Patient

        ct = ContentType.objects.get_for_model(Patient)
        perm = Permission.objects.get(
            content_type=ct,
            codename='view_patient'
        )
        self.doctor_role.permissions.add(perm)

        # Test
        self.assertTrue(user_has_permission(self.user, 'patients.view'))
        self.assertTrue(user_in_role(self.user, 'doctor'))
```

### Test New Permission

```bash
python manage.py test accounts.tests.test_permissions
```

Or run all tests:
```bash
python manage.py test accounts
```

---

## Debugging

### Enable Debug Logging

`settings.py`:

```python
# accounts/permissions.py
DEBUG_PERMISSIONS = True  # Set in settings or file
```

Then check logs:
```bash
python manage.py runserver
# Check console for:
# Permission GRANTED: patients.view -> patients.view_patient for user ...
# Permission DENIED: ...
```

### Inspect User's Permissions

```python
from django.contrib.auth.models import Permission
from accounts.permissions import get_user_roles, ROLE_PERMISSIONS

user = User.objects.get(username='...')

# 1. What roles does Django think user has?
print('User roles:', get_user_roles(user))

# 2. What Django permissions are directly assigned?
direct_perms = user.user_permissions.all()
print('Direct perms:', [f'{p.content_type.app_label}.{p.codename}' for p in direct_perms])

# 3. What permissions from roles?
roles = user.roles.all()
role_perms = set()
for role in roles:
    role_perms.update(role.permissions.all())
print('Role perms:', [f'{p.content_type.app_label}.{p.codename}' for p in role_perms])

# 4. All permissions (effective):
all_perms = set()
for perm in user.get_all_permissions():
    all_perms.add(perm)
print('Effective perms:', len(all_perms))
```

### Validate Definitions

```bash
python manage.py validate_permissions
```

Shows:
- Missing Django permissions
- Circular role references
- Users without roles
- Legacy `profile.role` usage

### Check Template Context

```python
from django.test import RequestFactory
from accounts.context_processors import user_permissions

request = RequestFactory().get('/')
request.user = user
ctx = user_permissions(request)
print(ctx['user_roles'])
print(list(ctx['user_permissions'].keys()))
```

---

## Common Pitfalls

### 1. Permission Key Not Found in PERMISSION_DEFINITIONS

**Symptom**: `user_has_permission(user, 'foo.bar')` returns False even though user has Django permission.

**Cause**: Custom key `'foo.bar'` not in `PERMISSION_DEFINITIONS`, so mapping fails.

**Fix**: Add to `PERMISSION_DEFINITIONS` in `permissions.py`

---

### 2. Using Django Permission String Directly

**Bad**:
```python
@permission_required('patients.view_patient')  # Django format
```

**Good**:
```python
@permission_required('patients.view')  # Custom key from PERMISSION_DEFINITIONS
```

**Why**: Custom keys provide:
- Stability (Django string may change)
- Metadata lookup
- Category grouping

---

### 3. Forgetting to Create Django Permission

**Symptom**: `sync_role_permissions` shows "missing permissions"

**Cause**: Django permission record not created in `auth_permission` table.

**Fix**: Add to model `Meta.permissions` and run migrations.

---

### 4. Hardcoding Role Checks

**Bad**:
```python
if user.profile.role == 'doctor':  # Only works for single role!
    ...
```

**Good**:
```python
from accounts.permissions import user_in_role
if user_in_role(user, 'doctor'):
    ...
```

**Why**: New system supports multiple roles and inheritance. `user.profile.role` is legacy and deprecated.

---

### 5. Not Syncing After Definition Updates

**Symptom**: Added permission to `ROLE_PERMISSIONS` but it's not available to users.

**Cause**: Role's `permissions` M2M not updated in database.

**Fix**: Run `python manage.py sync_role_permissions --fix`

---

### 6. Template Filter vs Tag

**Bad**:
```django
{% if user|has_permission:'patients.view' %}  {# Works but inefficient #}
```

**Good** (simple tags are more flexible):
```django
{% has_permission user 'patients.view' as can_view %}
{% if can_view %}
{% endif %}
```

---

## Migration Notes

### From `profile.role` to `user.roles`

**Old**:
```python
if user.profile.role == 'doctor':
    # ...
```

**New**:
```python
from accounts.permissions import user_in_role
if user_in_role(user, 'doctor'):
    # ...
```

Or in templates:
```django
{% if user|in_role:'doctor' %}
```

### From `role_tags.lookup` to `permission_tags`

**Old**:
```django
{% load role_tags %}
{% if permission in user_permissions|lookup:user_roles %}
```

**New**:
```django
{% load permission_tags %}
{% if user|has_permission:permission %}
```

---

## Reference

### PERMISSION_DEFINITIONS Structure

```python
{
    'custom.key': {                     # Your stable identifier
        'django_codename': 'app.codename',  # What Django expects
        'category': 'category_name',         # For grouping
        'description': 'Human string',       # For UI/docs
        'model': 'ModelName',                # Associated model
        'is_custom': True/False              # Custom vs standard
    }
}
```

### Creating Standard Django Permissions

Django auto-creates these for each model:
- `add_modelname`
- `change_modelname`
- `delete_modelname`
- `view_modelname` (Django 2.1+)

So for `Patient`:
```python
# PERMISSION_DEFINITIONS entry:
'patients.view': {
    'django_codename': 'patients.view_patient',  # view_ + lowercased model name
    ...
}

# Django will create 'view_patient' permission automatically
# Or define explicitly in Patient model Meta:
class Patient(models.Model):
    class Meta:
        permissions = [
            ('view_patient', 'Can view patient'),  # Already exists by default
        ]
```

---

## Performance Tips

### Caching

`get_user_roles()` and role permission inheritance can be expensive. Consider:

```python
# Prefetch in views
users = CustomUser.objects.prefetch_related(
    'roles',
    'roles__permissions',
    'roles__parent',
    'roles__parent__permissions',
).all()

for user in users:
    roles = get_user_roles(user)  # Uses prefetched data efficiently
```

### Template Context

The `user_permissions` context processor builds a dict on each request. If you need heavy optimization:

- Cache `get_user_roles()` result per request (done automatically)
- Use per-view caching for permission-heavy pages
- Consider `django.contrib.auth.context_processors.auth` for basic `user` object only

---

## Testing Checklist

When adding new permission:

- [ ] Added to `PERMISSION_DEFINITIONS`
- [ ] Django Permission exists (check with `python manage.py showmigrations`)
- [ ] Assign in `ROLE_PERMISSIONS` for appropriate roles
- [ ] Run `python manage.py sync_role_permissions --fix`
- [ ] Run `python manage.py validate_permissions` (should pass)
- [ ] Write unit tests
- [ ] Update `docs/ROLE_PERMISSIONS_REFERENCE.md` matrix
- [ ] Verify in admin interface (role edit page shows permission)

---

## Support

- **Reference**: `docs/ROLE_PERMISSIONS_REFERENCE.md`
- **Migration**: `docs/PERMISSION_MIGRATION_GUIDE.md`
- **CLAUDE.md**: Project-wide development guide
- **Code**: `accounts/permissions.py` - read the source!

---

**Version**: 2.0
**Last Updated**: 2025-02-08
