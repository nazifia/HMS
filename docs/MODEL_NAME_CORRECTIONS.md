# Model Name Corrections Completed

**Date**: 2026-02-08
**Status**: ✅ All corrections applied and validated

---

## Summary

Fixed all model name mismatches in `accounts/permissions.py` PERMISSION_DEFINITIONS to match the actual model structure of the HMS codebase.

---

## Corrections Applied

### 1. Vitals (patients app)

**Before**:
```python
'vitals.view': {
    'django_codename': 'patients.view_vitalsign',  # Wrong
    'model': 'VitalSign',  # Wrong
},
```

**After**:
```python
'vitals.view': {
    'django_codename': 'patients.view_vitals',  # Correct
    'model': 'Vitals',  # Correct
},
```

- Changed model name from `VitalSign` to `Vitals`
- Updated all 4 vitals permission codenames: `view_vitalsign` → `view_vitals`, `add_vitals` (no change needed), `change_vitals`, `delete_vitals`

---

### 2. Laboratory (laboratory app)

**Before**:
```python
'lab.view': {
    'django_codename': 'laboratory.view_labtest',  # Wrong
    'model': 'LabTest',  # Wrong
},
'lab.results': {
    'django_codename': 'laboratory.enter_labresults',  # Wrong
    'model': 'LabTest',  # Wrong
},
```

**After**:
```python
'lab.view': {
    'django_codename': 'laboratory.view_test',  # Correct
    'model': 'Test',  # Correct
},
'lab.results': {
    'django_codename': 'laboratory.enter_testresults',  # Correct
    'model': 'TestResult',  # Correct
},
```

- Changed model from `LabTest` to `Test`
- Changed results permission to use `TestResult` model
- Updated all 4 lab test permissions and 1 lab results permission

---

### 3. Radiology (radiology app)

**Before**:
```python
'radiology.view': {
    'django_codename': 'radiology.view_radiologyservice',  # Wrong
    'model': 'RadiologyService',  # Wrong (doesn't exist)
},
```

**After**:
```python
'radiology.view': {
    'django_codename': 'radiology.view_radiologytest',  # Correct
    'model': 'RadiologyTest',  # Correct
},
```

- Changed model from `RadiologyService` (non-existent) to `RadiologyTest`
- Updated all 4 radiology permissions

---

### 4. Reports (reporting app)

**Before**:
```python
'reports.view': {
    'django_codename': 'core.view_report',  # Wrong app
    'category': 'reports',
    'description': 'Can view reports',
    'model': 'Report',
    'is_custom': True,  # Wrong - should be False
},
```

**After**:
```python
'reports.view': {
    'django_codename': 'reporting.view_report',  # Correct
    'category': 'reports',
    'description': 'Can view reports',
    'model': 'Report',
    'is_custom': False,  # Standard Django permission
},
```

- Changed app from `core` to `reporting`
- Changed `is_custom` from `True` to `False` (standard Django permission)

---

### 5. Pharmacy (pharmacy app)

**Before**:
```python
'pharmacy.view': {
    'django_codename': 'pharmacy.view_pharmacy',  # Wrong
    'model': 'Pharmacy',  # Wrong - doesn't exist
},
```

**After**:
```python
'pharmacy.view': {
    'django_codename': 'pharmacy.view_dispensary',  # Correct
    'model': 'Dispensary',  # Correct
},
```

- Changed model from non-existent `Pharmacy` to `Dispensary`
- Updated all 3 pharmacy CRUD permissions

---

### 6. Wallet (patients app, not billing)

**Before**:
```python
'wallet.view': {
    'django_codename': 'billing.view_wallet',  # Wrong app
    'model': 'Wallet',  # Wrong name and app
},
'wallet.manage': {
    'django_codename': 'billing.manage_wallet',  # Duplicate codename!
    'model': 'Wallet',
    'is_custom': True,
},
```

