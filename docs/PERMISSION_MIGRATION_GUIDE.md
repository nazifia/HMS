# Permission & Role Migration Guide

This guide helps you migrate from the old single-role system to the new multi-role RBAC system.

## Background

The HMS RBAC system previously used a single `CustomUserProfile.role` field. The new system uses a many-to-many relationship `CustomUser.roles` for full flexibility.

### Key Differences

| Aspect | Old System | New System |
|--------|------------|------------|
| Storage | `profile.role` (CharField) | `user.roles` (M2M to Role model) |
| Multiple Roles | No | Yes |
| Role Hierarchy | No | Yes (via parent field) |
| Permission Control | Hardcoded | Dynamic via admin |
| Migration Path | N/A | This guide |

---

## Migration Checklist

### Phase 1: Preparation (Before Migration)

1. **Backup your database**
   ```bash
   python manage.py dumpdata > backup.json
   ```

2. **Verify current state**
   ```bash
   # Count users with profile.role set
   python manage.py shell -c "
   from accounts.models import CustomUserProfile
   print('Users with profile.role:', CustomUserProfile.objects.filter(role__isnull=False).count())
   "
   ```

3. **Ensure all default roles exist**
   ```bash
   python manage.py populate_roles
   ```

4. **Validate permission definitions**
   ```bash
   python manage.py validate_permissions
   ```

5. **Review custom roles**
   - Are there custom roles beyond the 9 defaults?
   - Document them and create role mapping JSON (see below)

### Phase 2: Dry Run Migration

```bash
python manage.py migrate_profile_roles --dry-run --verbose
```

Review output carefully. Look for:
- ✅ Users that will be migrated
- ⚠️ Users with unmapped legacy roles
- ❌ Missing target roles

### Phase 3: Execute Migration

#### Standard Migration

```bash
python manage.py migrate_profile_roles --verbose
```

This:
- For each `CustomUserProfile.role`, finds the corresponding `Role`
- Adds the `Role` to `user.roles` M2M
- Keeps `profile.role` unchanged (for backward compatibility)

#### With Custom Role Mapping

If your legacy roles don't match the defaults 1:1, create `mapping.json`:

```json
{
    "admin": "admin",
    "doctor": "doctor",
    "nurse": "nurse",
    "receptionist": "receptionist",
    "pharmacist": "pharmacist",
    "lab_technician": "lab_technician",
    "accountant": "accountant",
    "health_officer": "health_record_officer",
    "custom_role_1": "custom_role_new"
}
```

Then run:
```bash
python manage.py migrate_profile_roles --role-mapping=mapping.json
```

#### Auto-create Missing Roles

If you have custom legacy roles not in the system:

```bash
python manage.py migrate_profile_roles --create-missing-roles
```

This creates empty `Role` objects with the legacy names automatically.

### Phase 4: Verification

1. **Check users with no roles**
   ```bash
   python manage.py validate_permissions --checks=users
   ```

2. **Test permission checks**
   - Login as migrated user
   - Try accessing features for their old role
   - Verify access is granted/denied as expected

3. **Check for users with both old and new**
   ```bash
   python manage.py shell -c "
   from accounts.models import CustomUserProfile
   profiles = CustomUserProfile.objects.filter(role__isnull=False)
   for p in profiles[:5]:
       user = p.user
       print(f'{user.username}: profile.role={p.role}, user.roles={list(user.roles.values_list(\"name\", flat=True))}')
   "
   ```

4. **Test role hierarchy**
   - If you use role inheritance, verify child roles inherit parent permissions

### Phase 5: Cleanup (Optional)

After successful migration and verification, you may want to clear `profile.role`:

```bash
python manage.py migrate_profile_roles --clear-profile-roles
```

**Warning**: This is irreversible. Ensure full testing before doing this.

#### How to Clear Safely

Option A: Use the flag (as above) after verification

Option B: Manual SQL (advanced):
```sql
UPDATE accounts_customuserprofile SET role = NULL WHERE role IS NOT NULL;
```

**Keep backward compatibility**: If any code still references `profile.role`, keep it populated or update that code first.

---

## Common Scenarios

### Scenario 1: All Users Use Standard Roles

✅ Simple - just run:
```bash
python manage.py migrate_profile_roles
```

Default mapping handles all 9 standard roles.

### Scenario 2: Some Custom Legacy Roles

Create mapping file:

```json
{
    "admin": "admin",
    "doctor": "doctor",
    "nurse": "nurse",
    "senior_nurse": "nurse",      // Map custom to standard
    "head_nurse": "nurse",        // Map custom to standard
    "receptionist": "receptionist"
}
```

Then:
```bash
python manage.py migrate_profile_roles --role-mapping=mapping.json
```

### Scenario 3: Many Unique Legacy Roles

If each user has unique legacy role name (problematic!), consider:

1. **Consolidate**: Map similar roles to standard ones
2. **Create new Role objects**: Use `--create-missing-roles`
3. **Manual review**: Export list, decide mapping, then import

Export existing roles:
```bash
python manage.py shell -c "
from accounts.models import CustomUserProfile
roles = CustomUserProfile.objects.filter(role__isnull=False).values_list('role', flat=True).distinct()
for r in sorted(roles):
    print(r)
" > legacy_roles.txt
```

### Scenario 4: Users Already Have `user.roles` Set

