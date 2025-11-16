# Server Restart Required - Theatre Menu Fix

## Issue
Theatre link is missing from sidebar.

## Root Cause
All the changes we made (middleware, cache, permissions) require a **server restart** to take effect.

---

## **SOLUTION: RESTART THE SERVER**

### Step 1: Stop the Current Server

Press `Ctrl + C` in the terminal where Django is running.

### Step 2: Clear All Caches (Important!)

```bash
python manage.py clear_permission_cache
```

### Step 3: Restart the Server

```bash
python manage.py runserver
```

### Step 4: Clear Browser Cache

In your browser:
- **Hard refresh**: `Ctrl + F5` (Windows) or `Cmd + Shift + R` (Mac)
- **Or**: Open in incognito/private window

---

## What Should Happen After Restart

### For Admin/Doctor/Nurse Users:
✅ Theatre menu should appear in sidebar
✅ Can access all theatre features

### For Pharmacist/Accountant/Other Users:
❌ Theatre menu should NOT appear (hidden)
❌ Cannot access theatre URLs

---

## Verification Steps

### 1. Check Theatre Menu Appears

**Login as admin, doctor, or nurse:**
- Look for "Theatre" menu item in sidebar
- Should have icon: 🏥 (hospital-symbol)
- Should expand to show submenu

**Submenu items:**
- Dashboard
- Surgeries
- Operation Theatres
- Surgery Types
- Surgical Teams
- Equipment
- Equipment Maintenance
- Surgery Packs
- Order Surgery Pack
- Surgery Report

### 2. Test Permission System

**Test matrix:**

| User Role | Should See Theatre Menu | Can Access Theatre URLs |
|-----------|------------------------|------------------------|
| Admin | ✅ Yes | ✅ Yes |
| Doctor | ✅ Yes | ✅ Yes |
| Nurse | ✅ Yes | ✅ Yes |
| Pharmacist | ❌ No | ❌ No |
| Accountant | ❌ No | ❌ No |
| Receptionist | ❌ No | ❌ No |
| Lab Technician | ❌ No | ❌ No |

---

## Current Theatre Permission Status

```
Permission: menu_theatre
Status: ✅ Active
Required Roles: admin, doctor, nurse
Type: Menu
Module: theatre
```

---

## Troubleshooting

### Issue: Theatre still not showing after restart

**Solution 1**: Clear Django cache
```bash
python manage.py shell -c "from django.core.cache import cache; cache.clear()"
```

**Solution 2**: Clear browser completely
- Close all browser windows
- Reopen browser
- Try incognito/private window

**Solution 3**: Check user has correct role
```bash
python manage.py shell -c "
from accounts.models import CustomUser
user = CustomUser.objects.get(username='YOUR_USERNAME')
print(f'Roles: {[r.name for r in user.roles.all()]}')
"
```

**Solution 4**: Verify permission is active
```bash
python manage.py shell -c "
from core.models import UIPermission
theatre = UIPermission.objects.get(element_id='menu_theatre')
print(f'Active: {theatre.is_active}')
print(f'Roles: {[r.name for r in theatre.required_roles.all()]}')
"
```

### Issue: Theatre menu shows but clicking gives error

**Check if theatre app URLs are configured:**
```bash
python manage.py shell -c "
from django.urls import reverse
try:
    print(reverse('theatre:dashboard'))
    print('✅ Theatre URLs are configured')
except:
    print('❌ Theatre URLs not configured')
"
```

---

## Why Restart is Required

### Changes that need restart:

1. **Middleware** (`pharmacy.middleware.PharmacyAccessMiddleware`)
   - Added to `MIDDLEWARE` in settings.py
   - Only loads when Django starts

2. **Cache Backend** (DatabaseCache)
   - Changed from LocMemCache to DatabaseCache
   - Requires restart to switch backends

3. **Signal Handlers** (`core/signals.py`)
   - Registered in `core/apps.py`
   - Only loaded on app initialization

4. **Template Tag** (`{% load hms_permissions %}`)
   - Already loaded, but cache affects results

---

## Summary

**What to do:**
1. ✅ Stop server (Ctrl+C)
2. ✅ Run: `python manage.py clear_permission_cache`
3. ✅ Start server: `python manage.py runserver`
4. ✅ Hard refresh browser (Ctrl+F5)

**Expected result:**
- Theatre menu visible for admin/doctor/nurse
- All other menu items show based on role
- No access to restricted modules

---

## Quick Test Script

After restarting, run this to verify everything works:

```bash
python manage.py shell -c "
from accounts.models import CustomUser
from core.models import UIPermission

print('=== MENU VISIBILITY TEST ===\n')

# Get a nurse user
nurse = CustomUser.objects.get(username='nurse_jane')

# Check which menus nurse can see
menus = ['menu_dashboard', 'menu_patients', 'menu_consultations',
         'menu_pharmacy', 'menu_theatre', 'menu_laboratory', 'menu_billing']

for menu_id in menus:
    try:
        perm = UIPermission.objects.get(element_id=menu_id)
        can_see = perm.user_can_access(nurse)
        status = '✓' if can_see else '✗'
        print(f'{status} {menu_id.replace(\"menu_\", \"\").title():15} - {can_see}')
    except:
        print(f'? {menu_id:15} - Not found')

print('\nNurse should see: Dashboard, Patients, Consultations, Theatre')
print('Nurse should NOT see: Pharmacy, Laboratory, Billing')
"
```

**Expected output:**
```
✓ Dashboard       - True
✓ Patients        - True
✓ Consultations   - True
✗ Pharmacy        - False
✓ Theatre         - True
✗ Laboratory      - False
✗ Billing         - False
```

---

## Still Having Issues?

If theatre still doesn't show after restart:

1. **Check server logs** for errors
2. **Verify template file** is being used (not cached version)
3. **Check Django admin**: Can you see UIPermission model?
4. **Test in different browser**: Rule out browser cache issues

---

**Status**: ✅ Theatre permission configured correctly
**Action needed**: Restart server
**Time required**: 1 minute

**RESTART THE SERVER NOW TO SEE THEATRE MENU!**
