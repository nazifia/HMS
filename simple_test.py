#!/usr/bin/env python
import os
import sys

# Add the project directory to the Python path
sys.path.append(r'c:\Users\dell\Desktop\MY_PRODUCTS\HMS')

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

def test_imports():
    """Test that our modules can be imported correctly"""
    try:
        import django
        django.setup()
        print("Django setup successful")
        
        # Test importing our modified modules
        from pharmacy.views import dispense_prescription, get_stock_quantities
        print("Views imported successfully")
        
        from pharmacy.forms import DispenseItemForm
        print("Forms imported successfully")
        
        print("All imports successful!")
        return True
    except Exception as e:
        print(f"Import error: {e}")
        return False

if __name__ == '__main__':
    test_imports()