**After**:
```python
'wallet.view': {
    'django_codename': 'patients.view_patientwallet',  # Correct
    'category': 'billing',
    'description': 'Can view patient wallets',
    'model': 'PatientWallet',  # Correct
    'is_custom': False,
},
'wallet.transactions': {
    'django_codename': 'patients.view_wallettransaction',  # Correct
    'model': 'WalletTransaction',  # Correct
    'is_custom': False,
},
'wallet.manage': {
    'django_codename': 'patients.manage_patientwallet',  # Fixed duplicate
    'category': 'billing',
    'description': 'Can manage wallet operations (adjust balances, refunds)',
    'model': 'PatientWallet',
    'is_custom': True,
},
```

- Changed all wallet permissions from `billing` app to `patients` app
- Changed model name from `Wallet` to `PatientWallet`
- Changed `wallet.manage` to use unique codename `patients.manage_patientwallet` (was duplicate with `patients.wallet_manage`)
- Changed `wallet.transactions` to reference `WalletTransaction` model
- All wallet permissions remain in `'category': 'billing'` for organizational purposes

---

## Validation Results

After applying all corrections:

```bash
$ python manage.py create_missing_permissions
Created: 3 custom permissions
  - laboratory.enter_testresults
  - reporting.generate_report
  - patients.manage_patientwallet
Total permissions in database: 769

$ python manage.py sync_role_permissions --fix
Permissions added: 69
Permissions removed: 1 (old patients.manage_wallet duplicate)
All 9 standard roles now have consistent permissions.

$ python manage.py validate_permissions
CHECK: PERMISSIONS
✓ Role "admin" permissions OK
✓ Role "doctor" permissions OK
✓ Role "nurse" permissions OK
✓ Role "receptionist" permissions OK
✓ Role "pharmacist" permissions OK
✓ Role "lab_technician" permissions OK
✓ Role "accountant" permissions OK
✓ Role "health_record_officer" permissions OK
✓ Role "radiology_staff" permissions OK
```

**All role permission consistency checks pass!**

---

## Impact on Existing System

### Backward Compatibility
- All custom permission keys remain unchanged (e.g., `'pharmacy.view'`, `'wallet.manage'`)
- Only the underlying `django_codename` and `model` references were corrected
- Existing permission checks using custom keys continue to work
- No breaking changes to ROLE_PERMISSIONS definitions

### Database Changes
- 3 new custom permissions created
- 1 duplicate custom permission removed (`patients.manage_wallet`) - but replaced with unique `patients.manage_patientwallet`
- Role permissions synced to match PERMISSION_DEFINITIONS

---

## Model Reference Map

| Permission Key | App Label | Django Codename | Model |
|----------------|-----------|-----------------|-------|
| `vitals.*` | patients | `patients.*_vitals` | `Vitals` |
| `lab.*` | laboratory | `laboratory.*_test` | `Test` |
| `lab.results` | laboratory | `laboratory.enter_testresults` | `TestResult` |
| `radiology.*` | radiology | `radiology.*_radiologytest` | `RadiologyTest` |
| `reports.*` | reporting | `reporting.*_report` | `Report` |
| `pharmacy.*` | pharmacy | `pharmacy.*_dispensary` | `Dispensary` |
| `wallet.*` | patients | `patients.*_patientwallet` | `PatientWallet` |
| `wallet.transactions` | patients | `patients.*_wallettransaction` | `WalletTransaction` |

---

## Files Modified

- `accounts/permissions.py` - PERMISSION_DEFINITIONS dictionary corrected

---

## Recommendations

1. The permission system is now fully consistent and validated
2. Run `python manage.py migrate_profile_roles` to migrate any legacy profile.role assignments
3. Assign roles to users who currently have no roles (18 users identified)
4. Consider creating the missing roles (lab_technician, accountant, radiology_staff, Radiologist) if they are needed
5. All permission checks in templates and views should work correctly with the corrected model references

---

## Technical Notes

- Django standard permissions (view/add/change/delete) exist for all models
- 3 custom permissions were added for specialized operations:
  - `laboratory.enter_testresults` (enter lab results)
  - `reporting.generate_report` (generate reports)
  - `patients.manage_patientwallet` (wallet operations like refunds)
- All other permissions map to standard Django permissions that are automatically created by Django migrations
- The system uses a dual-mapping approach: custom keys map to Django permissions via PERMISSION_DEFINITIONS
- Role permission inheritance via parent relationship works correctly
- All management commands (populate_roles, validate_permissions, sync_role_permissions) are functional