The migration is **idempotent** - running it multiple times is safe:

- If user already has the role in `user.roles`, no error
- If `profile.role` maps to a role they already have, it's fine (no duplicate)
- Uses Django's M2M `add()` which avoids duplicates

You can safely run migration even if partial migration already occurred.

---

## Testing Migration

### Test Script

Create `test_migration.py`:

```python
from accounts.models import CustomUser, Role
from accounts.permissions import get_user_roles

# Pick a migrated user
user = CustomUser.objects.get(username='testuser')

# Check roles
roles = get_user_roles(user)
print(f'User roles: {roles}')

# Check specific permission
from accounts.permissions import user_has_permission
print('Can view patient?', user_has_permission(user, 'patients.view'))

# Check in template
from django.test import RequestFactory
request = RequestFactory().get('/')
request.user = user
from accounts.context_processors import user_permissions
ctx = user_permissions(request)
print('Template context roles:', ctx['user_roles'])
print('Template context perms:', list(ctx['user_permissions'].keys())[:10])
```

### Admin Interface

1. Go to `/admin/accounts/customuser/`
2. Find migrated user
3. Should see role badges in list view
4. Click user - Roles inline should show assigned roles

---

## Rollback Procedure

If something goes wrong:

1. **Stop application** (prevent new assignments)

2. **Restore database from backup**
   ```bash
   python manage.py loaddata backup.json
   ```

3. **Or selectively remove `user.roles` assignments**
   ```python
   # In Django shell
   for user in CustomUser.objects.all():
       user.roles.clear()
   ```

4. **Keep `profile.role` intact** (if backup not available, at least this data remains)

---

## Validation After Migration

### Run Full Validation

```bash
python manage.py validate_permissions
```

Expected output:
- ✅ No circular references
- ✅ No users without roles (unless intentionally role-less)
- ✅ No legacy `profile.role` (if cleared)
- ✅ All default roles exist
- ✅ Role permissions match definitions

### Fix Common Issues

```bash
# Fix permission mismatches
python manage.py sync_role_permissions --fix

# Fix circular role references
python manage.py validate_permissions --fix
```

---

## Post-Migration Tasks

1. **Update templates**: If templates check `profile.role`, update to use template tags:
   ```django
   {# Old #}
   {% if user.profile.role == 'doctor' %}

   {# New #}
   {% if user|in_role:'doctor' %}
   ```

2. **Remove old role checks in code**:
   ```python
   # Old
   if user.profile.role == 'doctor':
       ...

   # New
   from accounts.permissions import user_in_role
   if user_in_role(user, 'doctor'):
       ...
   ```

3. **Update documentation**: Reflect new roles in user guides, SOPs

4. **Train staff**: If migration changed role assignments, train affected users

5. **Monitor logs**: Watch for permission denied errors
   ```bash
   tail -f logs/hms.log | grep -i "permission"
   ```

---

## Rollout Strategy for Production

### Day 1: Migration
- Run migrate_profile_roles during maintenance window
- Keep `profile.role` values (no `--clear-profile-roles`)
- Monitor logs for errors

### Day 2-3: Testing
- Have sample users from each role test their access
- Verify all expected permissions work
- Check for false denials

### Day 4-5: Fix & Adjust
- Run `sync_role_permissions --fix` if needed
- Adjust custom role mappings if misconfigurations found
- Add missing default roles

### Week 2: Cleanup
- If all tests pass, clear `profile.role`:
  ```bash
  python manage.py migrate_profile_roles --clear-profile-roles
  ```
- Update code to remove `profile.role` checks
  (Search codebase for `.profile.role`)

### Week 3-4: Deprecation
- Add warnings if code still uses `profile.role`
- Plan to remove CustomUserProfile.role field in next major version (optional)

---

## FAQ

**Q: Will migration affect existing permissions?**
A: No. Permissions are derived from roles. Migration only assigns roles. Existing `user.has_perm()` checks continue working.

**Q: What if user already has the role via `user.roles`?**
A: Migration uses `add()` which is idempotent. No duplicate assignments.

**Q: Can I undo the migration?**
A: Yes - `user.roles.clear()` removes assignments without touching `profile.role`.

**Q: Should I delete the `role` field from CustomUserProfile?**
A: Not yet. Keep it for backward compatibility. Plan removal in next major version after confirming no code uses it.

**Q: What about users with no `profile.role`?**
A: They are skipped in migration. They need manual role assignment.

**Q: How do I handle role inheritance in migration?**
A: Role inheritance (`Role.parent`) is configured in the Role model itself, not during migration. Ensure parent relationships are set in admin before assigning roles to users.

**Q: Does migration change Django's `user.groups`?**
A: No. HMS uses separate `Role` model, not Django Groups.

---

## Support

If you encounter issues:

1. Check `logs/hms.log` for errors
2. Run `python manage.py validate_permissions` for diagnostics
3. Consult `docs/ROLE_PERMISSIONS_REFERENCE.md` for permission matrix
4. Search codebase for `profile.role` references: `grep -r "profile.role" .`
5. Create issue in GitHub repo with:
   - Error message
   - Output of `validate_permissions`
   - Sample user showing the problem

---

**Next Steps**: After migration, review `docs/ROLE_PERMISSIONS_REFERENCE.md` for usage examples and best practices.
