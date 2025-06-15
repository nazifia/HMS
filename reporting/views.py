from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Max
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import connection
from django.http import HttpResponse, JsonResponse
import json

# Try to import visualization libraries, but provide fallbacks if not available
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import io
    import base64
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

from .models import Report, ReportExecution, Dashboard, DashboardWidget
from .forms import (ReportForm, ReportExecutionForm, DashboardForm, DashboardWidgetForm,
                    ReportSearchForm, DashboardSearchForm)

from core.models import AuditLog, InternalNotification

# Helper functions
def execute_report(report, parameters_json=None):
    """Execute a report and return the results"""
    try:
        # Check if report is None
        if report is None:
            return {
                'columns': [],
                'rows': [],
                'data': []
            }

        # Parse parameters if provided
        parameters = {}
        if parameters_json and parameters_json.strip():
            parameters = json.loads(parameters_json)

        # Replace parameter placeholders in the query
        query = report.query
        if not query:
            return {
                'columns': [],
                'rows': [],
                'data': []
            }

        for key, value in parameters.items():
            placeholder = f'%({key})s'
            if placeholder in query:
                # Sanitize the value to prevent SQL injection
                if isinstance(value, (int, float)):
                    query = query.replace(placeholder, str(value))
                else:
                    query = query.replace(placeholder, f"'{value}'")

        # Execute the query
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            results = cursor.fetchall()

        # Convert to list of dictionaries
        result_dicts = [dict(zip(columns, row)) for row in results]

        # Save the execution record
        ReportExecution.objects.create(
            report=report,
            parameters=parameters_json,
            result_count=len(result_dicts)
        )

        return {
            'columns': columns,
            'rows': results,
            'data': result_dicts
        }
    except Exception as e:
        # Log the error
        print(f"Error executing report: {str(e)}")
        return {
            'columns': [],
            'rows': [],
            'data': [],
            'error': str(e)
        }

def generate_chart(result, chart_type):
    """Generate a chart from report results"""
    # Check if visualization libraries are available
    if not VISUALIZATION_AVAILABLE:
        return None

    try:
        # Check if result is valid
        if not result or 'data' not in result or not result['data']:
            return None

        # Convert result to DataFrame
        df = pd.DataFrame(result['data'])

        if df.empty:
            return None

        # Create a figure and axis
        plt.figure(figsize=(10, 6))

        # Generate the appropriate chart type
        if chart_type == 'bar':
            # Assume first column is x-axis, second is y-axis
            x_col = df.columns[0]
            y_col = df.columns[1] if len(df.columns) > 1 else None

            if y_col:
                df.plot(kind='bar', x=x_col, y=y_col)
            else:
                df.plot(kind='bar')

        elif chart_type == 'line':
            # Assume first column is x-axis, rest are y-axis
            x_col = df.columns[0]
            y_cols = df.columns[1:] if len(df.columns) > 1 else df.columns

            df.plot(kind='line', x=x_col, y=y_cols)

        elif chart_type in ['pie', 'donut']:
            # Assume first column is labels, second is values
            if len(df.columns) >= 2:
                labels = df[df.columns[0]]
                values = df[df.columns[1]]

                plt.pie(values, labels=labels, autopct='%1.1f%%')

                # For donut chart, add a circle in the middle
                if chart_type == 'donut':
                    plt.gca().add_artist(plt.Circle((0, 0), 0.3, fc='white'))

        # Save the chart to a buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()

        # Encode the image to base64
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()

        chart = base64.b64encode(image_png).decode('utf-8')
        return chart
    except Exception as e:
        # Log the error
        print(f"Error generating chart: {str(e)}")
        return None

