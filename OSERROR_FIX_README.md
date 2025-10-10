# OSError [Errno 22] Invalid Argument - Fix Documentation

## Problem Description

When attempting to log in to the HMS application on Windows, users encountered the following error:

```
OSError at /accounts/login/
[Errno 22] Invalid argument
```

This error occurred during the authentication process and prevented users from logging in.

## Root Cause

The error was caused by **Windows console encoding limitations**. When Django's logging system tried to output log messages containing Unicode characters (like special symbols in usernames or formatted strings) to the Windows console, the console couldn't handle the encoding, resulting in an `OSError [Errno 22]`.

### Technical Details

1. **Windows Console Limitations**: The Windows console (cmd.exe/PowerShell) has limited Unicode support and can fail when trying to display certain characters.

2. **Django's StreamHandler**: By default, Django uses `logging.StreamHandler` which writes directly to the console (stdout/stderr).

3. **Unicode in Log Messages**: Log messages containing:
   - User names with special characters
   - Formatted strings with Unicode symbols
   - Audit log details with JSON data
   
   These could trigger the encoding error.

## Solution Implemented

### 1. Custom Logging Handlers (`core/logging_handlers.py`)

Created two custom logging handlers that handle encoding errors gracefully:

#### SafeStreamHandler
- Wraps the console stream with UTF-8 encoding
- Replaces unencodable characters instead of crashing
- Catches and silently handles OSError exceptions
- Falls back to ASCII encoding if UTF-8 fails

```python
class SafeStreamHandler(logging.StreamHandler):
    """Handles encoding errors gracefully on Windows"""
    def emit(self, record):
        try:
            msg = self.format(record)
            stream.write(msg + self.terminator)
        except UnicodeEncodeError:
            # Fallback to ASCII
            msg_ascii = msg.encode('ascii', errors='replace').decode('ascii')
            stream.write(msg_ascii + self.terminator)
        except OSError:
            # Silently ignore Windows console errors
            pass
```

#### WindowsSafeFileHandler
- Ensures UTF-8 encoding for file-based logging
- Extends `RotatingFileHandler` with explicit UTF-8 encoding

### 2. Updated Logging Configuration (`hms/settings.py`)

Modified Django's logging configuration to:

1. **Detect Windows Platform**:
   ```python
   import platform
   IS_WINDOWS = platform.system() == 'Windows'
   ```

2. **Auto-enable File Logging on Windows**:
   ```python
   if IS_WINDOWS and not LOG_FILE:
       LOG_FILE = os.path.join(BASE_DIR, 'logs', 'hms.log')
       os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
   ```

3. **Use Safe Handlers**:
   ```python
   'handlers': {
       'console': {
           'class': 'core.logging_handlers.SafeStreamHandler' if IS_WINDOWS else 'logging.StreamHandler',
       },
       'file': {
           'class': 'core.logging_handlers.WindowsSafeFileHandler',
           'encoding': 'utf-8',
       },
   }
   ```

### 3. Replaced Print Statements (`accounts/views.py`)

Replaced all `print()` statements with proper logging:

**Before**:
```python
print(f"User {username} (ID: {user_id}) logged out. Reason: {logout_reason}")
```

**After**:
```python
logger.info(f"User {username} (ID: {user_id}) logged out. Reason: {logout_reason}")
```

## Files Modified

1. **`hms/settings.py`** (Lines 309-399)
   - Added platform detection
   - Configured Windows-safe logging handlers
   - Auto-enabled file logging on Windows

2. **`accounts/views.py`** (Lines 1, 25, 159, 1323)
   - Added logging import
   - Created logger instance
   - Replaced print statements with logger calls

3. **`core/logging_handlers.py`** (New file)
   - Created SafeStreamHandler class
   - Created WindowsSafeFileHandler class

4. **`test_login_fix.py`** (New file)
   - Test script to verify the fix

## Testing

### Automated Test

Run the test script to verify the fix:

```bash
python test_login_fix.py
```

Expected output:
```
============================================================
Testing Authentication Fix for OSError [Errno 22]
============================================================

1. Testing logging configuration...
   ✓ Logging works correctly

2. Checking for test users...
   Found X users in database

3. Testing authentication backend...
   Testing with user: XXXXXXXXXX
   Authentication result (expected None): None
   ✓ Authentication backend works without OSError

4. Checking log file...
   ✓ Log file created: C:\...\HMS\logs\hms.log
   Last log entry: ...

============================================================
✓ All tests passed! The OSError fix is working.
============================================================
```

### Manual Test

1. **Clear Python Cache** (Important!):
   ```powershell
   Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Recurse -Force
   Get-ChildItem -Path . -Filter "*.pyc" -Recurse -Force | Remove-Item -Force
   ```

2. **Restart Django Server**:
   ```bash
   python manage.py runserver
   ```

3. **Test Login**:
   - Navigate to `http://127.0.0.1:8000/accounts/login/`
   - Enter valid credentials
   - Login should work without OSError

4. **Check Log File**:
   - Log file location: `HMS/logs/hms.log`
   - Verify authentication logs are being written

## Log File Location

On Windows, logs are automatically written to:
```
C:\Users\dell\Desktop\MY_PRODUCTS\HMS\logs\hms.log
```

The log file:
- Uses UTF-8 encoding
- Rotates at 10MB
- Keeps 5 backup files
- Contains detailed logging information

## Benefits

1. **No More OSError**: Console encoding errors are handled gracefully
2. **Better Debugging**: All logs saved to file for later analysis
3. **Cross-Platform**: Works on both Windows and Unix-like systems
4. **Automatic**: No manual configuration needed on Windows
5. **Robust**: Multiple fallback mechanisms prevent crashes

## Troubleshooting

### If OSError Still Occurs

1. **Clear all Python cache**:
   ```powershell
   Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Recurse -Force
   ```

2. **Verify log directory exists**:
   ```powershell
   New-Item -ItemType Directory -Force -Path "logs"
   ```

3. **Check file permissions**: Ensure the application can write to the `logs` directory

4. **Restart the server**: Stop and restart the Django development server

### Check Log File

If login fails, check the log file for detailed error messages:
```powershell
Get-Content logs\hms.log -Tail 50
```

## Additional Notes

- The fix is **automatic on Windows** - no manual configuration needed
- On Linux/Mac, the original StreamHandler is used (no performance impact)
- Log files are automatically rotated to prevent disk space issues
- All authentication events are now logged for security auditing

## Related Issues

- Windows console encoding limitations
- Django logging on Windows
- Unicode handling in Python logging
- OSError [Errno 22] in Django authentication

## Version Information

- **Django Version**: 5.2.6
- **Python Version**: 3.13.7
- **Platform**: Windows (win32)
- **Fix Date**: 2025-10-10

