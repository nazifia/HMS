"""
Environment Variables Loader

This module loads environment variables from a .env file into os.environ.
It's used to configure the application for different environments.
"""

import os
from pathlib import Path

def load_env_file(env_file=None):
    """
    Load environment variables from a .env file.
    
    Args:
        env_file: Path to the .env file. If None, uses the default location.
        
    Returns:
        bool: True if the .env file was loaded successfully, False otherwise.
    """
    if env_file is None:
        # Default location is in the project root
        base_dir = Path(__file__).resolve().parent.parent
        env_file = base_dir / '.env'
    
    if not os.path.exists(env_file):
        return False
    
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse key-value pairs
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                
                # Set environment variable
                os.environ[key] = value
    
    return True
