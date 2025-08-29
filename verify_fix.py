#!/usr/bin/env python
"""
Simple verification script to check if the active_store_detail function is correct
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Import the function
from pharmacy.views import active_store_detail

# Check the function
print("Function name:", active_store_detail.__name__)
print("Function docstring:", active_store_detail.__doc__)

# Read the source code to verify it includes inventory_items
import inspect
source = inspect.getsource(active_store_detail)
if 'inventory_items' in source:
    print("✅ Function includes inventory_items - this is the correct version!")
else:
    print("❌ Function does not include inventory_items - this is the incomplete version!")

print("\nFirst 10 lines of function:")
for i, line in enumerate(source.split('\n')[:10]):
    print(f"{i+1:2}: {line}")