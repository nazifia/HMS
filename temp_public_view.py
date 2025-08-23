"""
Temporary view for testing charts without authentication
Add this to your pharmacy/views.py for testing
"""

def test_revenue_charts_public(request):
    """Temporary public view to test revenue charts"""
    from .revenue_service import RevenueAggregationService, MonthFilterHelper
    from .forms import ComprehensiveRevenueFilterForm
    import json
    from django.shortcuts import render
    
    # Get current month date range
    start_date, end_date = MonthFilterHelper.get_current_month()
    
    # Initialize revenue aggregation service
    revenue_service = RevenueAggregationService(start_date, end_date)
    
    # Get comprehensive revenue data
    comprehensive_data = revenue_service.get_comprehensive_revenue()
    
    # Get monthly trends (last 12 months)
    monthly_trends = revenue_service.get_monthly_trends(12)
    
    # Prepare chart data for monthly trends
    chart_months = [trend['month'] for trend in monthly_trends]
    chart_data = {
        'months': json.dumps(chart_months),
        'pharmacy': json.dumps([float(trend['pharmacy']) for trend in monthly_trends]),
        'laboratory': json.dumps([float(trend['laboratory']) for trend in monthly_trends]),
        'consultations': json.dumps([float(trend['consultations']) for trend in monthly_trends]),
        'theatre': json.dumps([float(trend['theatre']) for trend in monthly_trends]),
        'admissions': json.dumps([float(trend['admissions']) for trend in monthly_trends]),
        'general': json.dumps([float(trend['general']) for trend in monthly_trends]),
        'wallet': json.dumps([float(trend['wallet']) for trend in monthly_trends]),
        'total': json.dumps([float(trend['total_revenue']) for trend in monthly_trends])
    }
    
    # Top revenue sources analysis
    revenue_sources = [
        {'name': 'Pharmacy', 'revenue': comprehensive_data['pharmacy_revenue']['total_revenue'], 'icon': 'fas fa-pills', 'color': 'primary'},
        {'name': 'Laboratory', 'revenue': comprehensive_data['laboratory_revenue']['total_revenue'], 'icon': 'fas fa-microscope', 'color': 'success'},
        {'name': 'Consultations', 'revenue': comprehensive_data['consultation_revenue']['total_revenue'], 'icon': 'fas fa-stethoscope', 'color': 'info'},
        {'name': 'Theatre', 'revenue': comprehensive_data['theatre_revenue']['total_revenue'], 'icon': 'fas fa-procedures', 'color': 'warning'},
        {'name': 'Admissions', 'revenue': comprehensive_data['admission_revenue']['total_revenue'], 'icon': 'fas fa-bed', 'color': 'danger'},
        {'name': 'General & Others', 'revenue': comprehensive_data['general_revenue']['total_revenue'], 'icon': 'fas fa-receipt', 'color': 'secondary'},
        {'name': 'Wallet', 'revenue': comprehensive_data['wallet_revenue']['total_revenue'], 'icon': 'fas fa-wallet', 'color': 'dark'}
    ]
    
    # Sort by revenue (highest first)
    revenue_sources.sort(key=lambda x: x['revenue'], reverse=True)
    
    # Performance metrics
    total_revenue = comprehensive_data['total_revenue']
    performance_metrics = {
        'total_transactions': sum([
            comprehensive_data['pharmacy_revenue']['total_payments'],
            comprehensive_data['laboratory_revenue']['total_payments'],
            comprehensive_data['consultation_revenue']['total_payments'],
            comprehensive_data['theatre_revenue']['total_payments'],
            comprehensive_data['admission_revenue']['total_payments'],
            comprehensive_data['general_revenue']['total_payments'],
            comprehensive_data['wallet_revenue']['total_transactions']
        ]),
        'average_transaction_value': total_revenue / max(1, sum([
            comprehensive_data['pharmacy_revenue']['total_payments'],
            comprehensive_data['laboratory_revenue']['total_payments'],
            comprehensive_data['consultation_revenue']['total_payments'],
            comprehensive_data['theatre_revenue']['total_payments'],
            comprehensive_data['admission_revenue']['total_payments'],
            comprehensive_data['general_revenue']['total_payments'],
            comprehensive_data['wallet_revenue']['total_transactions']
        ])),
        'days_in_period': (end_date - start_date).days + 1,
        'daily_average': total_revenue / max(1, (end_date - start_date).days + 1)
    }
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'comprehensive_data': comprehensive_data,
        'monthly_trends': monthly_trends,
        'daily_breakdown': [],
        'chart_data': chart_data,
        'revenue_sources': revenue_sources,
        'performance_metrics': performance_metrics,
        'include_daily_breakdown': False,
        'selected_departments': [],
        'page_title': 'Revenue Charts Test',
        'active_nav': 'pharmacy',
        
        # Individual department data for backward compatibility with template
        'pharmacy_revenue': comprehensive_data['pharmacy_revenue'],
        'lab_revenue': comprehensive_data['laboratory_revenue'],
        'consultation_revenue': comprehensive_data['consultation_revenue'],
        'theatre_revenue': comprehensive_data['theatre_revenue'],
        'admission_revenue': comprehensive_data['admission_revenue'],
        'general_revenue': comprehensive_data['general_revenue'],
        'wallet_revenue': comprehensive_data['wallet_revenue'],
    }
    
    return render(request, 'pharmacy/comprehensive_revenue_analysis.html', context)