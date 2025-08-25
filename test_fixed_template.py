#!/usr/bin/env python
"""
Test the fixed revenue template
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_fixed_template():
    """Test the fixed revenue template"""
    print("🔍 Testing Fixed Revenue Template...")
    
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
        
        print("📋 Rendering fixed revenue template...")
        rendered = render_to_string('pharmacy/simple_revenue_statistics.html', context, request=request)
        print(f"✅ Fixed template rendered: {len(rendered)} characters")
        
        if len(rendered) > 0:
            # Save for inspection
            with open('fixed_revenue_test.html', 'w', encoding='utf-8') as f:
                f.write(rendered)
            print("💾 Rendered template saved to 'fixed_revenue_test.html'")
            
            # Check for key content
            key_indicators = [
                'Comprehensive Hospital Revenue Analysis',
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
            print("❌ Fixed template rendered but is empty")
            return False
            
    except Exception as e:
        print(f"❌ Fixed template test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Fixed Template Test")
    print("="*50)
    
    # Run test
    result = test_fixed_template()
    
    print("\n" + "="*50)
    print("📝 FIXED TEMPLATE TEST SUMMARY:")
    print(f"Test Result: {'✅ PASSED' if result else '❌ FAILED'}")