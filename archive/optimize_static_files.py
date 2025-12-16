#!/usr/bin/env python
"""
Static File Optimization Script
"""
import os
import gzip
import shutil
from pathlib import Path

def compress_static_files():
    """Compress static files for better performance"""
    static_dir = Path('static')
    if not static_dir.exists():
        return
    
    for file_path in static_dir.rglob('*'):
        if file_path.suffix in ['.css', '.js', '.html']:
            compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

if __name__ == "__main__":
    compress_static_files()
