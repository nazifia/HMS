#!/usr/bin/env python
"""
Simple verification that the transfer button issues have been fixed
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def verify_view_function():
    """Verify that the active_store_detail view function is correct"""
    print("🔍 Verifying active_store_detail view function...")
    
    try:
        from pharmacy.views import active_store_detail
        
        # Check function name and docstring
        print(f"   Function name: {active_store_detail.__name__}")
        print(f"   Docstring: {active_store_detail.__doc__}")
        
        # Read the source code to verify it includes inventory_items
        import inspect
        source = inspect.getsource(active_store_detail)
        
        if 'inventory_items' in source:
            print("   ✅ Function includes inventory_items - this is the correct version!")
            return True
        else:
            print("   ❌ Function does not include inventory_items - this is the incomplete version!")
            return False
            
    except Exception as e:
        print(f"   ❌ Error checking view function: {str(e)}")
        return False

def verify_template_structure():
    """Verify that the template has the correct structure"""
    print("\n🔍 Verifying template structure...")
    
    template_path = 'pharmacy/templates/pharmacy/active_store_detail.html'
    full_path = os.path.join(os.getcwd(), template_path)
    
    if not os.path.exists(full_path):
        print(f"   ❌ Template not found at {full_path}")
        return False
    
    try:
        with open(full_path, 'r') as f:
            content = f.read()
        
        # Check for required elements
        required_elements = [
            'transfer-btn',
            'data-medication=',
            'data-medication-name=',
            'data-batch=',
            'data-quantity=',
            'transferModal',
            'medicationId',
            'medicationName',
            'batchNumber',
            'availableQuantity',
            'transferQuantity'
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"   ❌ Missing elements in template: {missing_elements}")
            return False
        else:
            print("   ✅ All required template elements found")
            return True
            
    except Exception as e:
        print(f"   ❌ Error reading template: {str(e)}")
        return False

def verify_javascript_inclusion():
    """Verify that required JavaScript libraries are included"""
    print("\n🔍 Verifying JavaScript library inclusion...")
    
    base_template_path = 'templates/base.html'
    full_path = os.path.join(os.getcwd(), base_template_path)
    
    if not os.path.exists(full_path):
        print(f"   ❌ Base template not found at {full_path}")
        return False
    
    try:
        with open(full_path, 'r') as f:
            content = f.read()
        
        # Check for required JavaScript libraries
        required_js = [
            'jquery-3.6.0.min.js',
            'bootstrap.bundle.min.js'
        ]
        
        missing_js = []
        for js in required_js:
            if js not in content:
                missing_js.append(js)
        
        if missing_js:
            print(f"   ❌ Missing JavaScript libraries: {missing_js}")
            return False
        else:
            print("   ✅ All required JavaScript libraries found")
            # Check order (jQuery should come before Bootstrap)
            jquery_pos = content.find('jquery-3.6.0.min.js')
            bootstrap_pos = content.find('bootstrap.bundle.min.js')
            
            if jquery_pos < bootstrap_pos:
                print("   ✅ JavaScript libraries in correct order (jQuery before Bootstrap)")
                return True
            else:
                print("   ❌ JavaScript libraries in wrong order (Bootstrap before jQuery)")
                return False
                
    except Exception as e:
        print(f"   ❌ Error reading base template: {str(e)}")
        return False

def verify_no_duplicate_functions():
    """Verify that there are no duplicate active_store_detail functions"""
    print("\n🔍 Verifying no duplicate functions...")
    
    views_path = 'pharmacy/views.py'
    full_path = os.path.join(os.getcwd(), views_path)
    
    if not os.path.exists(full_path):
        print(f"   ❌ Views file not found at {full_path}")
        return False
    
    try:
        with open(full_path, 'r') as f:
            content = f.read()
        
        # Count occurrences of the function definition
        count = content.count('def active_store_detail(')
        
        if count == 1:
            print("   ✅ Exactly one active_store_detail function found")
            return True
        elif count == 0:
            print("   ❌ No active_store_detail function found")
            return False
        else:
            print(f"   ❌ Found {count} active_store_detail functions (should be 1)")
            return False
            
    except Exception as e:
        print(f"   ❌ Error reading views file: {str(e)}")
        return False

def main():
    """Main verification function"""
    print("🧪 Simple Verification of Transfer Button Fixes")
    print("=" * 50)
    
    # Run all verification tests
    test1 = verify_view_function()
    test2 = verify_template_structure()
    test3 = verify_javascript_inclusion()
    test4 = verify_no_duplicate_functions()
    
    print("\n" + "=" * 50)
    print("📋 VERIFICATION RESULTS:")
    print("=" * 50)
    
    if test1:
        print("✅ Active store detail view function is correct")
    else:
        print("❌ Active store detail view function has issues")
        
    if test2:
        print("✅ Template structure is correct")
    else:
        print("❌ Template structure has issues")
        
    if test3:
        print("✅ JavaScript libraries are properly included")
    else:
        print("❌ JavaScript libraries have issues")
        
    if test4:
        print("✅ No duplicate functions found")
    else:
        print("❌ Duplicate functions detected")
    
    if test1 and test2 and test3 and test4:
        print("\n🎉 ALL TESTS PASSED!")
        print("The transfer button functionality should now be working correctly.")
        print("\n🔧 Summary of fixes applied:")
        print("   1. Removed duplicate incomplete active_store_detail function")
        print("   2. Ensured inventory_items are properly passed to template context")
        print("   3. Fixed JavaScript library loading order")
        print("   4. Verified template structure for transfer buttons")
        return True
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("There may still be issues with the transfer functionality.")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)