"""
Revenue Point Breakdown Views for HMS
Provides comprehensive revenue analysis views while maintaining
integration with existing reporting system.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
from decimal import Decimal
import json
import csv

from .revenue_point_analyzer import RevenuePointBreakdownAnalyzer, RevenuePointFilterHelper
from .department_revenue_utils import DepartmentRevenueCalculator, RevenueComparisonAnalyzer

# Import existing reporting components for compatibility
from reporting.models import Report
# from reporting.forms import ReportFilterForm  # This form doesn't exist, commented out


@login_required
def revenue_point_dashboard(request):
    """
    Main revenue point breakdown dashboard
    Integrates with existing dashboard while adding new functionality
    """
    # Get filter parameters
    date_filter = request.GET.get('date_filter', 'current_month')
    department_filter = request.GET.get('department_filter', 'all')
    payment_method_filter = request.GET.get('payment_method_filter', 'all')
    custom_start_date = request.GET.get('start_date')
    custom_end_date = request.GET.get('end_date')
    
    # Determine date range based on filter
    if date_filter == 'custom_range' and custom_start_date and custom_end_date:
        start_date = datetime.strptime(custom_start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(custom_end_date, '%Y-%m-%d').date()
    else:
        start_date, end_date = _get_date_range(date_filter)
    
    # Initialize analyzer
    analyzer = RevenuePointBreakdownAnalyzer(start_date, end_date)
    
    try:
        # Get comprehensive breakdown
        breakdown_data = analyzer.get_revenue_point_breakdown(include_trends=True)

        # Debug: Print data structure
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Revenue breakdown data keys: {breakdown_data.keys()}")
        logger.info(f"Has trends: {'trends' in breakdown_data}")
        if 'trends' in breakdown_data:
            logger.info(f"Trends data: {breakdown_data['trends']}")

        # Get department-specific calculator for detailed analysis
        dept_calculator = DepartmentRevenueCalculator(start_date, end_date)
        
        # Enhanced data for dashboard
        enhanced_data = {
            'pharmacy_details': dept_calculator.get_pharmacy_detailed_revenue(),
            'laboratory_details': dept_calculator.get_laboratory_detailed_revenue(),
            'consultation_details': dept_calculator.get_consultation_detailed_revenue(),
            'theatre_details': dept_calculator.get_theatre_detailed_revenue(),
            'inpatient_details': dept_calculator.get_inpatient_detailed_revenue()
        }
        
        # Get comparison with previous period
        previous_start, previous_end = _get_previous_period(start_date, end_date)
        comparison_analyzer = RevenueComparisonAnalyzer(
            start_date, end_date, previous_start, previous_end
        )
        comparison_data = comparison_analyzer.get_period_comparison()
        
        # Prepare context
        context = {
            'breakdown_data': breakdown_data,
            'enhanced_data': enhanced_data,
            'comparison_data': comparison_data,
            'date_filter': date_filter,
            'department_filter': department_filter,
            'payment_method_filter': payment_method_filter,
            'start_date': start_date,
            'end_date': end_date,
            'date_filter_options': RevenuePointFilterHelper.get_filter_options(),
            'department_filter_options': RevenuePointFilterHelper.get_department_filter_options(),
            'payment_method_options': RevenuePointFilterHelper.get_payment_method_options(),
            'export_format_options': RevenuePointFilterHelper.get_export_format_options(),
            'page_title': 'Revenue Point Breakdown Analysis',
            'breadcrumb': 'Revenue Analysis'
        }
        
    except Exception as e:
        messages.error(request, f"Error loading revenue data: {str(e)}")
        context = {
            'error': str(e),
            'date_filter_options': RevenuePointFilterHelper.get_filter_options(),
            'department_filter_options': RevenuePointFilterHelper.get_department_filter_options(),
            'payment_method_options': RevenuePointFilterHelper.get_payment_method_options()
        }
    
    return render(request, 'core/revenue_point_dashboard.html', context)


@login_required
@require_http_methods(["GET"])
def revenue_point_api(request):
    """
    API endpoint for revenue point data
    Returns JSON data for AJAX requests
    """
    # Get parameters
    date_filter = request.GET.get('date_filter', 'current_month')
    department = request.GET.get('department', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    try:
        # Determine date range
        if date_filter == 'custom_range' and start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            start_date, end_date = _get_date_range(date_filter)
        
        # Initialize analyzer
        analyzer = RevenuePointBreakdownAnalyzer(start_date, end_date)
        
        if department == 'all':
            # Get full breakdown
            data = analyzer.get_revenue_point_breakdown(include_trends=True)
        else:
            # Get specific department data
            dept_calculator = DepartmentRevenueCalculator(start_date, end_date)
            
            if department == 'pharmacy':
                data = dept_calculator.get_pharmacy_detailed_revenue()
            elif department == 'laboratory':
                data = dept_calculator.get_laboratory_detailed_revenue()
            elif department == 'consultation':
                data = dept_calculator.get_consultation_detailed_revenue()
            elif department == 'theatre':
                data = dept_calculator.get_theatre_detailed_revenue()
            elif department == 'inpatient':
                data = dept_calculator.get_inpatient_detailed_revenue()
            else:
                data = dept_calculator.get_specialty_department_detailed_revenue(department)
        
        # Convert Decimal to string for JSON serialization
        data = _convert_decimals_for_json(data)
        
        return JsonResponse({
            'success': True,
            'data': data,
            'date_range': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["GET"])
def revenue_trends_view(request):
    """
    Revenue trends page with charts and data visualization
    """
    months = int(request.GET.get('months', 12))
    department = request.GET.get('department', 'all')
    
    try:
        # Get current date for trend calculation
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30 * months)
        
        analyzer = RevenuePointBreakdownAnalyzer(start_date, end_date)
        
        if department == 'all':
            # Get monthly trends for all departments
            trends = analyzer.get_monthly_trends(months)
        else:
            # Get trends for specific department
            trends = _get_department_trends(department, months)
        
        # Convert for JSON
        trends_json = _convert_decimals_for_json(trends)
        
        context = {
            'trends': trends,
            'trends_json': json.dumps(trends_json),
            'months': months,
            'department': department,
            'start_date': start_date,
            'end_date': end_date,
            'page_title': 'Revenue Trends Analysis',
            'breadcrumb': 'Revenue Trends'
        }
        
        return render(request, 'core/revenue_trends.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading revenue trends: {str(e)}")
        context = {
            'error': str(e),
            'page_title': 'Revenue Trends Analysis',
            'breadcrumb': 'Revenue Trends'
        }
        return render(request, 'core/revenue_trends.html', context)


@login_required
@require_http_methods(["GET"])
def revenue_trends_api(request):
    """
    API endpoint for revenue trend data
    Returns JSON data for charts
    """
    months = int(request.GET.get('months', 12))
    department = request.GET.get('department', 'all')
    
    try:
        # Get current date for trend calculation
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30 * months)
        
        analyzer = RevenuePointBreakdownAnalyzer(start_date, end_date)
        
        if department == 'all':
            # Get monthly trends for all departments
            trends = analyzer.get_monthly_trends(months)
        else:
            # Get trends for specific department
            trends = _get_department_trends(department, months)
        
        # Convert for JSON
        trends = _convert_decimals_for_json(trends)
        
        return JsonResponse({
            'success': True,
            'trends': trends,
            'months': months,
            'department': department
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["GET"])
def export_revenue_breakdown(request):
    """
    Export revenue breakdown data in various formats
    """
    export_format = request.GET.get('format', 'csv')
    date_filter = request.GET.get('date_filter', 'current_month')
    department_filter = request.GET.get('department_filter', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    try:
        # Determine date range
        if date_filter == 'custom_range' and start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            start_date, end_date = _get_date_range(date_filter)
        
        # Initialize analyzer
        analyzer = RevenuePointBreakdownAnalyzer(start_date, end_date)
        
        if export_format == 'csv':
            return _export_csv(analyzer, start_date, end_date, department_filter)
        elif export_format == 'excel':
            return _export_excel(analyzer, start_date, end_date, department_filter)
        elif export_format == 'pdf':
            return _export_pdf(analyzer, start_date, end_date, department_filter)
        else:
            messages.error(request, 'Invalid export format')
            return redirect('core:revenue_point_dashboard')
            
    except Exception as e:
        messages.error(request, f"Export failed: {str(e)}")
        return redirect('core:revenue_point_dashboard')


@login_required
def department_revenue_detail(request, department):
    """
    Detailed view for specific department revenue
    """
    # Get date range
    date_filter = request.GET.get('date_filter', 'current_month')
    start_date, end_date = _get_date_range(date_filter)
    
    try:
        # Get department-specific calculator
        dept_calculator = DepartmentRevenueCalculator(start_date, end_date)
        
        # Get detailed data based on department
        if department == 'pharmacy':
            detail_data = dept_calculator.get_pharmacy_detailed_revenue()
            template = 'core/pharmacy_revenue_detail.html'
        elif department == 'laboratory':
            detail_data = dept_calculator.get_laboratory_detailed_revenue()
            template = 'core/laboratory_revenue_detail.html'
        elif department == 'consultation':
            detail_data = dept_calculator.get_consultation_detailed_revenue()
            template = 'core/consultation_revenue_detail.html'
        elif department == 'theatre':
            detail_data = dept_calculator.get_theatre_detailed_revenue()
            template = 'core/theatre_revenue_detail.html'
        elif department == 'inpatient':
            detail_data = dept_calculator.get_inpatient_detailed_revenue()
            template = 'core/inpatient_revenue_detail.html'
        else:
            detail_data = dept_calculator.get_specialty_department_detailed_revenue(department)
            template = 'core/specialty_revenue_detail.html'
        
        # Get comparison data
        previous_start, previous_end = _get_previous_period(start_date, end_date)
        previous_calculator = DepartmentRevenueCalculator(previous_start, previous_end)
        
        if department == 'pharmacy':
            previous_data = previous_calculator.get_pharmacy_detailed_revenue()
        elif department == 'laboratory':
            previous_data = previous_calculator.get_laboratory_detailed_revenue()
        else:
            previous_data = {'total_revenue': Decimal('0.00')}
        
        # Calculate growth
        growth_rate = _calculate_growth_rate(
            detail_data.get('total_revenue', Decimal('0.00')),
            previous_data.get('total_revenue', Decimal('0.00'))
        )
        
        context = {
            'department': department,
            'department_name': department.replace('_', ' ').title(),
            'detail_data': detail_data,
            'previous_data': previous_data,
            'growth_rate': growth_rate,
            'date_filter': date_filter,
            'start_date': start_date,
            'end_date': end_date,
            'date_filter_options': RevenuePointFilterHelper.get_filter_options(),
            'page_title': f'{department.title()} Revenue Analysis',
            'breadcrumb': f'{department.title()} Revenue'
        }
        
        return render(request, template, context)
        
    except Exception as e:
        messages.error(request, f"Error loading {department} revenue data: {str(e)}")
        return redirect('core:revenue_point_dashboard')


@login_required
@cache_page(60 * 15)  # Cache for 15 minutes
def revenue_summary_widget(request):
    """
    Widget view for revenue summary (for dashboard integration)
    """
    try:
        # Get current month data
        start_date, end_date = RevenuePointFilterHelper.get_current_month()
        analyzer = RevenuePointBreakdownAnalyzer(start_date, end_date)
        
        # Get summary data
        breakdown = analyzer.get_revenue_point_breakdown()
        
        # Prepare widget data
        widget_data = {
            'total_revenue': breakdown['total_revenue'],
            'clinical_revenue': sum([s['revenue'] for s in breakdown['clinical_services'].values()]),
            'support_revenue': sum([s['revenue'] for s in breakdown['support_services'].values()]),
            'specialty_revenue': sum([s['revenue'] for s in breakdown['specialty_departments'].values()]),
            'top_department': _get_top_department(breakdown),
            'growth_indicator': _get_growth_indicator(start_date, end_date)
        }
        
        return render(request, 'core/revenue_summary_widget.html', {
            'widget_data': widget_data,
            'date_range': f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
        })
        
    except Exception as e:
        return render(request, 'core/revenue_summary_widget.html', {
            'error': str(e)
        })


# Helper functions

def _get_date_range(date_filter):
    """Get date range based on filter"""
    if date_filter == 'current_month':
        return RevenuePointFilterHelper.get_current_month()
    elif date_filter == 'previous_month':
        return RevenuePointFilterHelper.get_previous_month()
    elif date_filter == 'last_3_months':
        return RevenuePointFilterHelper.get_last_n_months(3)
    elif date_filter == 'last_6_months':
        return RevenuePointFilterHelper.get_last_n_months(6)
    elif date_filter == 'last_12_months':
        return RevenuePointFilterHelper.get_last_n_months(12)
    elif date_filter == 'year_to_date':
        return RevenuePointFilterHelper.get_year_to_date()
    else:
        return RevenuePointFilterHelper.get_current_month()


def _get_previous_period(start_date, end_date):
    """Get previous period dates for comparison"""
    period_length = (end_date - start_date).days
    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_length)
    return previous_start, previous_end


def _convert_decimals_for_json(data):
    """Convert Decimal and date objects to strings for JSON serialization"""
    from datetime import date, datetime
    
    if isinstance(data, dict):
        return {key: _convert_decimals_for_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_convert_decimals_for_json(item) for item in data]
    elif isinstance(data, Decimal):
        return str(data)
    elif isinstance(data, (date, datetime)):
        return data.isoformat() if isinstance(data, datetime) else data.strftime('%Y-%m-%d')
    else:
        return data


def _get_department_trends(department, months):
    """Get trend data for specific department"""
    trends = []
    end_date = timezone.now().date()
    
    for i in range(months):
        # Calculate month date range
        month_end = end_date.replace(day=1) - timedelta(days=30*i)
        month_start = month_end.replace(day=1)
        if month_end.month == 12:
            month_end = month_end.replace(year=month_end.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_end.replace(month=month_end.month + 1, day=1) - timedelta(days=1)
        
        # Get department data for month
        calc = DepartmentRevenueCalculator(month_start, month_end)
        
        if department == 'pharmacy':
            month_data = calc.get_pharmacy_detailed_revenue()
        elif department == 'laboratory':
            month_data = calc.get_laboratory_detailed_revenue()
        elif department == 'consultation':
            month_data = calc.get_consultation_detailed_revenue()
        elif department == 'theatre':
            month_data = calc.get_theatre_detailed_revenue()
        elif department == 'inpatient':
            month_data = calc.get_inpatient_detailed_revenue()
        else:
            month_data = calc.get_specialty_department_detailed_revenue(department)
        
        trends.append({
            'month': month_start.strftime('%b %Y'),
            'month_date': month_start,
            'revenue': month_data.get('total_revenue', Decimal('0.00'))
        })
    
    return list(reversed(trends))  # Return chronological order


def _export_csv(analyzer, start_date, end_date, department_filter):
    """Export data as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="revenue_breakdown_{start_date}_{end_date}.csv"'
    
    # Use existing CSV export from analyzer
    csv_content = analyzer.export_revenue_breakdown_csv()
    response.write(csv_content)
    
    return response


def _export_excel(analyzer, start_date, end_date, department_filter):
    """Export data as Excel (placeholder)"""
    # This would require openpyxl or xlsxwriter
    messages.info("Excel export functionality coming soon")
    return redirect('core:revenue_point_dashboard')


def _export_pdf(analyzer, start_date, end_date, department_filter):
    """Export data as PDF (placeholder)"""
    # This would require reportlab integration
    messages.info("PDF export functionality coming soon")
    return redirect('core:revenue_point_dashboard')


def _get_top_department(breakdown):
    """Get the top performing department"""
    try:
        all_departments = {}
        all_departments.update(breakdown['clinical_services'])
        all_departments.update(breakdown['support_services'])
        all_departments.update(breakdown['specialty_departments'])
        
        if all_departments:
            top_dept = max(all_departments.items(), key=lambda x: x[1]['revenue'])
            return {
                'name': top_dept[0].replace('_', ' ').title(),
                'revenue': top_dept[1]['revenue']
            }
    except:
        pass
    
    return {'name': 'N/A', 'revenue': Decimal('0.00')}


def _get_growth_indicator(start_date, end_date):
    """Get growth indicator for current vs previous period"""
    try:
        # Compare with previous period
        previous_start, previous_end = _get_previous_period(start_date, end_date)
        
        current_analyzer = RevenuePointBreakdownAnalyzer(start_date, end_date)
        previous_analyzer = RevenuePointBreakdownAnalyzer(previous_start, previous_end)
        
        current_revenue = current_analyzer.get_revenue_point_breakdown()['total_revenue']
        previous_revenue = previous_analyzer.get_revenue_point_breakdown()['total_revenue']
        
        return _calculate_growth_rate(current_revenue, previous_revenue)
    except:
        return 0.0


def _calculate_growth_rate(current, previous):
    """Calculate growth rate between two values"""
    if previous and previous > 0:
        return round(((current - previous) / previous) * 100, 2)
    return 0.0