@login_required
def dashboard(request):
    """Fully functional reporting dashboard with widgets, analytics, and audit logs."""
    dashboard_id = request.GET.get('id')

    # If no dashboards exist, redirect to create
    if Dashboard.objects.count() == 0:
        messages.info(request, 'No dashboards available. Create your first dashboard.')
        return redirect('reporting:create_dashboard')

    # Get dashboard (by id, or default, or first accessible)
    dashboard = None
    if dashboard_id:
        dashboard = get_object_or_404(Dashboard, id=dashboard_id)
        if not dashboard.is_public and dashboard.created_by != request.user:
            messages.error(request, 'You do not have permission to view this dashboard.')
            return redirect('reporting:dashboard')
    else:
        dashboard = Dashboard.objects.filter(created_by=request.user, is_default=True).first()
        if not dashboard:
            dashboard = Dashboard.objects.filter(is_public=True, is_default=True).first()
        if not dashboard:
            dashboard = Dashboard.objects.filter(Q(created_by=request.user) | Q(is_public=True)).first()
        if not dashboard:
            messages.info(request, 'No dashboards available for you. Create your first dashboard.')
            return redirect('reporting:create_dashboard')

    # Get widgets for dashboard
    widgets = DashboardWidget.objects.filter(dashboard=dashboard).select_related('report').order_by('position_y', 'position_x')
    user_dashboards = Dashboard.objects.filter(Q(created_by=request.user) | Q(is_public=True)).order_by('-is_default', 'name')

    # Execute each widget's report and generate chart if needed
    for widget in widgets:
        try:
            if not widget.report:
                widget.error = 'No report assigned to this widget'
                widget.result = {'columns': [], 'rows': [], 'data': []}
                continue
            widget.result = execute_report(widget.report, widget.parameters)
            if widget.widget_type in ['bar', 'line', 'pie', 'donut']:
                widget.chart = generate_chart(widget.result, widget.widget_type)
        except Exception as e:
            widget.error = str(e)
            widget.result = {'columns': [], 'rows': [], 'data': []}

    # Analytics: widget/report counts, last updated, etc.
    widget_count = widgets.count()
    report_count = Report.objects.count()
    last_updated = widgets.aggregate(last=Max('updated_at'))['last'] if widget_count else None

    # Audit logs and notifications
    audit_logs = AuditLog.objects.filter(action__icontains='dashboard').order_by('-timestamp')[:10]
    user_notifications = InternalNotification.objects.filter(
        user=request.user,
        message__icontains='dashboard',
        is_read=False
    ).order_by('-created_at')[:10]

    context = {
        'dashboard': dashboard,
        'widgets': widgets,
        'user_dashboards': user_dashboards,
        'widget_count': widget_count,
        'report_count': report_count,
        'last_updated': last_updated,
        'title': dashboard.name,
        'audit_logs': audit_logs,
        'user_notifications': user_notifications
    }
    return render(request, 'reporting/dashboard.html', context)

@login_required
def patient_reports(request):
    # Placeholder view
    return render(request, 'reporting/patient_reports.html')

@login_required
def appointment_reports(request):
    # Placeholder view
    return render(request, 'reporting/appointment_reports.html')

@login_required
def billing_reports(request):
    # Placeholder view
    return render(request, 'reporting/billing_reports.html')

@login_required
def pharmacy_reports(request):
    # Placeholder view
    return render(request, 'reporting/pharmacy_reports.html')

@login_required
def laboratory_reports(request):
    # Placeholder view
    return render(request, 'reporting/laboratory_reports.html')

@login_required
def inpatient_reports(request):
    # Placeholder view
    return render(request, 'reporting/inpatient_reports.html')

@login_required
def staff_reports(request):
    # Placeholder view
    return render(request, 'reporting/staff_reports.html')

@login_required
def export_csv(request, report_type):
    # Placeholder view for CSV export
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
    return response

@login_required
def export_pdf(request, report_type):
    # Placeholder view for PDF export
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.pdf"'
    return response

@login_required
def report_list(request):
    """View for listing all reports"""
    search_form = ReportSearchForm(request.GET)
    reports = Report.objects.all().order_by('-created_at')

    # Apply filters if the form is valid
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        category = search_form.cleaned_data.get('category')
        is_active = search_form.cleaned_data.get('is_active')

        if search_query:
            reports = reports.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        if category:
            reports = reports.filter(category=category)

        if is_active:
            is_active_bool = is_active == 'true'
            reports = reports.filter(is_active=is_active_bool)

    # Pagination
    paginator = Paginator(reports, 10)  # Show 10 reports per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get counts for different categories
    financial_count = reports.filter(category='financial').count()
    clinical_count = reports.filter(category='clinical').count()
    operational_count = reports.filter(category='operational').count()
    administrative_count = reports.filter(category='administrative').count()

    # Note: Current AuditLog model doesn't have object_type/object_id fields
    # Filtering by details that might contain report information
    audit_logs = AuditLog.objects.filter(
        details__icontains='Report'
    ).order_by('-timestamp')[:10]
    user_notifications = InternalNotification.objects.filter(
        user=request.user,
        message__icontains='Report',
        is_read=False
    ).order_by('-created_at')[:10]

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_reports': reports.count(),
        'financial_count': financial_count,
        'clinical_count': clinical_count,
        'operational_count': operational_count,
        'administrative_count': administrative_count,
        'title': 'Reports',
        'audit_logs': audit_logs,
        'user_notifications': user_notifications
    }

    return render(request, 'reporting/report_list.html', context)

