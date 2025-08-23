"""
Revenue Point Breakdown Integration with Existing Reporting System
Seamlessly integrates revenue analysis with HMS reporting infrastructure
while maintaining backward compatibility and existing functionality.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
import json

from reporting.models import Report, Dashboard, DashboardWidget, ReportExecution
from .revenue_point_analyzer import RevenuePointBreakdownAnalyzer, RevenuePointFilterHelper
from .department_revenue_utils import DepartmentRevenueCalculator


class RevenueReportGenerator:
    """
    Generates reports compatible with existing reporting system
    """
    
    @staticmethod
    def create_revenue_reports():
        """
        Create predefined revenue reports for the reporting system
        """
        reports = [
            {
                'name': 'Revenue Point Breakdown Summary',
                'description': 'Comprehensive breakdown of revenue by department and service point',
                'category': 'financial',
                'query': 'revenue_point_breakdown',
                'parameters': json.dumps({
                    'date_filter': 'current_month',
                    'department_filter': 'all',
                    'include_trends': True
                })
            },
            {
                'name': 'Clinical Services Revenue Analysis',
                'description': 'Detailed analysis of clinical services revenue including pharmacy, laboratory, and consultations',
                'category': 'clinical',
                'query': 'clinical_services_revenue',
                'parameters': json.dumps({
                    'date_filter': 'current_month',
                    'include_details': True
                })
            },
            {
                'name': 'Specialty Departments Performance',
                'description': 'Performance analysis of specialty departments including ANC, ENT, ICU, etc.',
                'category': 'operational',
                'query': 'specialty_departments_revenue',
                'parameters': json.dumps({
                    'date_filter': 'current_month',
                    'department_filter': 'specialty'
                })
            },
            {
                'name': 'Revenue Trends Analysis',
                'description': 'Monthly revenue trends across all departments',
                'category': 'financial',
                'query': 'revenue_trends',
                'parameters': json.dumps({
                    'months': 12,
                    'include_growth_rates': True
                })
            },
            {
                'name': 'Payment Method Distribution',
                'description': 'Analysis of revenue distribution by payment methods',
                'category': 'financial',
                'query': 'payment_method_analysis',
                'parameters': json.dumps({
                    'date_filter': 'current_month',
                    'include_percentages': True
                })
            },
            {
                'name': 'Department Comparison Report',
                'description': 'Comparative analysis of departmental revenue performance',
                'category': 'operational',
                'query': 'department_comparison',
                'parameters': json.dumps({
                    'date_filter': 'current_month',
                    'comparison_period': 'previous_month'
                })
            }
        ]
        
        created_reports = []
        for report_data in reports:
            report, created = Report.objects.get_or_create(
                name=report_data['name'],
                defaults={
                    'description': report_data['description'],
                    'category': report_data['category'],
                    'query': report_data['query'],
                    'parameters': report_data['parameters'],
                    'created_by_id': 1  # System user
                }
            )
            if created:
                created_reports.append(report)
        
        return created_reports
    
    @staticmethod
    def create_revenue_dashboard():
        """
        Create default revenue analysis dashboard
        """
        dashboard, created = Dashboard.objects.get_or_create(
            name='Revenue Point Analysis Dashboard',
            defaults={
                'description': 'Comprehensive revenue analysis dashboard with point breakdown',
                'is_default': False,
                'is_public': True,
                'created_by_id': 1  # System user
            }
        )
        
        if created:
            # Create widgets for the dashboard
            widgets = [
                {
                    'title': 'Total Revenue Summary',
                    'widget_type': 'table',
                    'position_x': 0,
                    'position_y': 0,
                    'width': 12,
                    'height': 3,
                    'report_query': 'revenue_summary'
                },
                {
                    'title': 'Revenue Distribution',
                    'widget_type': 'pie',
                    'position_x': 0,
                    'position_y': 3,
                    'width': 6,
                    'height': 4,
                    'report_query': 'revenue_distribution'
                },
                {
                    'title': 'Monthly Trends',
                    'widget_type': 'line',
                    'position_x': 6,
                    'position_y': 3,
                    'width': 6,
                    'height': 4,
                    'report_query': 'revenue_trends'
                },
                {
                    'title': 'Top Departments',
                    'widget_type': 'bar',
                    'position_x': 0,
                    'position_y': 7,
                    'width': 6,
                    'height': 4,
                    'report_query': 'top_departments'
                },
                {
                    'title': 'Clinical Services Breakdown',
                    'widget_type': 'table',
                    'position_x': 6,
                    'position_y': 7,
                    'width': 6,
                    'height': 4,
                    'report_query': 'clinical_services_breakdown'
                }
            ]
            
            for widget_data in widgets:
                # Create or get a dummy report for the widget
                report, _ = Report.objects.get_or_create(
                    name=f"Revenue Widget: {widget_data['title']}",
                    defaults={
                        'description': f"Data source for {widget_data['title']} widget",
                        'category': 'financial',
                        'query': widget_data['report_query'],
                        'created_by_id': 1
                    }
                )
                
                DashboardWidget.objects.create(
                    dashboard=dashboard,
                    report=report,
                    title=widget_data['title'],
                    widget_type=widget_data['widget_type'],
                    position_x=widget_data['position_x'],
                    position_y=widget_data['position_y'],
                    width=widget_data['width'],
                    height=widget_data['height']
                )
        
        return dashboard


class RevenueReportExecutor:
    """
    Executes revenue reports for the reporting system
    """
    
    def __init__(self, user=None):
        self.user = user
    
    def execute_report(self, report, parameters_json=None):
        """
        Execute a revenue report and return formatted results
        Compatible with existing reporting system
        """
        try:
            # Parse parameters
            parameters = {}
            if parameters_json:
                parameters = json.loads(parameters_json) if isinstance(parameters_json, str) else parameters_json
            
            # Default parameters
            date_filter = parameters.get('date_filter', 'current_month')
            start_date, end_date = self._get_date_range(date_filter, parameters)
            
            # Initialize analyzer
            analyzer = RevenuePointBreakdownAnalyzer(start_date, end_date)
            dept_calculator = DepartmentRevenueCalculator(start_date, end_date)
            
            # Execute based on query type
            if report.query == 'revenue_point_breakdown':
                result = self._execute_breakdown_report(analyzer, parameters)
            elif report.query == 'clinical_services_revenue':
                result = self._execute_clinical_services_report(dept_calculator, parameters)
            elif report.query == 'specialty_departments_revenue':
                result = self._execute_specialty_departments_report(analyzer, parameters)
            elif report.query == 'revenue_trends':
                result = self._execute_trends_report(analyzer, parameters)
            elif report.query == 'payment_method_analysis':
                result = self._execute_payment_method_report(analyzer, parameters)
            elif report.query == 'department_comparison':
                result = self._execute_comparison_report(analyzer, parameters)
            else:
                # Handle widget-specific queries
                result = self._execute_widget_query(analyzer, dept_calculator, report.query, parameters)
            
            # Log execution
            ReportExecution.objects.create(
                report=report,
                parameters=json.dumps(parameters),
                result_count=len(result.get('data', [])),
                executed_by=self.user
            )
            
            return result
            
        except Exception as e:
            return {
                'error': str(e),
                'data': [],
                'columns': [],
                'rows': []
            }
    
    def _execute_breakdown_report(self, analyzer, parameters):
        """Execute revenue point breakdown report"""
        breakdown = analyzer.get_revenue_point_breakdown(include_trends=True)
        
        # Format for reporting system
        data = []
        columns = ['Category', 'Revenue (₦)', 'Percentage (%)', 'Transactions']
        
        # Add summary data
        summary = breakdown.get('summary_by_category', {})
        for category, cat_data in summary.items():
            if category != 'grand_total':
                data.append([
                    category.replace('_', ' ').title(),
                    float(cat_data.get('revenue', 0)),
                    float(cat_data.get('percentage', 0)),
                    cat_data.get('transactions', 0)
                ])
        
        return {
            'data': data,
            'columns': columns,
            'rows': data,
            'summary': {
                'total_revenue': float(breakdown['total_revenue']),
                'date_range': breakdown['date_range']
            }
        }
    
    def _execute_clinical_services_report(self, dept_calculator, parameters):
        """Execute clinical services revenue report"""
        pharmacy = dept_calculator.get_pharmacy_detailed_revenue()
        laboratory = dept_calculator.get_laboratory_detailed_revenue()
        consultation = dept_calculator.get_consultation_detailed_revenue()
        theatre = dept_calculator.get_theatre_detailed_revenue()
        
        columns = ['Service', 'Revenue (₦)', 'Transactions', 'Avg Transaction (₦)', 'Details']
        data = [
            ['Pharmacy', float(pharmacy['total_revenue']), pharmacy.get('total_payments', 0), 
             float(pharmacy.get('avg_prescription_value', 0)), f"Prescriptions: {pharmacy.get('total_dispensed', 0)}"],
            ['Laboratory', float(laboratory['total_revenue']), laboratory.get('total_payments', 0),
             float(laboratory.get('avg_test_value', 0)), f"Tests: {laboratory.get('total_requests', 0)}"],
            ['Consultations', float(consultation['total_revenue']), consultation.get('total_payments', 0),
             float(consultation.get('avg_consultation_fee', 0)), f"Consultations: {consultation.get('total_payments', 0)}"],
            ['Theatre', float(theatre['total_revenue']), theatre.get('total_payments', 0),
             float(theatre.get('avg_surgery_fee', 0)), f"Surgeries: {theatre.get('total_payments', 0)}"]
        ]
        
        return {
            'data': data,
            'columns': columns,
            'rows': data
        }
    
    def _execute_specialty_departments_report(self, analyzer, parameters):
        """Execute specialty departments report"""
        breakdown = analyzer.get_revenue_point_breakdown()
        specialty = breakdown.get('specialty_departments', {})
        
        columns = ['Department', 'Revenue (₦)', 'Records', 'Revenue per Record (₦)']
        data = []
        
        for dept_name, dept_data in specialty.items():
            avg_per_record = 0
            if dept_data.get('records', 0) > 0:
                avg_per_record = dept_data.get('revenue', 0) / dept_data.get('records', 1)
            
            data.append([
                dept_name.replace('_', ' ').title(),
                float(dept_data.get('revenue', 0)),
                dept_data.get('records', 0),
                float(avg_per_record)
            ])
        
        return {
            'data': data,
            'columns': columns,
            'rows': data
        }
    
    def _execute_trends_report(self, analyzer, parameters):
        """Execute revenue trends report"""
        months = parameters.get('months', 12)
        trends = analyzer.get_monthly_trends(months)
        
        columns = ['Month', 'Total Revenue (₦)', 'Pharmacy (₦)', 'Laboratory (₦)', 'Consultations (₦)']
        data = []
        
        for trend in trends:
            data.append([
                trend['month'],
                float(trend['total_revenue']),
                float(trend['pharmacy']),
                float(trend['laboratory']),
                float(trend['consultations'])
            ])
        
        return {
            'data': data,
            'columns': columns,
            'rows': data
        }
    
    def _execute_payment_method_report(self, analyzer, parameters):
        """Execute payment method analysis report"""
        breakdown = analyzer.get_revenue_point_breakdown()
        payment_methods = breakdown.get('payment_method_breakdown', {})
        
        columns = ['Payment Method', 'Amount (₦)', 'Count', 'Percentage (%)']
        data = []
        
        total_amount = sum([method_data.get('amount', 0) for method_data in payment_methods.values()])
        
        for method, method_data in payment_methods.items():
            percentage = 0
            if total_amount > 0:
                percentage = (method_data.get('amount', 0) / total_amount) * 100
            
            data.append([
                method.replace('_', ' ').title(),
                float(method_data.get('amount', 0)),
                method_data.get('count', 0),
                round(percentage, 2)
            ])
        
        return {
            'data': data,
            'columns': columns,
            'rows': data
        }
    
    def _execute_comparison_report(self, analyzer, parameters):
        """Execute department comparison report"""
        # This would need comparison logic implementation
        return {
            'data': [],
            'columns': ['Department', 'Current Period (₦)', 'Previous Period (₦)', 'Growth (%)'],
            'rows': []
        }
    
    def _execute_widget_query(self, analyzer, dept_calculator, query, parameters):
        """Execute widget-specific queries"""
        if query == 'revenue_summary':
            breakdown = analyzer.get_revenue_point_breakdown()
            return {
                'data': [[
                    'Total Revenue',
                    float(breakdown['total_revenue']),
                    'Current Period'
                ]],
                'columns': ['Metric', 'Value (₦)', 'Period'],
                'rows': [[
                    'Total Revenue',
                    float(breakdown['total_revenue']),
                    'Current Period'
                ]]
            }
        elif query == 'revenue_distribution':
            breakdown = analyzer.get_revenue_point_breakdown()
            summary = breakdown.get('summary_by_category', {})
            
            data = []
            for category, cat_data in summary.items():
                if category != 'grand_total':
                    data.append([
                        category.replace('_', ' ').title(),
                        float(cat_data.get('revenue', 0))
                    ])
            
            return {
                'data': data,
                'columns': ['Category', 'Revenue'],
                'rows': data
            }
        else:
            # Default empty result
            return {
                'data': [],
                'columns': [],
                'rows': []
            }
    
    def _get_date_range(self, date_filter, parameters):
        """Get date range based on filter"""
        if date_filter == 'custom_range':
            start_date = parameters.get('start_date')
            end_date = parameters.get('end_date')
            if start_date and end_date:
                return start_date, end_date
        
        # Use helper to get predefined ranges
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


@login_required
def execute_revenue_report(request, report_id):
    """
    View to execute revenue reports for the reporting system
    Compatible with existing report execution interface
    """
    report = get_object_or_404(Report, id=report_id)
    parameters = request.GET.dict()
    
    executor = RevenueReportExecutor(user=request.user)
    result = executor.execute_report(report, parameters)
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse(result)
    
    # Return HTML view compatible with existing reporting templates
    context = {
        'report': report,
        'result': result,
        'parameters': parameters
    }
    
    return render(request, 'reporting/revenue_report_result.html', context)


@login_required  
def revenue_widget_data(request, widget_id):
    """
    API endpoint for revenue widget data
    Compatible with existing dashboard widget system
    """
    widget = get_object_or_404(DashboardWidget, id=widget_id)
    parameters = request.GET.dict()
    
    if widget.report:
        executor = RevenueReportExecutor(user=request.user)
        result = executor.execute_report(widget.report, parameters)
        
        # Format for widget consumption
        widget_data = {
            'type': widget.widget_type,
            'title': widget.title,
            'data': result.get('data', []),
            'columns': result.get('columns', []),
            'summary': result.get('summary', {})
        }
        
        return JsonResponse(widget_data)
    
    return JsonResponse({'error': 'No report assigned to widget'})


def initialize_revenue_reporting():
    """
    Initialize revenue reporting integration
    Creates default reports and dashboard
    """
    try:
        # Create reports
        reports = RevenueReportGenerator.create_revenue_reports()
        
        # Create dashboard
        dashboard = RevenueReportGenerator.create_revenue_dashboard()
        
        return {
            'success': True,
            'reports_created': len(reports),
            'dashboard_created': dashboard is not None
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }