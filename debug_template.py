#!/usr/bin/env python
"""
Template syntax and rendering debug script
"""

import os
import sys
import django
from datetime import date, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_template_syntax():
    """Test template syntax and compilation"""
    print("🔍 Testing Template Syntax...")
    
    try:
        from django.template import Template, Context
        from django.template.loader import get_template
        
        # Test 1: Load template
        print("📋 Test 1: Loading template...")
        template = get_template('pharmacy/simple_revenue_statistics.html')
        print("✅ Template loaded successfully")
        
        # Test 2: Check for syntax errors by compiling
        print("📋 Test 2: Compiling template...")
        try:
            # Force template compilation
            template.template
            print("✅ Template compiled successfully")
        except Exception as compile_error:
            print(f"❌ Template compilation error: {compile_error}")
            return False
        
        # Test 3: Test minimal context rendering
        print("📋 Test 3: Testing minimal context...")
        minimal_context = {
            'filter_form': None,
            'start_date': date.today(),
            'end_date': date.today(),
            'total_revenue': 1000,
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
            'monthly_trends': [
                {'month': 'Jan 2025', 'total_revenue': 1000, 'pharmacy': 100, 'laboratory': 200}
            ],
            'daily_breakdown': [],
            'include_daily_breakdown': False,
            'selected_departments': [],
            'page_title': 'Test Revenue Analysis',
            'active_nav': 'pharmacy',
            
            # Individual department data
            'pharmacy_revenue': {'total_revenue': 100, 'total_payments': 1, 'total_prescriptions': 1, 'total_medications_dispensed': 1},
            'lab_revenue': {'total_revenue': 200, 'total_payments': 2, 'total_tests': 2},
            'consultation_revenue': {'total_revenue': 300, 'total_payments': 3, 'total_consultations': 3},
            'theatre_revenue': {'total_revenue': 400, 'total_payments': 4, 'total_surgeries': 4},
            'admission_revenue': {'total_revenue': 500, 'total_payments': 5, 'total_admissions': 5},
            'general_revenue': {'total_revenue': 600, 'total_payments': 6},
            'wallet_revenue': {'total_revenue': 700, 'total_transactions': 7},
        }
        
        rendered = template.render(minimal_context)
        print(f"📋 Template rendered: {len(rendered)} characters")
        
        if len(rendered) == 0:
            print("❌ Template renders to empty string!")
            
            # Test base template
            print("📋 Testing base template...")
            try:
                base_template = get_template('base.html')
                base_rendered = base_template.render(Context({'title': 'Test'}))
                print(f"📋 Base template rendered: {len(base_rendered)} characters")
            except Exception as base_error:
                print(f"❌ Base template error: {base_error}")
                
        else:
            print("✅ Template renders content successfully")
            
            # Save rendered content for inspection
            with open('template_debug_output.html', 'w', encoding='utf-8') as f:
                f.write(rendered)
            print("💾 Rendered content saved to 'template_debug_output.html'")
        
        return True
        
    except Exception as e:
        print(f"❌ Template syntax test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_template_tags():
    """Test custom template tags and filters"""
    print("\n🔍 Testing Template Tags...")
    
    try:
        # Test if pharmacy_tags can be loaded
        from django.template import Template, Context
        
        test_template_source = """
        {% load static %}
        {% load pharmacy_tags %}
        <h1>{{ title }}</h1>
        <p>Revenue: {{ revenue|floatformat:2 }}</p>
        """
        
        template = Template(test_template_source)
        context = Context({'title': 'Test', 'revenue': 1234.567})
        
        rendered = template.render(context)
        print(f"📋 Tag test rendered: {len(rendered)} characters")
        print(f"📋 Content: {rendered.strip()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Template tags test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_template_inheritance():
    """Check template inheritance chain"""
    print("\n🔍 Checking Template Inheritance...")
    
    try:
        import os
        
        # Check if base.html exists
        base_path = os.path.join(os.getcwd(), 'templates', 'base.html')
        if os.path.exists(base_path):
            print("✅ base.html exists")
            
            # Check first few lines for syntax
            with open(base_path, 'r', encoding='utf-8') as f:
                first_lines = f.read(500)  # First 500 chars
                print(f"📋 Base template starts with: {first_lines[:100]}...")
        else:
            print("❌ base.html not found")
            
        # Check template directories
        from django.conf import settings
        template_dirs = []
        for template_config in settings.TEMPLATES:
            template_dirs.extend(template_config.get('DIRS', []))
            
        print(f"📋 Template directories: {template_dirs}")
        
        return True
        
    except Exception as e:
        print(f"❌ Template inheritance check error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Template Debug Script")
    print("="*50)
    
    # Run template tests
    inheritance_test = check_template_inheritance()
    tag_test = test_template_tags()
    syntax_test = test_template_syntax()
    
    print("\n" + "="*50)
    print("📝 TEMPLATE DEBUG SUMMARY:")
    print(f"Inheritance Test: {'✅ PASSED' if inheritance_test else '❌ FAILED'}")
    print(f"Tag Test: {'✅ PASSED' if tag_test else '❌ FAILED'}")
    print(f"Syntax Test: {'✅ PASSED' if syntax_test else '❌ FAILED'}")