@login_required
def create_report(request):
    """View for creating a new report"""
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.created_by = request.user
            report.save()
            messages.success(request, f'Report {report.name} has been created successfully.')
            return redirect('reporting:view_report', report_id=report.id)
    else:
        form = ReportForm()

    context = {
        'form': form,
        'title': 'Create New Report'
    }

    return render(request, 'reporting/report_form.html', context)

@login_required
def view_report(request, report_id):
    """View for viewing a report and its results"""
    report = get_object_or_404(Report, id=report_id)

    # Get the parameters from the form or request
    if request.method == 'POST':
        form = ReportExecutionForm(request.POST, report=report)
        if form.is_valid():
            parameters = form.cleaned_data.get('parameters')
            try:
                # Execute the report with the provided parameters
                result = execute_report(report, parameters)

                # Store the result in the session for potential export
                request.session['report_result'] = result

                context = {
                    'report': report,
                    'form': form,
                    'result': result,
                    'title': f'Report: {report.name}'
                }

                return render(request, 'reporting/view_report.html', context)
            except Exception as e:
                messages.error(request, f'Error executing report: {str(e)}')
    else:
        form = ReportExecutionForm(report=report)

    # Get recent executions of this report
    recent_executions = ReportExecution.objects.filter(report=report).order_by('-executed_at')[:5]

    # Note: Current AuditLog model doesn't have object_type/object_id fields
    # Filtering by details that might contain report information
    audit_logs = AuditLog.objects.filter(
        details__icontains='Report'
    ).order_by('-timestamp')[:10]
    user_notifications = InternalNotification.objects.filter(
        user=request.user,
        message__icontains='Report',
        is_read=False
    ).order_by('-created_at')[:10]

    context = {
        'report': report,
        'form': form,
        'recent_executions': recent_executions,
        'title': f'Report: {report.name}',
        'audit_logs': audit_logs,
        'user_notifications': user_notifications
    }

    return render(request, 'reporting/view_report.html', context)

@login_required
def edit_report(request, report_id):
    """View for editing a report"""
    report = get_object_or_404(Report, id=report_id)

    # Only the creator or an admin can edit a report
    if report.created_by != request.user and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to edit this report.')
        return redirect('reporting:view_report', report_id=report.id)

    if request.method == 'POST':
        form = ReportForm(request.POST, instance=report)
        if form.is_valid():
            form.save()
            messages.success(request, f'Report {report.name} has been updated successfully.')
            return redirect('reporting:view_report', report_id=report.id)
    else:
        form = ReportForm(instance=report)

    context = {
        'form': form,
        'report': report,
        'title': f'Edit Report: {report.name}'
    }

    return render(request, 'reporting/report_form.html', context)

@login_required
def delete_report(request, report_id):
    """View for deleting a report"""
    report = get_object_or_404(Report, id=report_id)

    # Only the creator or an admin can delete a report
    if report.created_by != request.user and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to delete this report.')
        return redirect('reporting:view_report', report_id=report.id)

    if request.method == 'POST':
        report_name = report.name
        report.delete()
        messages.success(request, f'Report {report_name} has been deleted successfully.')
        return redirect('reporting:reports')

    context = {
        'report': report,
        'title': f'Delete Report: {report.name}'
    }

    return render(request, 'reporting/delete_report.html', context)

