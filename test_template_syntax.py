#!/usr/bin/env python
"""
Test script to verify template syntax fix
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
sys.path.append(r'C:\Users\dell\Desktop\MY_PRODUCTS\HMS')

django.setup()

from django.template import Template, Context
from django.template.loader import get_template
from django.template.exceptions import TemplateSyntaxError

def test_template_syntax():
    """Test that the cart template has valid syntax"""
    
    print("🧪 Testing Template Syntax Fix...")
    
    try:
        # Try to load the template
        template = get_template('pharmacy/cart/view_cart.html')
        print("✅ Template loads successfully!")
        
        # Try to render with dummy context (minimal context)
        dummy_context = {
            'page_title': 'Test Cart',
            'cart': None,
            'dispensaries': [],
            'subtotal': '0.00',
            'patient_payable': '0.00',
            'nhia_coverage': '0.00',
            'can_checkout': True,
            'checkout_message': 'Test message',
            'is_nhia_patient': False,
            'payment_details': [],
            'active_nav': 'pharmacy',
        }
        
        # This will test if the template compiles without syntax errors
        rendered = template.render(dummy_context)
        print("✅ Template renders successfully!")
        print(f"📄 Rendered length: {len(rendered)} characters")
        
        # Check for specific content that should be present
        if 'cart-header' in rendered:
            print("✅ Header section found")
        
        if 'payment-status' in rendered:
            print("✅ Payment status section found")
            
        if 'items-table' in rendered:
            print("✅ Items table section found")
            
        if 'summary-card' in rendered:
            print("✅ Summary card section found")
            
        print("🎉 Template syntax test passed!")
        return True
        
    except TemplateSyntaxError as e:
        print(f"❌ Template Syntax Error: {e}")
        print(f"📍 Line {e.lineno}: {e.message}")
        return False
    except Exception as e:
        print(f"❌ Template Error: {str(e)}")
        return False

if __name__ == '__main__':
    success = test_template_syntax()
    if success:
        print("\n📝 The template syntax fix is working correctly!")
        print("🌐 You can now access the cart view at: http://127.0.0.1:8000/pharmacy/cart/14/")
    else:
        print("\n❌ There are still template syntax issues to fix.")
