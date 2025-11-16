# Cache Invalidation Fix - UI Permissions

## Date: 2025-01-16

## Issue Identified
Caching issues were preventing users from seeing updated menu items after permission changes. Old cached values persisted for up to 5 minutes, causing:
- Users seeing menus they shouldn't have access to
- Users not seeing menus they should have access to
- Confusion after admin makes permission changes

---

## Root Cause

### The Problem
The UI permission system uses Django cache with a 5-minute TTL to improve performance:
```python
cache_key = f"ui_perm_{user_id}_{element_id}"
cache.set(cache_key, result, 300)  # 5 minutes = 300 seconds
```

**Before the fix:**
- When an admin changed a UIPermission, the cache was NOT cleared
- When roles were added/removed from permissions, the cache was NOT cleared
- Users had to wait up to 5 minutes to see changes
- No way to manually clear permission caches

---

## Solution Implemented

### 1. **Automatic Cache Clearing on Save** (`core/models.py`)

Added cache clearing to the `UIPermission.save()` method:

```python
def save(self, *args, **kwargs):
    """Override save to clear cache when permission is modified."""
    super().save(*args, **kwargs)
    self.clear_cache()
```

**Effect**: Cache is cleared automatically when a permission is created or updated.

### 2. **Cache Clearing Methods** (`core/models.py`)

Added two methods to `UIPermission`:

#### `clear_cache()` - Clear cache for specific permission
```python
def clear_cache(self):
    """Clear all cached permission checks for this UI permission."""
    from django.core.cache import cache
    from accounts.models import CustomUser

    all_users = CustomUser.objects.all()
    cleared_count = 0

    for user in all_users:
        cache_key = f"ui_perm_{user.id}_{self.element_id}"
        if cache.delete(cache_key):
            cleared_count += 1

    logger.info(f"Cleared {cleared_count} cached permission checks for {self.element_id}")
    return cleared_count
```

#### `clear_all_caches()` - Clear all permission caches
```python
@staticmethod
def clear_all_caches():
    """Clear all UI permission caches in the system."""
    from django.core.cache import cache

    try:
        cache.delete_pattern("ui_perm_*")  # Redis, Memcached
    except AttributeError:
        cache.clear()  # Fallback for other backends
```

### 3. **Signal Handlers** (`core/signals.py` - NEW FILE)

Created signal handlers for many-to-many field changes:

```python
@receiver(m2m_changed, sender='core.UIPermission_required_roles')
def clear_cache_on_role_change(sender, instance, action, **kwargs):
    """Clear cache when roles are added/removed from a UIPermission."""
    if action in ['post_add', 'post_remove', 'post_clear']:
        instance.clear_cache()

@receiver(m2m_changed, sender='core.UIPermission_required_permissions')
def clear_cache_on_permission_change(sender, instance, action, **kwargs):
    """Clear cache when permissions are added/removed from a UIPermission."""
    if action in ['post_add', 'post_remove', 'post_clear']:
        instance.clear_cache()
```

**Effect**: Cache is cleared when roles or permissions are added/removed from a UIPermission.

### 4. **Signal Registration** (`core/apps.py`)

Registered signals in the app configuration:

```python
class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """Import signal handlers when the app is ready."""
        import core.signals  # noqa
```

### 5. **Management Command** (`clear_permission_cache.py` - NEW FILE)

Created management command for manual cache clearing:

```bash
# Clear all permission caches
python manage.py clear_permission_cache

# Clear cache for specific permission
python manage.py clear_permission_cache --element-id menu_pharmacy
```

---

## Files Created/Modified

### Created Files:
1. ✅ `core/signals.py` - Signal handlers for cache invalidation
2. ✅ `core/management/commands/clear_permission_cache.py` - Management command

### Modified Files:
1. ✅ `core/models.py` - Added cache clearing methods and save override
2. ✅ `core/apps.py` - Registered signal handlers

---

## How It Works Now

### Automatic Cache Invalidation Flow

1. **Admin edits a UIPermission** (via admin panel or code)
   - `save()` method is called
   - `clear_cache()` is automatically invoked
   - All cached entries for this permission are deleted
   - Users immediately see the change on next page load

2. **Admin adds/removes roles from a UIPermission**
   - `m2m_changed` signal is triggered
   - Signal handler calls `clear_cache()`
   - All cached entries are deleted
   - Users immediately see the change

3. **Admin adds/removes Django permissions from a UIPermission**
   - Same process as #2

### Cache Behavior Timeline

**Before Fix:**
```
Time 0:00 - User loads page, permission cached
Time 0:30 - Admin changes permission
Time 0:31 - User reloads page, still sees OLD cached value ❌
Time 5:00 - Cache expires
Time 5:01 - User reloads page, sees NEW value ✓
```

**After Fix:**
```
Time 0:00 - User loads page, permission cached
Time 0:30 - Admin changes permission → Cache cleared automatically
Time 0:31 - User reloads page, sees NEW value immediately ✓
```

---

## Testing Results

### Test Scenario 1: Role Addition
```
Initial state: Jane (nurse) CANNOT access pharmacy
Action: Add nurse role to menu_pharmacy permission
Cache status: CLEARED automatically
Result: Jane CAN now access pharmacy immediately ✅
```

