"""
Monkey patches for Django to fix Windows OSError issues.
This module patches Django's internal functions to prevent console encoding errors.
"""

import sys
import os
import logging

logger = logging.getLogger(__name__)


def patch_django_for_windows():
    """
    Apply patches to Django to prevent OSError on Windows.
    This should be called early in the application startup.
    """
    if sys.platform != 'win32':
        return  # Only patch on Windows
    
    logger.info("Applying Windows OSError patches to Django...")
    
    # Patch 1: Wrap sys.stdout and sys.stderr with error handling
    _patch_stdout_stderr()
    
    # Patch 2: Patch Django's authentication to suppress console output
    _patch_django_auth()
    
    # Patch 3: Patch Django's logging setup
    _patch_django_logging()
    
    logger.info("Windows OSError patches applied successfully")


def _patch_stdout_stderr():
    """
    Wrap stdout and stderr to handle encoding errors gracefully.
    """
    import io
    
    class SafeWriter(io.TextIOWrapper):
        """Text wrapper that handles encoding errors gracefully."""
        
        def write(self, s):
            try:
                return super().write(s)
            except (OSError, UnicodeEncodeError):
                # Silently ignore encoding errors
                return len(s)
        
        def flush(self):
            try:
                return super().flush()
            except OSError:
                # Silently ignore flush errors
                pass
    
    # Only wrap if not already wrapped
    if not isinstance(sys.stdout, SafeWriter) and hasattr(sys.stdout, 'buffer'):
        sys.stdout = SafeWriter(
            sys.stdout.buffer,
            encoding='utf-8',
            errors='replace',
            line_buffering=True
        )
    
    if not isinstance(sys.stderr, SafeWriter) and hasattr(sys.stderr, 'buffer'):
        sys.stderr = SafeWriter(
            sys.stderr.buffer,
            encoding='utf-8',
            errors='replace',
            line_buffering=True
        )


def _patch_django_auth():
    """
    Patch Django's authentication to suppress console output.
    """
    try:
        from django.contrib.auth import authenticate as original_authenticate
        from functools import wraps
        
        @wraps(original_authenticate)
        def safe_authenticate(*args, **kwargs):
            """Wrapper around Django's authenticate that suppresses console output."""
            # Temporarily redirect stdout/stderr to null
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            
            try:
                # Redirect to null device
                null_device = open(os.devnull, 'w', encoding='utf-8')
                sys.stdout = null_device
                sys.stderr = null_device
                
                # Call original authenticate
                result = original_authenticate(*args, **kwargs)
                
                return result
            except OSError as e:
                logger.error(f"OSError in authenticate: {e}")
                return None
            finally:
                # Restore stdout/stderr
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                try:
                    null_device.close()
                except:
                    pass
        
        # Replace Django's authenticate function
        import django.contrib.auth
        django.contrib.auth.authenticate = safe_authenticate
        
        logger.info("Django authenticate function patched")
        
    except Exception as e:
        logger.error(f"Failed to patch Django authenticate: {e}")


def _patch_django_logging():
    """
    Patch Django's logging to use file-based logging only.
    """
    try:
        import logging.handlers
        
        # Create a custom handler that never writes to console
        class NullConsoleHandler(logging.Handler):
            """Handler that discards all log records."""
            def emit(self, record):
                pass
        
        # Replace StreamHandler with NullConsoleHandler for all loggers
        for logger_name in logging.Logger.manager.loggerDict:
            logger_obj = logging.getLogger(logger_name)
            for handler in logger_obj.handlers[:]:
                if isinstance(handler, logging.StreamHandler):
                    logger_obj.removeHandler(handler)
                    logger_obj.addHandler(NullConsoleHandler())
        
        logger.info("Django logging patched to disable console output")
        
    except Exception as e:
        logger.error(f"Failed to patch Django logging: {e}")


def patch_mysql_convert_tz():
    """Make __date/__time/Trunc lookups work on MySQL servers without tz tables.

    Django compiles `datetime_field__date=...` to CONVERT_TZ(col, 'UTC',
    'Africa/Lagos'). With named zones, CONVERT_TZ returns NULL when the MySQL
    server's timezone tables are empty (e.g. PythonAnywhere) — so every such
    filter silently matches nothing. Numeric offsets ('+01:00') need no tz
    tables, so rewrite both zone args as offsets.

    ponytail: offset is computed at query time, so in DST regions dates near a
    past DST boundary can shift by an hour. Africa/Lagos has no DST; load the
    server tz tables and delete this patch if that ever matters.
    """
    try:
        from django.db.backends.mysql.operations import DatabaseOperations
    except ImportError:
        return

    import datetime
    import zoneinfo

    def _offset(tzname):
        if not tzname or tzname[0] in '+-':
            return tzname
        try:
            tz = zoneinfo.ZoneInfo(tzname)
        except Exception:
            return tzname
        total = int((datetime.datetime.now(tz).utcoffset() or datetime.timedelta()).total_seconds())
        sign = '+' if total >= 0 else '-'
        total = abs(total)
        return '%s%02d:%02d' % (sign, total // 3600, (total % 3600) // 60)

    def _convert_field_to_tz(self, field_name, tzname):
        from django.conf import settings
        if tzname and settings.USE_TZ and self.connection.timezone_name != tzname:
            field_name = "CONVERT_TZ(%s, '%s', '%s')" % (
                field_name,
                _offset(self.connection.timezone_name),
                _offset(self._prepare_tzname_delta(tzname)),
            )
        return field_name

    DatabaseOperations._convert_field_to_tz = _convert_field_to_tz
    logger.info("MySQL CONVERT_TZ patched to use numeric offsets")


# Auto-apply patches when module is imported
if sys.platform == 'win32':
    patch_django_for_windows()

patch_mysql_convert_tz()

