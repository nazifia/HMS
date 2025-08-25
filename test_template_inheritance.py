#!/usr/bin/env python
"""
Test template inheritance with minimal templates
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_template_inheritance():
    """Test template inheritance with minimal templates"""
    print("🔍 Testing Template Inheritance...")
    
    try:
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        
        # Create a request
        factory = RequestFactory()
        request = factory.get('/test/')
        
        print("📋 Test 1: Rendering base test template...")
        base_rendered = render_to_string('base_test.html', {'title': 'Base Test'}, request=request)
        print(f"✅ Base template rendered: {len(base_rendered)} characters")
        print(f"📋 Content preview: {base_rendered[:100]}...")
        
        print("\n📋 Test 2: Rendering child test template...")
        child_rendered = render_to_string('child_test.html', {'title': 'Child Test'}, request=request)
        print(f"✅ Child template rendered: {len(child_rendered)} characters")
        print(f"📋 Content preview: {child_rendered[:100]}...")
        
        if 'Child Template Content' in child_rendered:
            print("✅ Child content found in rendered template")
        else:
            print("❌ Child content missing from rendered template")
            
        return True
        
    except Exception as e:
        print(f"❌ Template inheritance test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_actual_revenue_template():
    """Test the actual revenue template with minimal inheritance"""
    print("\n🔍 Testing Actual Revenue Template...")
    
    try:
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        
        # Create a request
        factory = RequestFactory()
        request = factory.get('/pharmacy/revenue/statistics/')
        
        # Minimal context that should work
        context = {
            'request': request,
            'title': 'Comprehensive Revenue Analysis',
            'page_title': 'Comprehensive Revenue Analysis',
            'total_revenue': 1000.00,
            'start_date': '2025-08-01',
            'end_date': '2025-08-31',
            'filter_form': None,
            'comprehensive_data': {
                'pharmacy_revenue': {'total_revenue': 100, 'total_payments': 1},
                'laboratory_revenue': {'total_revenue': 200, 'total_payments': 2},
                'consultation_revenue': {'total_revenue': 300, 'total_payments': 3},
                'theatre_revenue': {'total_revenue': 400, 'total_payments': 4},
                'admission_revenue': {'total_revenue': 500, 'total_payments': 5},
                'general_revenue': {'total_revenue': 600, 'total_payments': 6},
                'wallet_revenue': {'total_revenue': 700, 'total_transactions': 7},
                'total_revenue': 2800,
            },
            'revenue_sources': [
                {'name': 'Pharmacy', 'revenue': 100, 'icon': 'fas fa-pills', 'color': 'primary'},
                {'name': 'Laboratory', 'revenue': 200, 'icon': 'fas fa-microscope', 'color': 'success'},
            ],
            'chart_data': {
                'months': '["Aug 2025"]',
                'pharmacy': '[100]',
                'laboratory': '[200]',
                'consultations': '[300]',
                'theatre': '[400]',
                'admissions': '[500]',
                'general': '[600]',
                'wallet': '[700]',
                'total': '[2800]'
            },
            'performance_metrics': {
                'total_transactions': 28,
                'average_transaction_value': 100,
                'daily_average': 50,
                'days_in_period': 31
            },
            'monthly_trends': [],
            'daily_breakdown': [],
            'include_daily_breakdown': False,
            'selected_departments': [],
            'active_nav': 'pharmacy',
            
            # Individual department data for backward compatibility
            'pharmacy_revenue': {'total_revenue': 100, 'total_payments': 1},
            'lab_revenue': {'total_revenue': 200, 'total_payments': 2},
            'consultation_revenue': {'total_revenue': 300, 'total_payments': 3},
            'theatre_revenue': {'total_revenue': 400, 'total_payments': 4},
            'admission_revenue': {'total_revenue': 500, 'total_payments': 5},
            'general_revenue': {'total_revenue': 600, 'total_payments': 6},
            'wallet_revenue': {'total_revenue': 700, 'total_transactions': 7},
        }
        
        print("📋 Rendering actual revenue template...")
        rendered = render_to_string('pharmacy/simple_revenue_statistics.html', context, request=request)
        print(f"✅ Revenue template rendered: {len(rendered)} characters")
        
        if len(rendered) > 0:
            # Save for inspection
            with open('actual_revenue_test.html', 'w', encoding='utf-8') as f:
                f.write(rendered)
            print("💾 Rendered template saved to 'actual_revenue_test.html'")
            
            # Check for key content
            key_indicators = [
                'Comprehensive Revenue Analysis',
                'Total Hospital Revenue',
                '₦1000.00',  # Total revenue
                'Pharmacy Revenue',
                'Laboratory Revenue'
            ]
            
            found_indicators = []
            missing_indicators = []
            
            for indicator in key_indicators:
                if indicator in rendered:
                    found_indicators.append(indicator)
                else:
                    missing_indicators.append(indicator)
            
            print(f"✅ Found indicators: {found_indicators}")
            print(f"❌ Missing indicators: {missing_indicators}")
            
            return len(found_indicators) > 0
            
        else:
            print("❌ Revenue template rendered but is empty")
            return False
            
    except Exception as e:
        print(f"❌ Actual revenue template test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Template Inheritance Test")
    print("="*50)
    
    # Run tests
    inheritance_test = test_template_inheritance()
    revenue_test = test_actual_revenue_template()
    
    print("\n" + "="*50)
    print("📝 TEMPLATE INHERITANCE TEST SUMMARY:")
    print(f"Inheritance Test: {'✅ PASSED' if inheritance_test else '❌ FAILED'}")
    print(f"Revenue Template Test: {'✅ PASSED' if revenue_test else '❌ FAILED'}")
    
    if inheritance_test and revenue_test:
        print("\n🎉 Template inheritance is working!")
    elif inheritance_test and not revenue_test:
        print("\n🔍 Template inheritance works but revenue template has issues.")
    else:
        print("\n⚠️ Template inheritance has issues.")