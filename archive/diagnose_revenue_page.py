#!/usr/bin/env python
"""
Diagnostic script to check the revenue analysis page
"""

import os
import sys
import django
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_page_access():
    """Test if the revenue page is accessible"""
    print("🔍 Testing Revenue Page Access...")
    
    try:
        from django.test import Client
        from django.contrib.auth import get_user_model
        
        # Create test client
        client = Client()
        
        # Try without authentication first
        response = client.get('/pharmacy/revenue/statistics/')
        print(f"📊 Response Status (no auth): {response.status_code}")
        
        if response.status_code == 302:
            print("🔄 Page redirects (authentication required)")
            
            # Try with authentication
            User = get_user_model()
            user, created = User.objects.get_or_create(
                username='admin',
                defaults={'email': 'admin@test.com', 'is_staff': True, 'is_superuser': True}
            )
            
            client.force_login(user)
            response = client.get('/pharmacy/revenue/statistics/')
            print(f"📊 Response Status (with auth): {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Page loads successfully!")
            
            content = response.content.decode('utf-8')
            
            # Check if Chart.js is included
            if 'chart.js' in content.lower():
                print("✅ Chart.js library is included")
            else:
                print("❌ Chart.js library NOT found")
            
            # Check for canvas elements
            if '<canvas' in content:
                print("✅ Canvas elements found (charts should render)")
            else:
                print("❌ No canvas elements found")
            
            # Check for chart data
            if 'chart_data' in content:
                print("✅ Chart data variables found")
            else:
                print("❌ Chart data variables NOT found")
                
            # Check for JavaScript errors indicators
            if 'error' in content.lower() and 'chart' in content.lower():
                print("⚠️  Potential JavaScript errors detected")
            
            # Save response for inspection
            with open('revenue_page_response.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("💾 Full response saved to 'revenue_page_response.html'")
            
        else:
            print(f"❌ Page returned error status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing page: {e}")
        import traceback
        traceback.print_exc()

def test_view_directly():
    """Test the view function directly"""
    print("\n🔍 Testing View Function Directly...")
    
    try:
        from django.test import RequestFactory
        from django.contrib.auth import get_user_model
        from pharmacy.views import simple_revenue_statistics as comprehensive_revenue_analysis
        
        # Create a test request
        factory = RequestFactory()
        request = factory.get('/pharmacy/revenue/statistics/')
        
        # Create a test user
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@test.com', 'is_staff': True}
        )
        request.user = user
        
        # Call the view
        response = comprehensive_revenue_analysis(request)
        
        print(f"📊 View Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ View executes successfully")
            
            # Check context data
            context = response.context_data if hasattr(response, 'context_data') else {}
            
            if 'chart_data' in context:
                chart_data = context['chart_data']
                print(f"✅ Chart data present: {list(chart_data.keys())}")
                print(f"📊 Sample data: {chart_data.get('months', 'N/A')}")
            else:
                print("❌ Chart data NOT in context")
                
            if 'total_revenue' in context:
                print(f"✅ Total revenue: ₦{context['total_revenue']}")
            else:
                print("❌ Total revenue NOT in context")
                
        else:
            print(f"❌ View returned error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing view: {e}")
        import traceback
        traceback.print_exc()

def check_static_files():
    """Check if static files configuration looks correct"""
    print("\n🔍 Checking Static Files Configuration...")
    
    try:
        from django.conf import settings
        
        print(f"✅ STATIC_URL: {getattr(settings, 'STATIC_URL', 'Not set')}")
        print(f"✅ STATIC_ROOT: {getattr(settings, 'STATIC_ROOT', 'Not set')}")
        
        # Check if we're using CDN (which should work)
        print("✅ Using Chart.js CDN - should work if internet is available")
        
    except Exception as e:
        print(f"❌ Error checking static files: {e}")

def check_template_syntax():
    """Check template for common issues"""
    print("\n🔍 Checking Template Syntax...")
    
    try:
        template_path = 'pharmacy/templates/pharmacy/simple_revenue_statistics.html'
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for common issues
            if '{{ chart_data.months|safe }}' in content:
                print("✅ Chart data template syntax looks correct")
            else:
                print("❌ Chart data template syntax issue detected")
                
            if 'Chart(' in content:
                print("✅ Chart.js initialization code found")
            else:
                print("❌ Chart.js initialization code NOT found")
                
            if 'chart.min.js' in content or 'chart.js' in content:
                print("✅ Chart.js library inclusion found")
            else:
                print("❌ Chart.js library inclusion NOT found")
                
        else:
            print(f"❌ Template file not found: {template_path}")
            
    except Exception as e:
        print(f"❌ Error checking template: {e}")

def main():
    print("🏥 HMS Revenue Page Diagnostics")
    print("=" * 50)
    
    test_page_access()
    test_view_directly() 
    check_static_files()
    check_template_syntax()
    
    print("\n" + "=" * 50)
    print("📋 DIAGNOSTIC SUMMARY")
    print("📋 Check the output above for specific issues")
    print("📋 If 'revenue_page_response.html' was created, examine it for errors")
    print("📋 Common issues:")
    print("   - Authentication required (302 redirect)")
    print("   - Chart.js not loading (network issues)")
    print("   - JavaScript errors (check browser console)")
    print("   - Missing chart data (empty database)")
    print("   - Template syntax errors")

if __name__ == "__main__":
    main()