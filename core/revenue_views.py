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
from django.db.models import Sum
from datetime import datetime, timedelta
from decimal import Decimal
import json
import csv

from .revenue_point_analyzer import RevenuePointBreakdownAnalyzer, RevenuePointFilterHelper
from .department_revenue_utils import DepartmentRevenueCalculator, RevenueComparisonAnalyzer

# Import models for revenue calculation
from billing.models import Invoice
from patients.models import WalletTransaction

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
    selected_month = request.GET.get('selected_month')
    
    # Determine date range based on filter
    if date_filter in ['current_month', 'previous_month'] and selected_month:
        # Use selected_month explicitly if provided (YYYY-MM)
        try:
            year, month = map(int, selected_month.split('-'))
            start_date = datetime(year, month, 1).date()
            # last day of month
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        except ValueError:
            start_date, end_date = _get_date_range(date_filter)
    elif date_filter == 'custom_range' and custom_start_date and custom_end_date:
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
    department = request.GET.get('department', 'all')

    # Get date range parameters (defaults to last 12 months)
    current_date = timezone.now().date()

    # Get start month/year (default to 12 months ago)
    default_start = current_date - timedelta(days=365)
    start_month = int(request.GET.get('start_month', default_start.month))
    start_year = int(request.GET.get('start_year', default_start.year))

    # Get end month/year (default to current month)
    end_month = int(request.GET.get('end_month', current_date.month))
    end_year = int(request.GET.get('end_year', current_date.year))

    try:
        # Calculate start and end dates
        start_date = datetime(start_year, start_month, 1).date()

        # Get last day of end month
        if end_month == 12:
            end_date = datetime(end_year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(end_year, end_month + 1, 1).date() - timedelta(days=1)

        # Calculate number of months between start and end
        months = (end_year - start_year) * 12 + (end_month - start_month) + 1

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
            'start_month': start_month,
            'start_year': start_year,
            'end_month': end_month,
            'end_year': end_year,
            'department': department,
            'start_date': start_date,
            'end_date': end_date,
            'page_title': 'Revenue Trends Analysis',
            'breadcrumb': 'Revenue Trends'
        }

        return render(request, 'core/revenue_trends.html', context)

    except Exception as e:
        messages.error(request, f"Error loading revenue trends: {str(e)}")
        # Include empty trends data to prevent JavaScript errors
        context = {
            'error': str(e),
            'trends': [],
            'trends_json': json.dumps([]),
            'start_month': start_month,
            'start_year': start_year,
            'end_month': end_month,
            'end_year': end_year,
            'department': department,
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
    department = request.GET.get('department', 'all')

    # Get date range parameters (defaults to last 12 months)
    current_date = timezone.now().date()

    # Get start month/year (default to 12 months ago)
    default_start = current_date - timedelta(days=365)
    start_month = int(request.GET.get('start_month', default_start.month))
    start_year = int(request.GET.get('start_year', default_start.year))

    # Get end month/year (default to current month)
    end_month = int(request.GET.get('end_month', current_date.month))
    end_year = int(request.GET.get('end_year', current_date.year))

    try:
        # Calculate start and end dates
        start_date = datetime(start_year, start_month, 1).date()

        # Get last day of end month
        if end_month == 12:
            end_date = datetime(end_year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(end_year, end_month + 1, 1).date() - timedelta(days=1)

        # Calculate number of months between start and end
        months = (end_year - start_year) * 12 + (end_month - start_month) + 1

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
            'start_month': start_month,
            'start_year': start_year,
            'end_month': end_month,
            'end_year': end_year,
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
            return _export_excel(analyzer, start_date, end_date, department_filter, request)
        elif export_format == 'pdf':
            return _export_pdf(analyzer, start_date, end_date, department_filter, request)
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
    """
    Get trend data for specific department.
    Returns data in format expected by revenue_trends template.
    """
    trends = []
    end_date = timezone.now().date()

    for i in range(months):
        # Calculate month date range (going backwards from current date)
        year = end_date.year
        month = end_date.month - i

        # Handle year rollover
        while month <= 0:
            month += 12
            year -= 1

        # Get first day of the month
        month_start = datetime(year, month, 1).date()

        # Get last day of the month
        if month == 12:
            month_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)

        # Get department data for month
        calc = DepartmentRevenueCalculator(month_start, month_end)

        # Initialize all departments to zero
        pharmacy_revenue = Decimal('0.00')
        lab_revenue = Decimal('0.00')
        consultation_revenue = Decimal('0.00')
        theatre_revenue = Decimal('0.00')
        admissions_revenue = Decimal('0.00')
        general_revenue = Decimal('0.00')
        wallet_revenue = Decimal('0.00')

        # Get specific department data
        try:
            if department == 'pharmacy':
                month_data = calc.get_pharmacy_detailed_revenue()
                pharmacy_revenue = month_data.get('total_revenue', Decimal('0.00'))
            elif department == 'laboratory':
                month_data = calc.get_laboratory_detailed_revenue()
                lab_revenue = month_data.get('total_revenue', Decimal('0.00'))
            elif department == 'consultation':
                month_data = calc.get_consultation_detailed_revenue()
                consultation_revenue = month_data.get('total_revenue', Decimal('0.00'))
            elif department == 'theatre':
                month_data = calc.get_theatre_detailed_revenue()
                theatre_revenue = month_data.get('total_revenue', Decimal('0.00'))
            elif department == 'inpatient' or department == 'admissions':
                month_data = calc.get_inpatient_detailed_revenue()
                admissions_revenue = month_data.get('total_revenue', Decimal('0.00'))
            elif department == 'general':
                # Get general billing revenue
                general_revenue = Invoice.objects.filter(
                    created_at__date__gte=month_start,
                    created_at__date__lte=month_end,
                    status='paid'
                ).exclude(
                    items__service__name__icontains='pharmacy'
                ).exclude(
                    items__service__name__icontains='lab'
                ).exclude(
                    items__service__name__icontains='consultation'
                ).exclude(
                    items__service__name__icontains='theatre'
                ).exclude(
                    items__service__name__icontains='admission'
                ).aggregate(
                    total=Sum('total_amount')
                )['total'] or Decimal('0.00')
            elif department == 'wallet':
                # Get wallet transactions
                wallet_revenue = WalletTransaction.objects.filter(
                    created_at__date__gte=month_start,
                    created_at__date__lte=month_end,
                    transaction_type='credit'
                ).aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0.00')
            else:
                # Handle specialty departments
                month_data = calc.get_specialty_department_detailed_revenue(department)
                general_revenue = month_data.get('total_revenue', Decimal('0.00'))
        except Exception as e:
            # Log error but continue with zero values
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting {department} revenue for {month_start}: {e}")

        # Calculate total revenue
        total_revenue = (
            pharmacy_revenue +
            lab_revenue +
            consultation_revenue +
            theatre_revenue +
            admissions_revenue +
            general_revenue +
            wallet_revenue
        )

        trends.append({
            'month': month_start,
            'total_revenue': total_revenue,
            'pharmacy': pharmacy_revenue,
            'laboratory': lab_revenue,
            'consultations': consultation_revenue,
            'theatre': theatre_revenue,
            'admissions': admissions_revenue,
            'general': general_revenue,
            'wallet': wallet_revenue
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


def _export_excel(analyzer, start_date, end_date, department_filter, request):
    """Export data as Excel (placeholder)"""
    # This would require openpyxl or xlsxwriter
    messages.info(request, "Excel export functionality coming soon")
    return redirect('core:revenue_point_dashboard')


def _export_pdf(analyzer, start_date, end_date, department_filter, request):
    """Export data as PDF (placeholder)"""
    # This would require reportlab integration
    messages.info(request, "PDF export functionality coming soon")
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