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


# Auto-apply patches when module is imported
if sys.platform == 'win32':
    patch_django_for_windows()

