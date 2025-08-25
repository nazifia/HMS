#!/usr/bin/env python
"""
Test the simplified revenue template
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_simplified_template():
    """Test the simplified revenue template"""
    print("🔍 Testing Simplified Revenue Template...")
    
    try:
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        
        # Create a request
        factory = RequestFactory()
        request = factory.get('/pharmacy/revenue/statistics/')
        
        # Context
        context = {
            'request': request,
            'title': 'Comprehensive Revenue Analysis',
            'page_title': 'Comprehensive Revenue Analysis',
            'total_revenue': 1000.00,
        }
        
        print("📋 Rendering simplified revenue template...")
        rendered = render_to_string('pharmacy/comprehensive_revenue_simple.html', context, request=request)
        print(f"✅ Simplified template rendered: {len(rendered)} characters")
        
        if len(rendered) > 0:
            # Save for inspection
            with open('simplified_revenue_test.html', 'w', encoding='utf-8') as f:
                f.write(rendered)
            print("💾 Rendered template saved to 'simplified_revenue_test.html'")
            
            # Check for key content
            if 'DEBUG: Template is working!' in rendered:
                print("✅ Simplified template is working correctly!")
                return True
            else:
                print("❌ Simplified template missing debug content")
                return False
        else:
            print("❌ Simplified template rendered but is empty")
            return False
            
    except Exception as e:
        print(f"❌ Simplified template test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Simplified Template Test")
    print("="*50)
    
    # Run test
    result = test_simplified_template()
    
    print("\n" + "="*50)
    print("📝 SIMPLIFIED TEMPLATE TEST SUMMARY:")
    print(f"Test Result: {'✅ PASSED' if result else '❌ FAILED'}")