#!/usr/bin/env python
"""
Simple test to check chart data generation
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_chart_data_generation():
    """Test if chart data is being generated correctly"""
    print("🔍 Testing Chart Data Generation...")
    
    try:
        from pharmacy.revenue_service import RevenueAggregationService, MonthFilterHelper
        import json
        
        # Get current month date range
        start_date, end_date = MonthFilterHelper.get_current_month()
        print(f"📅 Date range: {start_date} to {end_date}")
        
        # Initialize revenue service
        revenue_service = RevenueAggregationService(start_date, end_date)
        
        # Get comprehensive revenue data
        comprehensive_data = revenue_service.get_comprehensive_revenue()
        print(f"💰 Total revenue: ₦{comprehensive_data['total_revenue']:.2f}")
        
        # Get monthly trends
        monthly_trends = revenue_service.get_monthly_trends(6)
        print(f"📈 Monthly trends count: {len(monthly_trends)}")
        
        if monthly_trends:
            print("📊 Sample trend data:")
            for trend in monthly_trends[:3]:  # Show first 3
                print(f"  {trend['month']}: ₦{trend['total_revenue']:.2f}")
        
        # Prepare chart data like in the view
        chart_months = [trend['month'] for trend in monthly_trends]
        chart_data = {
            'months': json.dumps(chart_months),
            'pharmacy': json.dumps([float(trend['pharmacy']) for trend in monthly_trends]),
            'laboratory': json.dumps([float(trend['laboratory']) for trend in monthly_trends]),
            'total': json.dumps([float(trend['total_revenue']) for trend in monthly_trends])
        }
        
        print("🎯 Chart data structure:")
        print(f"  Months: {chart_data['months']}")
        print(f"  Pharmacy: {chart_data['pharmacy']}")
        print(f"  Total: {chart_data['total']}")
        
        # Test if the JSON is valid
        try:
            months_parsed = json.loads(chart_data['months'])
            pharmacy_parsed = json.loads(chart_data['pharmacy'])
            print("✅ Chart data JSON is valid")
            print(f"✅ Months parsed: {months_parsed}")
            print(f"✅ Pharmacy parsed: {pharmacy_parsed}")
        except json.JSONDecodeError as e:
            print(f"❌ Chart data JSON is invalid: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_template_rendering():
    """Test template rendering with sample data"""
    print("\n🔍 Testing Template Rendering...")
    
    try:
        from django.template import Template, Context
        from django.template.loader import get_template
        
        # Try to load the template
        template = get_template('pharmacy/simple_revenue_statistics.html')
        print("✅ Template loads successfully")
        
        # Create sample context data
        sample_context = {
            'chart_data': {
                'months': '["Jan 2025", "Feb 2025", "Mar 2025"]',
                'pharmacy': '[100, 200, 300]',
                'laboratory': '[50, 75, 100]',
                'total': '[150, 275, 400]'
            },
            'total_revenue': 825.00,
            'revenue_sources': [
                {'name': 'Pharmacy', 'revenue': 600, 'icon': 'fas fa-pills', 'color': 'primary'},
                {'name': 'Laboratory', 'revenue': 225, 'icon': 'fas fa-microscope', 'color': 'success'},
            ],
            'performance_metrics': {
                'total_transactions': 10,
                'average_transaction_value': 82.50,
                'daily_average': 27.50,
                'days_in_period': 30
            },
            'start_date': '2025-08-01',
            'end_date': '2025-08-31',
            'monthly_trends': [],
            'daily_breakdown': [],
            'include_daily_breakdown': False,
            'selected_departments': [],
            'filter_form': None,
            'pharmacy_revenue': {'total_revenue': 600, 'total_payments': 5},
            'lab_revenue': {'total_revenue': 225, 'total_payments': 5},
            'consultation_revenue': {'total_revenue': 0, 'total_payments': 0},
            'theatre_revenue': {'total_revenue': 0, 'total_payments': 0},
            'admission_revenue': {'total_revenue': 0, 'total_payments': 0},
            'general_revenue': {'total_revenue': 0, 'total_payments': 0},
            'wallet_revenue': {'total_revenue': 0, 'total_transactions': 0},
        }
        
        # Try to render the template
        rendered = template.render(sample_context)
        print("✅ Template renders successfully")
        
        # Check for chart elements in rendered HTML
        if 'new Chart(' in rendered:
            print("✅ Chart.js initialization code present")
        else:
            print("❌ Chart.js initialization code missing")
            
        if 'chart_data.months' in rendered:
            print("✅ Chart data variables present")
        else:
            print("❌ Chart data variables missing")
        
        # Save rendered template for inspection
        with open('test_rendered_template.html', 'w', encoding='utf-8') as f:
            f.write(rendered)
        print("💾 Rendered template saved to 'test_rendered_template.html'")
        
        return True
        
    except Exception as e:
        print(f"❌ Template error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Chart Data Diagnostics")
    print("=" * 50)
    
    data_test = test_chart_data_generation()
    template_test = test_template_rendering()
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY:")
    print(f"Data Generation: {'✅ PASS' if data_test else '❌ FAIL'}")
    print(f"Template Rendering: {'✅ PASS' if template_test else '❌ FAIL'}")
    
    if data_test and template_test:
        print("\n🎉 Both tests passed! The issue might be:")
        print("   1. Authentication/login required")
        print("   2. Browser JavaScript disabled")
        print("   3. Network issues loading Chart.js CDN")
        print("   4. View not passing data to template correctly")
    else:
        print("\n⚠️ Issues found - check error messages above")