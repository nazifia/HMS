# Comprehensive Cache Fix - Persistent Issues

## Root Cause: LocMemCache Limitation

Your Django setup uses **LocMemCache** (Local Memory Cache):
- Each Django worker/process has its own independent cache
- Clearing cache in one process doesn't affect others
- **This is the reason caching issues persist!**

---

## Immediate Solutions

### Solution 1: Restart Django Server (Quick Fix)

**This clears ALL process caches:**

```bash
# Stop the server (Ctrl+C)
# Then restart:
python manage.py runserver
```

**Why this works**: Restarting clears all in-memory caches across all processes.

### Solution 2: Clear Browser Cache

Users must hard-refresh their browsers:
- **Windows**: `Ctrl + F5` or `Ctrl + Shift + R`
- **Mac**: `Cmd + Shift + R`
- **Or**: Open in incognito/private window

### Solution 3: Switch to Shared Cache (Permanent Fix)

Use a cache backend that's shared across all processes.

---

## Permanent Fix: Use Database Cache (Simple)

**Step 1**: Create cache table

```bash
python manage.py createcachetable
```

**Step 2**: Update `settings.py`

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
    }
}
```

**Step 3**: Restart server

```bash
python manage.py runserver
```

**Advantages**:
- ✅ Shared across all processes
- ✅ Persists across server restarts
- ✅ No additional dependencies
- ✅ Easy to clear (`DELETE FROM cache_table`)

**Disadvantages**:
- ⚠ Slower than Redis/Memcached
- ⚠ Adds database load

---

## Best Solution: Use Redis (Production-Ready)

### Step 1: Install Redis

**Windows** (using Memurai - Redis for Windows):
```bash
# Download from: https://www.memurai.com/get-memurai
# Or use WSL2 with Redis
```

**Linux/Mac**:
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# Mac
brew install redis

# Start Redis
redis-server
```

### Step 2: Install django-redis

```bash
pip install django-redis
```

### Step 3: Update `settings.py`

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'hms',
        'TIMEOUT': 300,  # 5 minutes default
    }
}
```

### Step 4: Update requirements.txt

```bash
pip freeze > requirements.txt
```

### Step 5: Restart server

```bash
python manage.py runserver
```

**Advantages**:
- ✅ Extremely fast
- ✅ Shared across all processes
- ✅ Supports pattern deletion (`cache.delete_pattern("ui_perm_*")`)
- ✅ Production-ready
- ✅ Can be used for sessions, celery, etc.

---

## Alternative: Disable Caching for UI Permissions (Not Recommended)

If you want to completely disable caching for UI permissions:

### Update `core/templatetags/hms_permissions.py`

```python
@register.filter
def can_show_ui(user, element_id):
    """Check if a UI element should be shown to the user."""
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    # DISABLED CACHING - Always check database
    try:
        ui_perm = UIPermission.objects.get(element_id=element_id, is_active=True)
        return ui_perm.user_can_access(user)
    except UIPermission.DoesNotExist:
        return True
```

### Update `core/decorators.py`

Remove caching from both decorators:
- `ui_permission_required`
- `api_ui_permission_required`

**Trade-off**: More database queries, but no cache issues.

---

## Troubleshooting Current Setup

### Check if Multiple Processes are Running

```bash
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000
```

If you see multiple processes, they each have their own cache!

### Clear All Caches Immediately

```bash
# Method 1: Use management command
python manage.py clear_permission_cache

# Method 2: Restart server
# Ctrl+C then restart

# Method 3: Python shell
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
>>> exit()
```

### Force Users to Hard Refresh

Add cache-control headers to prevent browser caching:

**Update `base.html`**:

```html
<head>
    <!-- Prevent browser caching -->
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    ...
</head>
```

---

## Recommended Action Plan

### For Development (Right Now):

1. **Restart Django server** (clears all caches)
   ```bash
   # Ctrl+C to stop
   python manage.py runserver
   ```

2. **Clear browser cache** (hard refresh)
   - `Ctrl + F5` or `Ctrl + Shift + R`

3. **Test with incognito/private window**
   - Eliminates browser cache as variable

### For Production (Long-term):

1. **Switch to Database Cache** (simple, works immediately)
   ```bash
   python manage.py createcachetable
   ```

   Update settings.py:
   ```python
   CACHES = {
       'default': {
           'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
           'LOCATION': 'cache_table',
       }
   }
   ```

2. **OR Switch to Redis** (better performance)
   - Install Redis
   - Install django-redis
   - Update settings.py

---

## Testing the Fix

### Test Script

```python
# test_cache.py
from django.core.cache import cache
from accounts.models import CustomUser
from core.models import UIPermission

# Clear all caches first
cache.clear()
print("✓ Cleared all caches")

# Get test data
jane = CustomUser.objects.get(username='nurse_jane')
pharmacy = UIPermission.objects.get(element_id='menu_pharmacy')

# Test 1: Check permission (creates cache)
result1 = pharmacy.user_can_access(jane)
print(f"Can Jane access pharmacy? {result1}")

# Test 2: Check cache exists
cache_key = f'ui_perm_{jane.id}_menu_pharmacy'
cached = cache.get(cache_key)
print(f"Cached value: {cached}")

# Test 3: Clear specific cache
cache.delete(cache_key)
print(f"Cleared cache for key: {cache_key}")

# Test 4: Verify cleared
cached_after = cache.get(cache_key)
print(f"Cached value after clear: {cached_after}")

if cached_after is None:
    print("\n✅ SUCCESS: Cache is working and can be cleared!")
else:
    print("\n❌ FAILED: Cache clearing not working!")
```

Run it:
```bash
python manage.py shell < test_cache.py
```

---

## Quick Reference

### Clear Cache Commands

```bash
# Clear all UI permission caches
python manage.py clear_permission_cache

# Clear entire Django cache
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Restart server (clears LocMemCache)
# Ctrl+C then python manage.py runserver
```

### Check Current Cache

```bash
python manage.py shell -c "
from django.core.cache import cache
print('Cache Backend:', cache.__class__.__name__)
print('Cache Location:', getattr(cache, '_cache', 'N/A'))
"
```

---

## Summary

**The Issue**: LocMemCache is process-local, not shared
**Quick Fix**: Restart server + hard refresh browser
**Permanent Fix**: Switch to Database Cache or Redis

**Immediate Action Required**:
1. Restart Django server
2. Have users hard-refresh browsers
3. Switch to Database Cache or Redis

