#!/usr/bin/env python
"""
Systematic template debugging to find the problematic section
"""

import os
import sys
import django
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_template_sections():
    """Test different sections of the template to isolate the issue"""
    print("🔍 Testing Template Sections Systematically...")
    
    try:
        from django.template import Template
        
        # Get the full template content
        template_path = 'pharmacy/templates/pharmacy/simple_revenue_statistics.html'
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        print(f"📋 Template size: {len(template_content)} characters")
        
        # Test 1: Basic template structure
        print("\n📋 Test 1: Basic template without content...")
        basic_template = """
        {% extends "base.html" %}
        {% block title %}Test{% endblock %}
        {% block content %}
        <h1>Hello World</h1>
        {% endblock %}
        """
        
        template = Template(basic_template)
        rendered = template.render({'title': 'Test'})
        print(f"Basic template rendered: {len(rendered)} characters")
        
        # Test 2: Template with static and tags
        print("\n📋 Test 2: Template with static and pharmacy_tags...")
        tagged_template = """
        {% extends "base.html" %}
        {% load static %}
        {% load pharmacy_tags %}
        {% block title %}Test{% endblock %}
        {% block content %}
        <h1>Hello World with Tags</h1>
        {% endblock %}
        """
        
        template = Template(tagged_template)
        rendered = template.render({'title': 'Test'})
        print(f"Tagged template rendered: {len(rendered)} characters")
        
        # Test 3: Template with some context variables
        print("\n📋 Test 3: Template with context variables...")
        context_template = """
        {% extends "base.html" %}
        {% load static %}
        {% load pharmacy_tags %}
        {% block title %}{{ page_title }}{% endblock %}
        {% block content %}
        <h1>{{ page_title }}</h1>
        <p>Total Revenue: {{ total_revenue }}</p>
        {% endblock %}
        """
        
        template = Template(context_template)
        context = {
            'page_title': 'Revenue Analysis',
            'total_revenue': 1000,
        }
        rendered = template.render(context)
        print(f"Context template rendered: {len(rendered)} characters")
        
        # Test 4: Test with filter_form (might be None)
        print("\n📋 Test 4: Template with filter_form...")
        form_template = """
        {% extends "base.html" %}
        {% load static %}
        {% load pharmacy_tags %}
        {% block title %}{{ page_title }}{% endblock %}
        {% block content %}
        <h1>{{ page_title }}</h1>
        {% if filter_form %}
            <p>Form exists</p>
        {% else %}
            <p>No form</p>
        {% endif %}
        {% endblock %}
        """
        
        template = Template(form_template)
        context = {
            'page_title': 'Revenue Analysis',
            'filter_form': None,
        }
        rendered = template.render(context)
        print(f"Form template rendered: {len(rendered)} characters")
        
        # Test 5: Test specific problematic sections
        print("\n📋 Test 5: Testing specific template sections...")
        
        # Extract and test the header section
        lines = template_content.split('\n')
        header_end = 0
        for i, line in enumerate(lines):
            if 'block content' in line:
                header_end = i + 5  # Include a few lines after block content
                break
        
        if header_end > 0:
            header_content = '\n'.join(lines[:header_end]) + '\n<h1>Header Test</h1>\n{% endblock %}'
            try:
                template = Template(header_content)
                rendered = template.render({'title': 'Test'})
                print(f"Header section rendered: {len(rendered)} characters")
            except Exception as header_error:
                print(f"❌ Header section error: {header_error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Template section test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_problematic_template_tags():
    """Test for problematic template tags or filters"""
    print("\n🔍 Testing Potentially Problematic Template Features...")
    
    try:
        from django.template import Template
        
        # Test template tags that might cause issues
        test_cases = [
            # Test for loop with missing context
            "{% for item in missing_list %}{{ item }}{% endfor %}",
            
            # Test filters with None values
            "{{ none_value|floatformat:2 }}",
            
            # Test mathematical operations that might fail
            "{{ total_revenue|mul:100|div:total_revenue|floatformat:1 }}",
            
            # Test nested context access
            "{{ comprehensive_data.pharmacy_revenue.total_revenue }}",
        ]
        
        base_template = """
        {% load static %}
        {% load pharmacy_tags %}
        TEST_CONTENT
        """
        
        context = {
            'none_value': None,
            'total_revenue': 1000,
            'comprehensive_data': {
                'pharmacy_revenue': {'total_revenue': 100}
            }
        }
        
        for i, test_content in enumerate(test_cases):
            print(f"\n📋 Testing case {i+1}: {test_content[:50]}...")
            template_source = base_template.replace('TEST_CONTENT', test_content)
            
            try:
                template = Template(template_source)
                rendered = template.render(context)
                print(f"✅ Case {i+1} rendered: {len(rendered)} characters")
            except Exception as case_error:
                print(f"❌ Case {i+1} error: {case_error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Template tag test error: {e}")
        return False

def find_exact_problem_line():
    """Try to find the exact line causing the issue"""
    print("\n🔍 Finding Exact Problem Line...")
    
    try:
        from django.template import Template
        
        # Read the template
        template_path = 'pharmacy/templates/pharmacy/simple_revenue_statistics.html'
        with open(template_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Minimal context
        context = {
            'title': 'Test',
            'page_title': 'Test',
            'total_revenue': 1000,
            'filter_form': None,
            'start_date': date.today(),
            'end_date': date.today(),
            'comprehensive_data': {},
            'revenue_sources': [],
            'chart_data': {'months': '[]'},
            'performance_metrics': {'total_transactions': 0},
        }
        
        # Test the template line by line (binary search approach)
        def test_lines(start, end):
            if start >= end:
                return start
            
            mid = (start + end) // 2
            test_template = ''.join(lines[:mid+1]) + '\n{% endblock %}'
            
            try:
                template = Template(test_template)
                rendered = template.render(context)
                if len(rendered) == 0:
                    # Problem is in first half
                    return test_lines(start, mid)
                else:
                    # Problem is in second half
                    return test_lines(mid + 1, end)
            except:
                # Problem is in first half
                return test_lines(start, mid)
        
        # Find content block start
        content_start = 0
        for i, line in enumerate(lines):
            if 'block content' in line:
                content_start = i
                break
        
        if content_start > 0:
            problem_line = test_lines(content_start, len(lines) - 1)
            print(f"📋 Problem likely around line {problem_line + 1}: {lines[problem_line].strip()}")
            
            # Show context around problem line
            start_ctx = max(0, problem_line - 3)
            end_ctx = min(len(lines), problem_line + 4)
            
            print("📋 Context around problem:")
            for i in range(start_ctx, end_ctx):
                marker = ">>> " if i == problem_line else "    "
                print(f"{marker}Line {i+1}: {lines[i].rstrip()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Line-by-line test error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Systematic Template Debugging")
    print("="*60)
    
    # Run systematic tests
    section_test = test_template_sections()
    tag_test = test_problematic_template_tags()
    line_test = find_exact_problem_line()
    
    print("\n" + "="*60)
    print("📝 SYSTEMATIC DEBUG SUMMARY:")
    print(f"Section Test: {'✅ PASSED' if section_test else '❌ FAILED'}")
    print(f"Tag Test: {'✅ PASSED' if tag_test else '❌ FAILED'}")
    print(f"Line Test: {'✅ PASSED' if line_test else '❌ FAILED'}")