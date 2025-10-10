"""
Custom runserver command that prevents OSError on Windows.
This command wraps Django's runserver with proper encoding handling.
"""

import sys
import os
import io
from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    """
    Custom runserver command with Windows OSError fix.
    """
    
    help = 'Starts the development server with Windows encoding fixes'
    
    def handle(self, *args, **options):
        """
        Override handle to set up proper encoding before starting server.
        """
        # Force UTF-8 encoding on Windows
        if sys.platform == 'win32':
            # Wrap stdout and stderr with UTF-8 encoding
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout = io.TextIOWrapper(
                    sys.stdout.buffer,
                    encoding='utf-8',
                    errors='replace',
                    line_buffering=True
                )
            if hasattr(sys.stderr, 'buffer'):
                sys.stderr = io.TextIOWrapper(
                    sys.stderr.buffer,
                    encoding='utf-8',
                    errors='replace',
                    line_buffering=True
                )
            
            # Set environment variables
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            os.environ['PYTHONUTF8'] = '1'
            
            # Suppress Django's colored output which can cause issues
            options['no_color'] = True
        
        # Call parent's handle method
        try:
            super().handle(*args, **options)
        except OSError as e:
            # If OSError still occurs, log it and continue
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"OSError in runserver: {e}")
            # Try to continue anyway
            pass

