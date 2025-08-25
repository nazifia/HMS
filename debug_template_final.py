#!/usr/bin/env python
"""
Final template debugging script with proper Django methods
"""

import os
import sys
import django
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_template_rendering():
    """Test template rendering with proper Django methods"""
    print("🔍 Testing Template Rendering with Proper Methods...")
    
    try:
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        from django.contrib.auth import get_user_model
        
        # Create a proper request context
        factory = RequestFactory()
        request = factory.get('/test/')
        
        # Basic minimal context
        minimal_context = {
            'request': request,
            'title': 'Test Revenue Analysis',
            'page_title': 'Test Revenue Analysis',
            'total_revenue': 1000.00,
            'start_date': date.today(),
            'end_date': date.today(),
            'filter_form': None,
            'comprehensive_data': {
                'pharmacy_revenue': {'total_revenue': 100, 'total_payments': 1, 'total_prescriptions': 1, 'total_medications_dispensed': 1},
                'laboratory_revenue': {'total_revenue': 200, 'total_payments': 2, 'total_tests': 2},
                'consultation_revenue': {'total_revenue': 300, 'total_payments': 3, 'total_consultations': 3},
                'theatre_revenue': {'total_revenue': 400, 'total_payments': 4, 'total_surgeries': 4},
                'admission_revenue': {'total_revenue': 500, 'total_payments': 5, 'total_admissions': 5},
                'general_revenue': {'total_revenue': 600, 'total_payments': 6},
                'wallet_revenue': {'total_revenue': 700, 'total_transactions': 7},
            },
            'revenue_sources': [
                {'name': 'Pharmacy', 'revenue': 100, 'icon': 'fas fa-pills', 'color': 'primary'},
                {'name': 'Laboratory', 'revenue': 200, 'icon': 'fas fa-microscope', 'color': 'success'},
            ],
            'chart_data': {
                'months': '["Jan 2025"]',
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
                'days_in_period': 30
            },
            'monthly_trends': [],
            'daily_breakdown': [],
            'include_daily_breakdown': False,
            'selected_departments': [],
            'active_nav': 'pharmacy',
            
            # Individual department data for backward compatibility
            'pharmacy_revenue': {'total_revenue': 100, 'total_payments': 1, 'total_prescriptions': 1, 'total_medications_dispensed': 1},
            'lab_revenue': {'total_revenue': 200, 'total_payments': 2, 'total_tests': 2},
            'consultation_revenue': {'total_revenue': 300, 'total_payments': 3, 'total_consultations': 3},
            'theatre_revenue': {'total_revenue': 400, 'total_payments': 4, 'total_surgeries': 4},
            'admission_revenue': {'total_revenue': 500, 'total_payments': 5, 'total_admissions': 5},
            'general_revenue': {'total_revenue': 600, 'total_payments': 6},
            'wallet_revenue': {'total_revenue': 700, 'total_transactions': 7},
        }
        
        print("📋 Test 1: Rendering with minimal context...")
        try:
            rendered = render_to_string('pharmacy/simple_revenue_statistics.html', minimal_context, request=request)
            print(f"✅ Template rendered successfully: {len(rendered)} characters")
            
            if len(rendered) > 0:
                # Save sample for inspection
                with open('final_template_test.html', 'w', encoding='utf-8') as f:
                    f.write(rendered)
                print("💾 Rendered template saved to 'final_template_test.html'")
                
                # Check if basic content is present
                if 'Revenue Analysis' in rendered:
                    print("✅ Basic content found in template")
                else:
                    print("❌ Basic content missing from template")
                    
                return True
            else:
                print("❌ Template rendered but is empty")
                return False
                
        except Exception as render_error:
            print(f"❌ Template rendering error: {render_error}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ Template test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_view_directly_with_logging():
    """Test the view directly with detailed logging"""
    print("\n🔍 Testing View Directly with Detailed Logging...")
    
    try:
        from django.test import RequestFactory
        from django.contrib.auth import get_user_model
        import logging
        
        # Enable Django template debugging
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger('django.template')
        logger.setLevel(logging.DEBUG)
        
        # Create request and user
        factory = RequestFactory()
        request = factory.get('/pharmacy/revenue/statistics/')
        
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@test.com', 'is_staff': True, 'is_superuser': True}
        )
        request.user = user
        
        # Import and call the view
        from pharmacy.views import simple_revenue_statistics as comprehensive_revenue_analysis
        
        print("📊 Calling view function...")
        response = comprehensive_revenue_analysis(request)
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Response content length: {len(response.content)} bytes")
        
        if response.status_code == 200:
            if len(response.content) > 0:
                print("✅ View returned content successfully!")
                
                # Save the actual response
                with open('view_response_output.html', 'wb') as f:
                    f.write(response.content)
                print("💾 View response saved to 'view_response_output.html'")
                
                return True
            else:
                print("❌ View returned empty content")
                
                # Check if it's a template issue or data issue
                print("📋 Checking if this is a template or data issue...")
                
                # Try to manually render with same logic as view
                from pharmacy.revenue_service import RevenueAggregationService, MonthFilterHelper
                import json
                
                # Get default data like the view does
                start_date, end_date = MonthFilterHelper.get_current_month()
                revenue_service = RevenueAggregationService(start_date, end_date)
                comprehensive_data = revenue_service.get_comprehensive_revenue()
                
                print(f"📊 Service total revenue: {comprehensive_data['total_revenue']}")
                
                return False
        else:
            print(f"❌ View returned error status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ View test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_pharmacy_tags():
    """Check if pharmacy_tags are working correctly"""
    print("\n🔍 Checking Pharmacy Template Tags...")
    
    try:
        from django.template.loader import render_to_string
        
        # Test a simple template with pharmacy_tags
        test_template = """
        {% load pharmacy_tags %}
        <h1>Template Tags Test</h1>
        <p>Test successful</p>
        """
        
        # Write temporary template
        temp_template_path = 'templates/test_pharmacy_tags.html'
        os.makedirs(os.path.dirname(temp_template_path), exist_ok=True)
        
        with open(temp_template_path, 'w') as f:
            f.write(test_template)
        
        try:
            rendered = render_to_string('test_pharmacy_tags.html', {})
            print(f"✅ Pharmacy tags template rendered: {len(rendered)} characters")
            print(f"📋 Content: {rendered.strip()}")
            
            # Clean up
            os.remove(temp_template_path)
            
            return True
            
        except Exception as tag_error:
            print(f"❌ Pharmacy tags error: {tag_error}")
            # Clean up
            if os.path.exists(temp_template_path):
                os.remove(temp_template_path)
            return False
        
    except Exception as e:
        print(f"❌ Template tags check error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Final Template Debugging Script")
    print("="*60)
    
    # Run final tests
    tag_test = check_pharmacy_tags()
    template_test = test_template_rendering()
    view_test = test_view_directly_with_logging()
    
    print("\n" + "="*60)
    print("📝 FINAL DEBUG SUMMARY:")
    print(f"Tag Test: {'✅ PASSED' if tag_test else '❌ FAILED'}")
    print(f"Template Test: {'✅ PASSED' if template_test else '❌ FAILED'}")
    print(f"View Test: {'✅ PASSED' if view_test else '❌ FAILED'}")
    
    if template_test and view_test:
        print("\n🎉 Template and view are working! The issue might be elsewhere.")
    elif template_test and not view_test:
        print("\n🔍 Template works but view doesn't. Check view logic.")
    else:
        print("\n⚠️ Template has issues. Check template syntax and context.")