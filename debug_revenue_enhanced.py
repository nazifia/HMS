#!/usr/bin/env python
"""
Enhanced debug script for pharmacy revenue view
"""

import os
import sys
import django
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_view_with_detailed_debugging():
    """Test the view with detailed debugging"""
    print("🔍 Enhanced View Testing...")
    
    try:
        from django.test import RequestFactory, Client
        from django.contrib.auth import get_user_model
        from django.template import Context, Template
        from django.template.loader import render_to_string
        
        # Test 1: Use Django test client
        print("\n📊 Test 1: Using Django Test Client")
        client = Client()
        
        # Create test user
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@test.com', 'is_staff': True, 'is_superuser': True}
        )
        
        # Login the user
        client.force_login(user)
        
        # Make request to the URL
        response = client.get('/pharmacy/revenue/statistics/')
        print(f"📊 Client Response Status: {response.status_code}")
        print(f"📊 Client Content Length: {len(response.content)} bytes")
        
        if response.status_code == 302:
            print(f"📊 Redirect Location: {response.get('Location', 'None')}")
        
        # Test 2: Directly test the view function with context capture
        print("\n📊 Test 2: Direct View Function with Context")
        from pharmacy.views import simple_revenue_statistics as comprehensive_revenue_analysis
        
        factory = RequestFactory()
        request = factory.get('/pharmacy/revenue/statistics/')
        request.user = user
        
        # Monkey patch to capture context
        original_render = None
        captured_context = {}
        
        def capture_render(request, template_name, context=None, **kwargs):
            print(f"📋 Template: {template_name}")
            if context:
                captured_context.update(context)
                print(f"📋 Context keys: {list(context.keys())}")
                print(f"📋 Total revenue: {context.get('total_revenue', 'NOT FOUND')}")
            return original_render(request, template_name, context, **kwargs)
        
        # Patch the render function
        from django.shortcuts import render
        original_render = render
        
        # Call view with patches
        try:
            # Import and patch render in the view module
            import pharmacy.views
            pharmacy.views.render = capture_render
            
            response = comprehensive_revenue_analysis(request)
            print(f"📊 Direct Response Status: {response.status_code}")
            print(f"📊 Direct Content Length: {len(response.content)} bytes")
            
            if captured_context:
                print(f"📋 Captured context keys: {list(captured_context.keys())}")
            else:
                print("❌ No context captured!")
            
        finally:
            # Restore original render
            pharmacy.views.render = original_render
        
        # Test 3: Test template rendering directly
        print("\n📊 Test 3: Direct Template Test")
        try:
            # Create minimal context
            test_context = {
                'total_revenue': 1000,
                'start_date': date.today(),
                'end_date': date.today(),
                'filter_form': None,
                'comprehensive_data': {
                    'pharmacy_revenue': {'total_revenue': 100, 'total_payments': 1},
                    'laboratory_revenue': {'total_revenue': 200, 'total_payments': 2},
                    'consultation_revenue': {'total_revenue': 300, 'total_payments': 3},
                    'theatre_revenue': {'total_revenue': 400, 'total_payments': 4},
                    'admission_revenue': {'total_revenue': 500, 'total_payments': 5},
                    'general_revenue': {'total_revenue': 600, 'total_payments': 6},
                    'wallet_revenue': {'total_revenue': 700, 'total_transactions': 7},
                },
                'revenue_sources': [],
                'chart_data': {'months': '[]', 'pharmacy': '[]'},
                'performance_metrics': {'total_transactions': 0, 'daily_average': 0},
                'monthly_trends': [],
                'daily_breakdown': [],
                'include_daily_breakdown': False,
                'selected_departments': [],
                'page_title': 'Test',
                'active_nav': 'pharmacy',
            }
            
            rendered = render_to_string('pharmacy/simple_revenue_statistics.html', test_context)
            print(f"📋 Template rendered successfully: {len(rendered)} characters")
            
            # Save sample to file
            with open('template_test_output.html', 'w', encoding='utf-8') as f:
                f.write(rendered[:5000])  # First 5000 characters
            print("💾 Template test output saved to 'template_test_output.html'")
            
        except Exception as template_error:
            print(f"❌ Template rendering error: {template_error}")
            import traceback
            traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced testing error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_middleware_and_decorators():
    """Test if middleware or decorators are interfering"""
    print("\n🔍 Testing Middleware and Decorators...")
    
    try:
        from django.test import RequestFactory, override_settings
        from django.contrib.auth import get_user_model
        
        # Create request and user
        factory = RequestFactory()
        request = factory.get('/pharmacy/revenue/statistics/')
        
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username='testuser2',
            defaults={'email': 'test2@test.com', 'is_staff': True, 'is_superuser': True}
        )
        request.user = user
        
        # Test view without decorators
        print("📊 Testing view without @login_required...")
        from pharmacy.views import simple_revenue_statistics as comprehensive_revenue_analysis
        
        # Get the actual function (unwrapped)
        view_func = comprehensive_revenue_analysis
        while hasattr(view_func, '__wrapped__'):
            view_func = view_func.__wrapped__
        
        response = view_func(request)
        print(f"📊 Unwrapped view status: {response.status_code}")
        print(f"📊 Unwrapped view content length: {len(response.content)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Middleware/decorator testing error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_django_settings():
    """Check Django settings that might affect rendering"""
    print("\n🔍 Checking Django Settings...")
    
    try:
        from django.conf import settings
        
        print(f"📋 DEBUG: {getattr(settings, 'DEBUG', 'NOT SET')}")
        print(f"📋 TEMPLATE_DEBUG: {getattr(settings, 'TEMPLATE_DEBUG', 'NOT SET')}")
        
        # Check template settings
        if hasattr(settings, 'TEMPLATES'):
            for i, template_config in enumerate(settings.TEMPLATES):
                print(f"📋 Template Engine {i}: {template_config.get('BACKEND', 'Unknown')}")
                print(f"📋 Template Dirs {i}: {template_config.get('DIRS', [])}")
                
        # Check installed apps
        if 'pharmacy' in getattr(settings, 'INSTALLED_APPS', []):
            print("✅ Pharmacy app is installed")
        else:
            print("❌ Pharmacy app not in INSTALLED_APPS")
        
        return True
        
    except Exception as e:
        print(f"❌ Settings check error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Enhanced Revenue View Diagnostic Script")
    print("="*60)
    
    # Run enhanced tests
    settings_test = check_django_settings()
    middleware_test = test_middleware_and_decorators()
    detailed_test = test_view_with_detailed_debugging()
    
    print("\n" + "="*60)
    print("📝 ENHANCED SUMMARY:")
    print(f"Settings Test: {'✅ PASSED' if settings_test else '❌ FAILED'}")
    print(f"Middleware Test: {'✅ PASSED' if middleware_test else '❌ FAILED'}")
    print(f"Detailed View Test: {'✅ PASSED' if detailed_test else '❌ FAILED'}")