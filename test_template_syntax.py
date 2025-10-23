#!/usr/bin/env python
"""
Test script to verify template syntax is correct
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from django.template import Template, Context
from django.template.loader import get_template
from django.template.exceptions import TemplateSyntaxError


def test_active_store_template():
    """Test if the active store template has correct syntax"""
    print("Testing active store template syntax...")
    
    try:
        # Try to load and compile the template
        template_path = 'pharmacy/active_store_detail.html'
        template = get_template(template_path)
        print("✓ Template loads successfully")
        
        # Test basic rendering with minimal context
        context = {
            'active_store': {
                'id': 1,
                'name': 'Test Active Store'
            },
            'dispensary': {
                'id': 1,
                'name': 'Test Dispensary'
            },
            'inventory_items': [],
            'bulk_stores': [],
            'available_bulk_medications': [],
            'bulk_transfer_form': None,
            'dispensary_transfer_form': None,
            'pending_dispensary_transfers': [],
            'page_title': 'Test Page'
        }
        
        # Try to render the template
        rendered = template.render(context)
        print("✓ Template renders successfully")
        print(f"✓ Template length: {len(rendered)} characters")
        
        # Check for key elements
        if 'Transfer to Dispensary' in rendered:
            print("✓ Dispensary transfer section found")
        else:
            print("✗ Dispensary transfer section missing")
            return False
            
        if 'id_medication' in rendered:
            print("✓ Medication field ID found")
        else:
            print("✗ Medication field ID missing")
            return False
            
        if 'id_quantity' in rendered:
            print("✓ Quantity field ID found")
        else:
            print("✗ Quantity field ID missing")
            return False
        
        return True
        
    except TemplateSyntaxError as e:
        print(f"✗ TemplateSyntaxError: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("TEMPLATE SYNTAX TEST")
    print("=" * 60)
    
    success = test_active_store_template()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 TEMPLATE SYNTAX TEST PASSED!")
        print("\nThe template should now render correctly.")
    else:
        print("❌ TEMPLATE SYNTAX TEST FAILED!")
        print("Please check the template for syntax errors.")
    print("=" * 60)
