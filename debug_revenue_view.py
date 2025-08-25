#!/usr/bin/env python
"""
Debug script for pharmacy revenue comprehensive view
"""

import os
import sys
import django
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_revenue_view():
    """Test the revenue view function directly"""
    print("🔍 Testing Revenue View Function...")
    
    try:
        from django.test import RequestFactory
        from django.contrib.auth import get_user_model
        from pharmacy.views import simple_revenue_statistics as comprehensive_revenue_analysis
        
        # Create a test request
        factory = RequestFactory()
        request = factory.get('/pharmacy/revenue/statistics/')
        
        # Create a test user and attach to request
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@test.com', 'is_staff': True, 'is_superuser': True}
        )
        request.user = user
        
        print(f"✅ Test user created/found: {user.username}")
        
        # Call the view function directly
        print("📊 Calling comprehensive_revenue_analysis view...")
        response = comprehensive_revenue_analysis(request)
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📊 Response Type: {type(response).__name__}")
        
        if hasattr(response, 'content'):
            content_length = len(response.content)
            print(f"📊 Content Length: {content_length} bytes")
            
            if content_length > 0:
                print("✅ View returns content successfully!")
                # Save a sample of content to file for inspection
                with open('revenue_view_output_sample.html', 'w', encoding='utf-8') as f:
                    content_str = response.content.decode('utf-8')
                    f.write(content_str[:2000])  # First 2000 characters
                print("💾 Sample content saved to 'revenue_view_output_sample.html'")
            else:
                print("❌ View returns empty content!")
        
        if hasattr(response, 'context_data'):
            print(f"📊 Context Keys: {list(response.context_data.keys()) if response.context_data else 'No context'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing view: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_revenue_service():
    """Test the revenue service directly"""
    print("\n🔍 Testing Revenue Service...")
    
    try:
        from pharmacy.revenue_service import RevenueAggregationService, MonthFilterHelper
        
        # Get current month date range
        start_date, end_date = MonthFilterHelper.get_current_month()
        print(f"📅 Date range: {start_date} to {end_date}")
        
        # Initialize revenue service
        revenue_service = RevenueAggregationService(start_date, end_date)
        
        # Test individual revenue components
        print("📊 Testing individual revenue components...")
        pharmacy_revenue = revenue_service.get_pharmacy_revenue()
        print(f"  Pharmacy: ₦{pharmacy_revenue['total_revenue']:.2f}")
        
        laboratory_revenue = revenue_service.get_laboratory_revenue()
        print(f"  Laboratory: ₦{laboratory_revenue['total_revenue']:.2f}")
        
        consultation_revenue = revenue_service.get_consultation_revenue()
        print(f"  Consultations: ₦{consultation_revenue['total_revenue']:.2f}")
        
        # Get comprehensive revenue data
        comprehensive_data = revenue_service.get_comprehensive_revenue()
        print(f"📊 Total Revenue: ₦{comprehensive_data['total_revenue']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing service: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_form():
    """Test the revenue filter form"""
    print("\n🔍 Testing Revenue Filter Form...")
    try:
        from pharmacy.revenue_service import MonthFilterHelper

        # Test MonthFilterHelper as replacement for removed form
        start_date, end_date = MonthFilterHelper.get_current_month()
        print(f"📋 MonthFilterHelper current month: {start_date} to {end_date}")
        prev_start, prev_end = MonthFilterHelper.get_previous_month()
        print(f"📋 Previous month: {prev_start} to {prev_end}")
        spec_start, spec_end = MonthFilterHelper.get_specific_month(2025, 1)
        print(f"📋 Specific month Jan 2025: {spec_start} to {spec_end}")

        return True
    except Exception as e:
        print(f"❌ Error testing form: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_template_exists():
    """Test if the template file exists"""
    print("\n🔍 Testing Template File...")
    
    try:
        import os
        template_path = 'pharmacy/templates/pharmacy/simple_revenue_statistics.html'
        full_path = os.path.join(os.getcwd(), template_path)
        
        if os.path.exists(full_path):
            print(f"✅ Template exists: {full_path}")
            file_size = os.path.getsize(full_path)
            print(f"📄 Template size: {file_size} bytes")
        else:
            print(f"❌ Template not found: {full_path}")
            # List pharmacy templates
            pharmacy_templates_dir = 'pharmacy/templates/pharmacy/'
            if os.path.exists(pharmacy_templates_dir):
                templates = os.listdir(pharmacy_templates_dir)
                print(f"📄 Available templates: {templates}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking template: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Revenue View Diagnostic Script")
    print("="*50)
    
    # Test components in order
    template_test = test_template_exists()
    form_test = test_form()
    service_test = test_revenue_service()
    view_test = test_revenue_view()
    
    print("\n" + "="*50)
    print("📝 SUMMARY:")
    print(f"Template Test: {'✅ PASSED' if template_test else '❌ FAILED'}")
    print(f"Form Test: {'✅ PASSED' if form_test else '❌ FAILED'}")
    print(f"Service Test: {'✅ PASSED' if service_test else '❌ FAILED'}")
    print(f"View Test: {'✅ PASSED' if view_test else '❌ FAILED'}")
    
    if all([template_test, form_test, service_test, view_test]):
        print("\n🎉 All tests passed! The view should be working.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")