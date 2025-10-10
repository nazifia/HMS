"""
Authentication wrapper to handle Windows OSError [Errno 22] Invalid argument.
This module provides a safe wrapper around Django's authenticate function.
"""

import sys
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def suppress_console_output():
    """
    Context manager to suppress all console output (stdout/stderr).
    This prevents OSError [Errno 22] on Windows when Unicode characters
    are written to the console.
    """
    # Save original stdout and stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    try:
        # Redirect to null device (NUL on Windows, /dev/null on Unix)
        null_device = open(os.devnull, 'w', encoding='utf-8')
        sys.stdout = null_device
        sys.stderr = null_device
        
        yield
        
    finally:
        # Restore original stdout and stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        try:
            null_device.close()
        except:
            pass


def safe_authenticate(request, username=None, password=None, **kwargs):
    """
    Safely authenticate a user without risking OSError on Windows.
    
    This function wraps Django's authenticate() to prevent console encoding
    errors that can occur on Windows when logging contains Unicode characters.
    
    Args:
        request: The HTTP request object
        username: Username or phone number
        password: User's password
        **kwargs: Additional authentication parameters
        
    Returns:
        User object if authentication successful, None otherwise
    """
    try:
        # Import here to avoid circular imports
        from django.contrib.auth import authenticate as django_authenticate
        
        # Try authentication with console output suppressed
        with suppress_console_output():
            user = django_authenticate(
                request=request,
                username=username,
                password=password,
                **kwargs
            )
        
        return user
        
    except OSError as e:
        # Log the error to file (not console)
        logger.error(f"OSError during authentication: {e}", exc_info=True)
        logger.error(f"Username: {username}, Request path: {request.path if request else 'N/A'}")
        
        # Try again without request object (might help in some cases)
        try:
            from django.contrib.auth import authenticate as django_authenticate
            with suppress_console_output():
                user = django_authenticate(
                    username=username,
                    password=password,
                    **kwargs
                )
            return user
        except Exception as retry_error:
            logger.error(f"Retry authentication also failed: {retry_error}", exc_info=True)
            return None
            
    except Exception as e:
        # Log any other unexpected errors
        logger.error(f"Unexpected error during authentication: {e}", exc_info=True)
        return None