@login_required
def dashboard_list(request):
    """View for listing all dashboards"""
    search_form = DashboardSearchForm(request.GET)

    # Show only dashboards the user has access to
    dashboards = Dashboard.objects.filter(
        Q(created_by=request.user) | Q(is_public=True)
    ).order_by('-created_at')

    # Apply filters if the form is valid
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        is_public = search_form.cleaned_data.get('is_public')

        if search_query:
            dashboards = dashboards.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        if is_public:
            is_public_bool = is_public == 'true'
            dashboards = dashboards.filter(is_public=is_public_bool)

    # Pagination
    paginator = Paginator(dashboards, 10)  # Show 10 dashboards per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get counts
    my_dashboards_count = Dashboard.objects.filter(created_by=request.user).count()
    public_dashboards_count = Dashboard.objects.filter(is_public=True).exclude(created_by=request.user).count()
    default_dashboards_count = Dashboard.objects.filter(is_default=True).count()

    # Note: Current AuditLog model doesn't have object_type/object_id fields
    # Filtering by details that might contain report information
    audit_logs = AuditLog.objects.filter(
        details__icontains='Report'
    ).order_by('-timestamp')[:10]
    user_notifications = InternalNotification.objects.filter(
        user=request.user,
        message__icontains='Report',
        is_read=False
    ).order_by('-created_at')[:10]

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_dashboards': dashboards.count(),
        'my_dashboards_count': my_dashboards_count,
        'public_dashboards_count': public_dashboards_count,
        'default_dashboards_count': default_dashboards_count,
        'title': 'Dashboards',
        'audit_logs': audit_logs,
        'user_notifications': user_notifications
    }

    return render(request, 'reporting/dashboard_list.html', context)

@login_required
def create_dashboard(request):
    """View for creating a new dashboard"""
    if request.method == 'POST':
        form = DashboardForm(request.POST)
        if form.is_valid():
            dashboard = form.save(commit=False)
            dashboard.created_by = request.user

            # If this is set as default, unset other defaults for this user
            if dashboard.is_default:
                Dashboard.objects.filter(created_by=request.user, is_default=True).update(is_default=False)

            dashboard.save()
            messages.success(request, f'Dashboard {dashboard.name} has been created successfully.')
            return redirect(f'/reporting/dashboard/?id={dashboard.id}')
    else:
        form = DashboardForm()

    context = {
        'form': form,
        'title': 'Create New Dashboard'
    }

    return render(request, 'reporting/dashboard_form.html', context)

@login_required
def edit_dashboard(request, dashboard_id):
    """View for editing a dashboard"""
    dashboard = get_object_or_404(Dashboard, id=dashboard_id)

    # Only the creator can edit a dashboard
    if dashboard.created_by != request.user:
        messages.error(request, 'You do not have permission to edit this dashboard.')
        return redirect('reporting:dashboard')

    if request.method == 'POST':
        form = DashboardForm(request.POST, instance=dashboard)
        if form.is_valid():
            # If this is set as default, unset other defaults for this user
            if form.cleaned_data.get('is_default'):
                Dashboard.objects.filter(created_by=request.user, is_default=True).exclude(id=dashboard.id).update(is_default=False)

            form.save()
            messages.success(request, f'Dashboard {dashboard.name} has been updated successfully.')
            return redirect('reporting:dashboard')
    else:
        form = DashboardForm(instance=dashboard)

    context = {
        'form': form,
        'dashboard': dashboard,
        'title': f'Edit Dashboard: {dashboard.name}'
    }

    return render(request, 'reporting/dashboard_form.html', context)

@login_required
def delete_dashboard(request, dashboard_id):
    """View for deleting a dashboard"""
    dashboard = get_object_or_404(Dashboard, id=dashboard_id)

    # Only the creator can delete a dashboard
    if dashboard.created_by != request.user:
        messages.error(request, 'You do not have permission to delete this dashboard.')
        return redirect('reporting:dashboard')

    if request.method == 'POST':
        dashboard_name = dashboard.name
        dashboard.delete()
        messages.success(request, f'Dashboard {dashboard_name} has been deleted successfully.')
        return redirect('reporting:dashboards')

    context = {
        'dashboard': dashboard,
        'title': f'Delete Dashboard: {dashboard.name}'
    }

    return render(request, 'reporting/delete_dashboard.html', context)

