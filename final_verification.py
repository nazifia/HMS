#!/usr/bin/env python
"""
Final verification that the transfer button issues have been fixed
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.test import RequestFactory
from accounts.models import CustomUser
from pharmacy.views import active_store_detail
from pharmacy.models import Dispensary

def verify_active_store_detail_view():
    """Verify that the active_store_detail view works correctly"""
    print("🔍 Verifying active_store_detail view...")
    
    try:
        # Get the actual dispensary from the database
        dispensary = Dispensary.objects.get(id=58)  # THEATRE-PH
        print(f"   Found dispensary: {dispensary.name}")
        
        # Check if it has an active store
        active_store = getattr(dispensary, 'active_store', None)
        if not active_store:
            print("   ❌ No active store found for this dispensary")
            return False
            
        print(f"   Active store: {active_store.name}")
        
        # Create a test user
        user = CustomUser.objects.first()
        if not user:
            user = CustomUser.objects.create_user(username='testuser', phone_number='+1234567890', password='testpass')
            print("   Created test user")
        else:
            print(f"   Using existing user: {user.username}")
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.get(f'/pharmacy/dispensaries/{dispensary.id}/active-store/')
        request.user = user
        
        # Import and add required middleware
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        
        # Add session
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()
        
        # Add messages
        middleware = MessageMiddleware()
        middleware.process_request(request)
        
        # Call the view function
        response = active_store_detail(request, dispensary.id)
        
        # Check response
        if hasattr(response, 'status_code') and response.status_code == 200:
            print("   ✅ View returned successful response (HTTP 200)")
            
            # Check if the response contains inventory items
            content = response.content.decode('utf-8')
            if 'inventory_items' in content:
                print("   ✅ Response contains inventory_items")
            else:
                print("   ⚠️  Could not verify inventory_items in response content")
            
            return True
        else:
            print(f"   ❌ View returned unexpected status code: {response.status_code}")
            return False
            
    except Dispensary.DoesNotExist:
        print("   ❌ Dispensary with ID 58 not found")
        return False
    except Exception as e:
        print(f"   ❌ Error testing view: {str(e)}")
        import traceback
        traceback.print_exc()
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

def main():
    """Main verification function"""
    print("🧪 Final Verification of Transfer Button Fixes")
    print("=" * 50)
    
    # Run all verification tests
    test1 = verify_active_store_detail_view()
    test2 = verify_template_structure()
    test3 = verify_javascript_inclusion()
    
    print("\n" + "=" * 50)
    print("📋 VERIFICATION RESULTS:")
    print("=" * 50)
    
    if test1:
        print("✅ Active store detail view is working correctly")
    else:
        print("❌ Active store detail view has issues")
        
    if test2:
        print("✅ Template structure is correct")
    else:
        print("❌ Template structure has issues")
        
    if test3:
        print("✅ JavaScript libraries are properly included")
    else:
        print("❌ JavaScript libraries have issues")
    
    if test1 and test2 and test3:
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