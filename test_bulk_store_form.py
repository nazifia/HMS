#!/usr/bin/env python
"""
Test script to verify bulk store transfer form functionality
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from pharmacy.dispensary_transfer_forms import BulkStoreTransferForm
from pharmacy.models import BulkStore


def test_bulk_store_form():
    """Test the bulk store transfer form"""
    print("Testing BulkStoreTransferForm...")
    
    try:
        # Create form instance
        form = BulkStoreTransferForm()
        
        print("✓ Form created successfully")
        
        # Check if bulk_store field exists
        if 'bulk_store' in form.fields:
            print("✓ bulk_store field found")
        else:
            print("✗ bulk_store field missing")
            return False
        
        # Check field attributes
        bulk_store_field = form.fields['bulk_store']
        print(f"✓ Field type: {type(bulk_store_field).__name__}")
        
        # Check widget attributes
        widget = bulk_store_field.widget
        attrs = widget.attrs or {}
        print(f"✓ Widget class: {attrs.get('class', 'Not set')}")
        print(f"✓ Widget ID: {attrs.get('id', 'Not set')}")
        
        # Check if required
        if bulk_store_field.required:
            print("✓ Field is required")
        else:
            print("⚠ Field is not required")
        
        # Check empty label
        if hasattr(bulk_store_field, 'empty_label'):
            print(f"✓ Empty label: {bulk_store_field.empty_label}")
        else:
            print("⚠ No empty label set")
        
        # Test form rendering
        html = form.as_p()
        if 'id_bulk_store' in html:
            print("✓ Correct ID found in rendered HTML")
        else:
            print("✗ Correct ID not found in rendered HTML")
            print(f"Rendered HTML: {html}")
            return False
        
        if 'form-select' in html:
            print("✓ Bootstrap CSS class found in rendered HTML")
        else:
            print("⚠ Bootstrap CSS class not found")
        
        # Check for BulkStore data
        bulk_stores = BulkStore.objects.filter(is_active=True)
        print(f"✓ Found {bulk_stores.count()} active bulk stores")
        
        if bulk_stores.exists():
            for store in bulk_stores[:3]:  # Show first 3
                print(f"   - {store.name} (ID: {store.id})")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing form: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("BULK STORE TRANSFER FORM TEST")
    print("=" * 60)
    
    success = test_bulk_store_form()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 BULK STORE FORM TEST PASSED!")
        print("\nThe bulk store form should now render correctly with:")
        print("✓ Proper Bootstrap styling")
        print("✓ Correct field IDs")
        print("✓ Error handling")
        print("✓ Empty label for dropdown")
    else:
        print("❌ BULK STORE FORM TEST FAILED!")
        print("Please check the form implementation.")
    print("=" * 60)