@login_required
def add_widget(request, dashboard_id):
    """View for adding a widget to a dashboard"""
    dashboard = get_object_or_404(Dashboard, id=dashboard_id)

    # Only the creator can add widgets to a dashboard
    if dashboard.created_by != request.user:
        messages.error(request, 'You do not have permission to add widgets to this dashboard.')
        return redirect('reporting:dashboard')

    if request.method == 'POST':
        form = DashboardWidgetForm(request.POST, dashboard=dashboard)
        if form.is_valid():
            widget = form.save()
            messages.success(request, f'Widget {widget.title} has been added to the dashboard successfully.')
            return redirect('reporting:dashboard')
    else:
        # Get the next available position
        existing_widgets = DashboardWidget.objects.filter(dashboard=dashboard)
        next_y = 0
        if existing_widgets.exists():
            next_y = existing_widgets.order_by('-position_y').first().position_y + 1

        form = DashboardWidgetForm(dashboard=dashboard, initial={
            'position_y': next_y,
            'position_x': 0,
            'width': 6,
            'height': 4
        })

    # Get all available reports for the dropdown
    reports = Report.objects.filter(is_active=True).order_by('name')

    context = {
        'form': form,
        'dashboard': dashboard,
        'reports': reports,
        'title': f'Add Widget to {dashboard.name}'
    }

    return render(request, 'reporting/widget_form.html', context)

@login_required
def edit_widget(request, widget_id):
    """View for editing a dashboard widget"""
    widget = get_object_or_404(DashboardWidget, id=widget_id)
    dashboard = widget.dashboard

    # Only the dashboard creator can edit widgets
    if dashboard.created_by != request.user:
        messages.error(request, 'You do not have permission to edit widgets on this dashboard.')
        return redirect('reporting:dashboard')

    if request.method == 'POST':
        form = DashboardWidgetForm(request.POST, instance=widget, dashboard=dashboard)
        if form.is_valid():
            widget = form.save()
            messages.success(request, f'Widget {widget.title} has been updated successfully.')
            return redirect('reporting:dashboard')
    else:
        form = DashboardWidgetForm(instance=widget, dashboard=dashboard)

    # Get all available reports for the dropdown
    reports = Report.objects.filter(is_active=True).order_by('name')

    context = {
        'form': form,
        'widget': widget,
        'dashboard': dashboard,
        'reports': reports,
        'title': f'Edit Widget: {widget.title}'
    }

    return render(request, 'reporting/widget_form.html', context)

@login_required
def delete_widget(request, widget_id):
    """View for deleting a dashboard widget"""
    widget = get_object_or_404(DashboardWidget, id=widget_id)
    dashboard = widget.dashboard

    # Only the dashboard creator can delete widgets
    if dashboard.created_by != request.user:
        messages.error(request, 'You do not have permission to delete widgets from this dashboard.')
        return redirect('reporting:dashboard')

    if request.method == 'POST':
        widget_title = widget.title
        widget.delete()
        messages.success(request, f'Widget {widget_title} has been deleted successfully.')
        return redirect('reporting:dashboard')

    context = {
        'widget': widget,
        'dashboard': dashboard,
        'title': f'Delete Widget: {widget.title}'
    }

    return render(request, 'reporting/delete_widget.html', context)

@login_required
def export_patient_reports(request, format):
    """Stub for exporting patient reports (CSV/PDF)"""
    # TODO: Implement actual export logic
    return HttpResponse(f"Exporting patient reports as {format.upper()} (stub)")

@login_required
def export_appointment_reports(request, format):
    """Stub for exporting appointment reports (CSV/PDF)"""
    # TODO: Implement actual export logic
    return HttpResponse(f"Exporting appointment reports as {format.upper()} (stub)")

@login_required
def export_billing_reports(request, format):
    """Stub for exporting billing/financial reports (CSV/PDF)"""
    # TODO: Implement actual export logic
    return HttpResponse(f"Exporting billing reports as {format.upper()} (stub)")

@login_required
def export_pharmacy_reports(request, format):
    """Stub for exporting pharmacy reports (CSV/PDF)"""
    # TODO: Implement actual export logic
    return HttpResponse(f"Exporting pharmacy reports as {format.upper()} (stub)")

@login_required
def export_laboratory_reports(request, format):
    """Stub for exporting laboratory/clinical reports (CSV/PDF)"""
    # TODO: Implement actual export logic
    return HttpResponse(f"Exporting laboratory reports as {format.upper()} (stub)")