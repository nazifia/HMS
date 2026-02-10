# Manual Testing Guide for Permission Fix

## Test 1: Verify Permission Assignment via Web Interface

### Step 1: Open the Role Edit Page
1. Navigate to: http://127.0.0.1:8000/accounts/roles/167/edit/
2. Log in if required

### Step 2: Modify Permissions
1. Select or deselect some permissions using the checkboxes
2. Click "Save"

### Step 3: Check the Logs
Look at the server console output. You should see messages like:
```
[Role Edit] Updating role 'Doctor' (ID: 167)
[Role Edit] Old permissions: ['view_patient', 'add_consultation']
[Role Edit] Form cleaned_data permissions: ['view_patient', 'add_consultation', 'view_medication']
[Role Edit] New permissions after save: ['view_patient', 'add_consultation', 'view_medication']
[Role Edit] Cleared permission cache for 5 users with role 'Doctor'
[Signal] Role permissions changed for 'Doctor' - action: post_add
[Signal] Cleared permission cache for 5 users with role 'Doctor'
```

### Step 4: Verify Immediate Effect
1. Without logging out, navigate to a page that requires the new permission
2. The user should immediately have access (or be denied if permission was removed)

## Test 2: Test via Django Shell

```bash
python manage.py shell
```

```python
from accounts.models import CustomUser, Role
from django.contrib.auth.models import Permission

# Get a user with role 167
user = CustomUser.objects.filter(roles__id=167).first()
role = Role.objects.get(id=167)

# Check current permissions
print("Current permissions:", user.has_perm('patients.view_patient'))

# Modify role permissions via admin
role.permissions.add(Permission.objects.get(codename='view_patient', content_type__app_label='patients'))

# Reload user to simulate new request
user = CustomUser.objects.get(id=user.id)

# Check again - should reflect immediately
print("After update:", user.has_perm('patients.view_patient'))
```

## Test 3: Use the Automated Test Script

```bash
python test_permissions_fix.py
```

This will run 5 comprehensive tests to verify permission cache invalidation works correctly.
