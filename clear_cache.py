#!/usr/bin/env python
"""
Clear Python cache files
"""
import os
import shutil

def clear_cache():
    """Clear Python cache files"""
    cleared = 0
    
    # Clear __pycache__ directories
    for root, dirs, files in os.walk('.'):
        for d in dirs:
            if d == '__pycache__':
                cache_path = os.path.join(root, d)
                try:
                    shutil.rmtree(cache_path)
                    cleared += 1
                    print(f"Removed: {cache_path}")
                except Exception as e:
                    print(f"Failed to remove {cache_path}: {e}")
    
    # Clear .pyc files
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f.endswith('.pyc'):
                pyc_path = os.path.join(root, f)
                try:
                    os.remove(pyc_path)
                    cleared += 1
                    print(f"Removed: {pyc_path}")
                except Exception as e:
                    print(f"Failed to remove {pyc_path}: {e}")
    
    print(f"\nCleared {cleared} cache items")
    return cleared > 0

if __name__ == '__main__':
    clear_cache()