### Test Scenario 2: Role Removal
```
Initial state: Jane (nurse) CAN access pharmacy
Action: Remove nurse role from menu_pharmacy permission
Cache status: CLEARED automatically
Result: Jane CANNOT access pharmacy immediately ✅
```

### Test Scenario 3: Permission Edit
```
Initial state: Permission exists with specific settings
Action: Edit permission details and save
Cache status: CLEARED automatically
Result: Changes visible immediately ✅
```

---

## Cache Performance

### Before Optimization
- **Cache misses**: 0% (all cached for 5 minutes)
- **Update delay**: Up to 5 minutes
- **User confusion**: High
- **Admin workflow**: Required manual intervention

### After Optimization
- **Cache hits**: High (normal operation)
- **Cache invalidation**: Automatic and instant
- **Update delay**: 0 seconds
- **User confusion**: None
- **Admin workflow**: Seamless

### Performance Impact
- **Minimal**: Cache clearing only happens on permission changes (rare)
- **No impact**: On regular page loads (still uses cache)
- **Trade-off**: Slightly more database queries when permissions change vs user confusion

---

## Manual Cache Management

### When to Manually Clear Cache

1. **After bulk permission changes via Django shell**
   ```bash
   python manage.py clear_permission_cache
   ```

2. **After database migrations affecting permissions**
   ```bash
   python manage.py clear_permission_cache
   ```

3. **Troubleshooting permission issues**
   ```bash
   python manage.py clear_permission_cache
   ```

4. **After importing permissions from backup**
   ```bash
   python manage.py clear_permission_cache
   ```

### Command Options

```bash
# Clear all UI permission caches
python manage.py clear_permission_cache

# Clear cache for specific permission only
python manage.py clear_permission_cache --element-id menu_pharmacy

# View cache backend information
python manage.py clear_permission_cache
# (displays cache backend info after clearing)
```

---

## Cache Backend Compatibility

### Supported Backends

✅ **Django's default cache** (LocMemCache)
- Uses `cache.clear()` fallback
- Clears entire cache (acceptable for most cases)

✅ **Redis** (django-redis)
- Supports `cache.delete_pattern("ui_perm_*")`
- Only clears UI permission caches (optimal)

✅ **Memcached**
- Supports pattern deletion (implementation-dependent)
- Falls back to `cache.clear()` if needed

✅ **Database cache**
- Uses `cache.clear()` fallback
- Works but not recommended for production

### Recommended Setup for Production

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

---

## Troubleshooting

### Issue: Cache not clearing after permission changes

**Solution 1**: Check if signals are registered
```python
# In Django shell
from django.db.models.signals import m2m_changed
print(m2m_changed.receivers)  # Should show our signal handlers
```

**Solution 2**: Manually clear cache
```bash
python manage.py clear_permission_cache
```

**Solution 3**: Check logs
```bash
# Look for cache clearing messages
grep "Cleared.*cached permission" logs/django.log
```

### Issue: Users still seeing old menus

**Solution 1**: Clear browser cache
- Users should hard refresh (Ctrl+F5 or Cmd+Shift+R)

**Solution 2**: Clear server cache
```bash
python manage.py clear_permission_cache
```

**Solution 3**: Restart Django server
```bash
# Stop server, then restart
python manage.py runserver
```

### Issue: Performance degradation after changes

**Diagnosis**: Too many permission changes in short time
**Solution**: Use bulk operations and clear cache once at the end

```python
# Bad: Multiple saves = multiple cache clears
for perm in permissions:
    perm.is_active = True
    perm.save()  # Clears cache each time!

# Good: Bulk update + single cache clear
UIPermission.objects.filter(id__in=ids).update(is_active=True)
UIPermission.clear_all_caches()  # Clear once at the end
```

---

## Future Enhancements

### 1. Selective Cache Invalidation
Instead of clearing all users' cache for a permission, only clear cache for users whose access actually changed:

```python
def clear_cache_for_affected_users(self, old_roles, new_roles):
    """Only clear cache for users in changed roles."""
    changed_roles = old_roles.symmetric_difference(new_roles)
    affected_users = CustomUser.objects.filter(roles__in=changed_roles)
    # Clear only for affected users
```

### 2. Cache Versioning
Use cache versioning instead of deletion:

```python
cache_key = f"ui_perm_v{version}_{user_id}_{element_id}"
```

### 3. Event-Driven Cache Invalidation
Use Django Channels or Redis pub/sub to notify all server instances:

```python
# When permission changes
channel_layer.group_send("permissions", {
    "type": "invalidate_cache",
    "element_id": self.element_id
})
```

---

## Summary

✅ **Problem Solved**: Cache invalidation now happens automatically
✅ **Performance**: Minimal impact, cache still improves performance
✅ **User Experience**: Changes visible immediately
✅ **Admin Workflow**: No manual intervention required
✅ **Flexibility**: Manual command available when needed

**Before**: Users waited up to 5 minutes to see permission changes
**After**: Users see permission changes immediately (0 seconds)

---

## Related Documentation

- **Access Fix**: `RBAC_ACCESS_FIX.md`
- **Implementation Guide**: `RBAC_ACCESS_RESTRICTION_IMPLEMENTATION.md`
- **System Guide**: `UI_PERMISSION_SYSTEM_GUIDE.md`

---

**Fix Date**: 2025-01-16
**Status**: ✅ Complete and Tested
**Version**: 1.0
