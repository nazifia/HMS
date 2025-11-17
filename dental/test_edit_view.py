#!/usr/bin/env python
# Test to check if edit_dental_record view exists
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dental.views import edit_dental_record
    print("SUCCESS: edit_dental_record function found and importable")
except ImportError as e:
    print(f"ERROR: Could not import edit_dental_record: {e}")
except Exception as e:
    print(f"ERROR: Unexpected error: {e}")
