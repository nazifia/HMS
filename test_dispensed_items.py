#!/usr/bin/env python
"""
Simple test script to verify the dispensed items functionality
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_imports():
    """Test that all imports work correctly"""
    try:
        from pharmacy.models import DispensingLog, Dispensary, Medication, MedicationCategory
        from pharmacy.forms import DispensedItemsSearchForm
        from pharmacy.views import dispensed_items_tracker, dispensed_item_detail, dispensed_items_export
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_model_structure():
    """Test that models have the expected fields"""
    try:
        from pharmacy.models import DispensingLog
        
        # Check if DispensingLog has the dispensary field
        fields = [field.name for field in DispensingLog._meta.fields]
        expected_fields = [
            'prescription_item', 'dispensed_by', 'dispensed_quantity', 
            'dispensed_date', 'unit_price_at_dispense', 'total_price_for_this_log',
            'dispensary', 'created_at'
        ]
        
        missing_fields = [field for field in expected_fields if field not in fields]
        if missing_fields:
            print(f"✗ Missing fields in DispensingLog: {missing_fields}")
            return False
        
        print("✓ DispensingLog model structure is correct")
        return True
    except Exception as e:
        print(f"✗ Model structure test failed: {e}")
        return False

def test_form_structure():
    """Test that the search form has all expected fields"""
    try:
        from pharmacy.forms import DispensedItemsSearchForm
        
        form = DispensedItemsSearchForm()
        expected_fields = [
            'medication_name', 'date_from', 'date_to', 'patient_name',
            'dispensed_by', 'category', 'min_quantity', 'max_quantity',
            'prescription_type'
        ]
        
        form_fields = list(form.fields.keys())
        missing_fields = [field for field in expected_fields if field not in form_fields]
        
        if missing_fields:
            print(f"✗ Missing fields in DispensedItemsSearchForm: {missing_fields}")
            return False
        
        print("✓ DispensedItemsSearchForm structure is correct")
        return True
    except Exception as e:
        print(f"✗ Form structure test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Dispensed Items Implementation...")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_model_structure,
        test_form_structure,
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✓ All tests passed ({passed}/{total})")
        print("The dispensed items functionality is ready to use!")
    else:
        print(f"✗ Some tests failed ({passed}/{total})")
        print("Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)