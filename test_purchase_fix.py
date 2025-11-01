#!/usr/bin/env python
"""
Test to verify Purchase model doesn't have updated_by attribute error
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.models import Purchase

def test_purchase_model():
    """Test that Purchase model has correct attributes"""
    print("Testing Purchase model attributes...")
    
    # Get all field names
    field_names = [f.name for f in Purchase._meta.get_fields()]
    print(f"Purchase model fields: {field_names}")
    
    # Check for problematic attributes
    if 'updated_by' in field_names:
        print("ERROR: Purchase model still has 'updated_by' field!")
        return False
    
    if 'updated_at' in field_names:
        print("WARNING: Purchase model has 'updated_at' field (should use 'approval_updated_at')")
    
    # Check for correct attributes
    required_fields = ['created_by', 'approval_updated_at', 'current_approver']
    for field in required_fields:
        if field in field_names:
            print(f"✓ Found required field: {field}")
        else:
            print(f"✗ Missing required field: {field}")
            return False
    
    print("\n✅ Purchase model attribute check passed!")
    return True

if __name__ == '__main__':
    success = test_purchase_model()
    sys.exit(0 if success else 1)
