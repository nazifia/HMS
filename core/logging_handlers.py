"""
Custom logging handlers for HMS Application.
Provides Windows-safe logging handlers that avoid OSError [Errno 22] Invalid argument.
"""

import logging
import logging.handlers
import sys
import codecs


class SafeStreamHandler(logging.StreamHandler):
    """
    A StreamHandler that handles encoding errors gracefully on Windows.
    This prevents OSError [Errno 22] Invalid argument when logging Unicode characters.
    """
    
    def __init__(self, stream=None):
        super().__init__(stream)
        # Ensure the stream can handle Unicode
        if stream is None:
            stream = sys.stderr
        
        # Wrap the stream with a writer that handles encoding errors
        if hasattr(stream, 'buffer'):
            # For Python 3, wrap the binary buffer with UTF-8 encoding
            self.stream = codecs.getwriter('utf-8')(
                stream.buffer, 
                errors='replace'  # Replace unencodable characters instead of crashing
            )
        else:
            self.stream = stream
    
    def emit(self, record):
        """
        Emit a record with error handling for encoding issues.
        """
        try:
            msg = self.format(record)
            stream = self.stream
            # Ensure the message is a string
            if not isinstance(msg, str):
                msg = str(msg)
            
            # Write with error handling
            try:
                stream.write(msg + self.terminator)
            except UnicodeEncodeError:
                # If encoding fails, try with ASCII and replace non-ASCII characters
                msg_ascii = msg.encode('ascii', errors='replace').decode('ascii')
                stream.write(msg_ascii + self.terminator)
            except OSError:
                # If OSError occurs (Windows console issue), silently ignore
                pass
            
            self.flush()
        except Exception:
            self.handleError(record)


class WindowsSafeFileHandler(logging.handlers.RotatingFileHandler):
    """
    A RotatingFileHandler that ensures UTF-8 encoding on Windows.
    """
    
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, 
                 encoding='utf-8', delay=False):
        # Always use UTF-8 encoding
        super().__init__(
            filename, 
            mode=mode, 
            maxBytes=maxBytes, 
            backupCount=backupCount,
            encoding='utf-8',  # Force UTF-8
            delay=delay
        )

