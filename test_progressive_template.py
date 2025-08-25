#!/usr/bin/env python
"""
Progressive template testing to find the exact problematic section
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def test_progressive_template_sections():
    """Test template sections progressively to find the issue"""
    print("🔍 Testing Template Sections Progressively...")
    
    try:
        from django.template.loader import render_to_string
        from django.test import RequestFactory
        
        # Create a request
        factory = RequestFactory()
        request = factory.get('/pharmacy/revenue/statistics/')
        
        # Base context
        base_context = {
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
        
        # Test sections progressively
        test_sections = [
            # Section 1: Basic header and title
            """
{% extends "base.html" %}
{% load static %}
{% load pharmacy_tags %}

{% block title %}Comprehensive Revenue Analysis{% endblock %}

{% block extra_css %}
<link href="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.css" rel="stylesheet">
<style>
    .revenue-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h1 class="h3 mb-0">Comprehensive Hospital Revenue Analysis</h1>
            </div>
        </div>
    </div>
</div>
{% endblock %}
            """,
            
            # Section 2: Add revenue overview
            """
{% extends "base.html" %}
{% load static %}
{% load pharmacy_tags %}

{% block title %}Comprehensive Revenue Analysis{% endblock %}

{% block extra_css %}
<link href="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.css" rel="stylesheet">
<style>
    .revenue-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h1 class="h3 mb-0">Comprehensive Hospital Revenue Analysis</h1>
            </div>
        </div>
    </div>

    <!-- Total Revenue Overview -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="revenue-card text-center">
                <div class="row">
                    <div class="col-md-12">
                        <h3 class="mb-1">Total Hospital Revenue</h3>
                        <div class="metric-value">₦{{ total_revenue|floatformat:2 }}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
            """,
            
            # Section 3: Add module breakdown
            """
{% extends "base.html" %}
{% load static %}
{% load pharmacy_tags %}

{% block title %}Comprehensive Revenue Analysis{% endblock %}

{% block extra_css %}
<link href="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.css" rel="stylesheet">
<style>
    .revenue-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .module-card {
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h1 class="h3 mb-0">Comprehensive Hospital Revenue Analysis</h1>
            </div>
        </div>
    </div>

    <!-- Total Revenue Overview -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="revenue-card text-center">
                <div class="row">
                    <div class="col-md-12">
                        <h3 class="mb-1">Total Hospital Revenue</h3>
                        <div class="metric-value">₦{{ total_revenue|floatformat:2 }}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Module-wise Revenue Breakdown -->
    <div class="row mb-4">
        {% for source in revenue_sources %}
        <div class="col-lg-4 col-md-6 mb-3">
            <div class="card module-card h-100">
                <div class="card-body text-center">
                    <i class="{{ source.icon }} fa-3x text-{{ source.color }} mb-3"></i>
                    <h5 class="card-title">{{ source.name }} Revenue</h5>
                    <div class="metric-value text-{{ source.color }}">₦{{ source.revenue|floatformat:2 }}</div>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
            """,
        ]
        
        # Test each section
        for i, section_template in enumerate(test_sections):
            print(f"\n📋 Testing Section {i+1}...")
            
            # Save temporary template
            temp_template_path = f'templates/temp_section_{i+1}.html'
            os.makedirs(os.path.dirname(temp_template_path), exist_ok=True)
            
            with open(temp_template_path, 'w', encoding='utf-8') as f:
                f.write(section_template)
            
            try:
                rendered = render_to_string(f'temp_section_{i+1}.html', base_context, request=request)
                print(f"✅ Section {i+1} rendered: {len(rendered)} characters")
                
                if len(rendered) > 0:
                    # Save for inspection
                    with open(f'temp_section_{i+1}_output.html', 'w', encoding='utf-8') as f:
                        f.write(rendered)
                    print(f"💾 Section {i+1} output saved to 'temp_section_{i+1}_output.html'")
                else:
                    print(f"❌ Section {i+1} rendered but is empty")
                    
            except Exception as section_error:
                print(f"❌ Section {i+1} error: {section_error}")
                import traceback
                traceback.print_exc()
            
            # Clean up
            if os.path.exists(temp_template_path):
                os.remove(temp_template_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Progressive template test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Progressive Template Section Testing")
    print("="*60)
    
    # Run test
    result = test_progressive_template_sections()
    
    print("\n" + "="*60)
    print("📝 PROGRESSIVE TEMPLATE TEST SUMMARY:")
    print(f"Test Result: {'✅ PASSED' if result else '❌ FAILED'}")