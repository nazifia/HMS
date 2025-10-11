"""
User Activity Monitoring Views
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta, datetime
import json

from .models import UserActivity, ActivityAlert, UserSession
from django.contrib.auth.decorators import login_required, user_passes_test
# from .forms import ActivityFilterForm, AlertFilterForm  # We'll create inline forms

User = get_user_model()

# Inline form classes to avoid import issues
from django import forms

class ActivityFilterForm(forms.Form):
    """Form for filtering user activities"""
    
    ACTION_TYPES = [('', 'All')] + UserActivity.ACTION_TYPES
    ACTIVITY_LEVELS = [('', 'All')] + UserActivity.ACTIVITY_LEVELS
    
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    action_type = forms.ChoiceField(
        choices=ACTION_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    activity_level = forms.ChoiceField(
        choices=ACTIVITY_LEVELS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search activities...'
        })
    )

class AlertFilterForm(forms.Form):
    """Form for filtering activity alerts"""
    
    ALERT_TYPES = [('', 'All')] + ActivityAlert.ALERT_TYPES
    SEVERITY_LEVELS = [('', 'All')] + ActivityAlert.SEVERITY_LEVELS
    
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    alert_type = forms.ChoiceField(
        choices=ALERT_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    severity = forms.ChoiceField(
        choices=SEVERITY_LEVELS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_resolved = forms.ChoiceField(
        choices=[
            ('', 'All Status'),
            ('true', 'Resolved'),
            ('false', 'Open'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def activity_dashboard(request):
    """Main activity monitoring dashboard"""
    
    # Get time range from request
    time_range = request.GET.get('time_range', '24h')
    
    # Calculate time period
    now = timezone.now()
    if time_range == '1h':
        start_time = now - timedelta(hours=1)
    elif time_range == '24h':
        start_time = now - timedelta(hours=24)
    elif time_range == '7d':
        start_time = now - timedelta(days=7)
    elif time_range == '30d':
        start_time = now - timedelta(days=30)
    else:
        start_time = now - timedelta(hours=24)
    
    # Get statistics
    total_activities = UserActivity.objects.filter(timestamp__gte=start_time).count()
    active_users = UserActivity.objects.filter(
        timestamp__gte=start_time, 
        user__isnull=False
    ).values('user').distinct().count()
    
    # Get activity levels breakdown
    activity_levels = UserActivity.objects.filter(
        timestamp__gte=start_time
    ).values('activity_level').annotate(
        count=Count('id')
    ).order_by('activity_level')
    
    # Get top activities
    top_activities = UserActivity.objects.filter(
        timestamp__gte=start_time
    ).values('action_type').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Get recent alerts
    recent_alerts = ActivityAlert.objects.filter(
        created_at__gte=start_time,
        is_resolved=False
    ).order_by('-created_at')[:5]
    
    # Get active sessions
    active_sessions = UserSession.objects.filter(
        is_active=True,
        last_activity__gte=start_time
    ).select_related('user').order_by('-last_activity')[:10]
    
    # Chart data for time series
    chart_data = []
    hours = int((now - start_time).total_seconds() / 3600)
    for i in range(hours + 1):
        hour_start = start_time + timedelta(hours=i)
        hour_end = hour_start + timedelta(hours=1)
        count = UserActivity.objects.filter(
            timestamp__gte=hour_start,
            timestamp__lt=hour_end
        ).count()
        chart_data.append({
            'time': hour_start.strftime('%Y-%m-%d %H:%M'),
            'count': count
        })
    
    context = {
        'time_range': time_range,
        'total_activities': total_activities,
        'active_users': active_users,
        'activity_levels': activity_levels,
        'top_activities': top_activities,
        'recent_alerts': recent_alerts,
        'active_sessions': active_sessions,
        'chart_data': json.dumps(chart_data),
        'page_title': 'Activity Monitor Dashboard',
        'active_nav': 'activity_dashboard',
    }
    
    return render(request, 'accounts/activity_dashboard.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def user_activity_list(request):
    """List all user activities with filters"""
    
    # Get filters
    form = ActivityFilterForm(request.GET)
    activities = UserActivity.objects.select_related('user')
    
    # Filter by user
    user_id = request.GET.get('user')
    if user_id:
        activities = activities.filter(user_id=user_id)
    
    # Filter by action type
    action_type = request.GET.get('action_type')
    if action_type:
        activities = activities.filter(action_type=action_type)
    
    # Filter by activity level
    activity_level = request.GET.get('activity_level')
    if activity_level:
        activities = activities.filter(activity_level=activity_level)
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__gte=date_from)
        except ValueError:
            pass
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__lte=date_to)
        except ValueError:
            pass
    
    # Filter by search term
    search = request.GET.get('search')
    if search:
        activities = activities.filter(
            Q(description__icontains=search) |
            Q(user__username__icontains=search) |
            Q(module__icontains=search) |
            Q(ip_address__icontains=search)
        )
    
    # Order by timestamp (newest first)
    activities = activities.order_by('-timestamp')
    
    # Pagination
    paginator = Paginator(activities, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'page_title': 'User Activities',
        'active_nav': 'user_activities',
        'activities_count': paginator.count,
    }
    
    return render(request, 'accounts/user_activity_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def activity_detail(request, activity_id):
    """ detailed view of a specific activity"""
    
    activity = get_object_or_404(UserActivity, id=activity_id)
    
    # Get related activities (same user, same session)
    related_activities = UserActivity.objects.filter(
        Q(user=activity.user) if activity.user else Q(),
        session_key=activity.session_key
    ).exclude(id=activity.id).order_by('-timestamp')[:10]
    
    context = {
        'activity': activity,
        'related_activities': related_activities,
        'page_title': f'Activity Details - {activity.id}',
        'active_nav': 'user_activities',
    }
    
    return render(request, 'accounts/activity_detail.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def activity_alerts(request):
    """View and manage activity alerts"""
    
    # Get filters
    form = AlertFilterForm(request.GET)
    alerts = ActivityAlert.objects.select_related('user', 'resolved_by')
    
    # Filter by user
    user_id = request.GET.get('user')
    if user_id:
        alerts = alerts.filter(user_id=user_id)
    
    # Filter by alert type
    alert_type = request.GET.get('alert_type')
    if alert_type:
        alerts = alerts.filter(alert_type=alert_type)
    
    # Filter by severity
    severity = request.GET.get('severity')
    if severity:
        alerts = alerts.filter(severity=severity)
    
    # Filter by status
    is_resolved = request.GET.get('is_resolved')
    if is_resolved is not None:
        is_resolved = is_resolved.lower() == 'true'
        alerts = alerts.filter(is_resolved=is_resolved)
    
    # Order by most recent
    alerts = alerts.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(alerts, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'page_title': 'Activity Alerts',
        'active_nav': 'activity_alerts',
        'alerts_count': paginator.count,
    }
    
    return render(request, 'accounts/activity_alerts.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def resolve_alert(request, alert_id):
    """Mark an alert as resolved"""
    
    alert = get_object_or_404(ActivityAlert, id=alert_id)
    
    if request.method == 'POST':
        resolution_notes = request.POST.get('resolution_notes', '')
        
        alert.is_resolved = True
        alert.resolved_by = request.user
        alert.resolved_at = timezone.now()
        alert.resolution_notes = resolution_notes
        alert.save()
        
        messages.success(request, f'Alert "{alert.get_alert_type_display()}" marked as resolved.')
        
        # Log the resolution activity
        UserActivity.objects.create(
            user=request.user,
            action_type='update',
            activity_level='medium',
            description=f'Resolved activity alert: {alert.get_alert_type_display()}',
            module='Activity Monitor',
            object_type='ActivityAlert',
            object_id=str(alert.id),
            object_repr=str(alert),
            additional_data={
                'alert_id': alert.id,
                'alert_type': alert.alert_type,
                'resolved': True,
            }
        )
        
    return redirect('accounts:activity_alerts')


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def user_sessions(request):
    """View active and historical user sessions"""
    
    # Get status filter
    status = request.GET.get('status', 'active')
    
    if status == 'active':
        sessions = UserSession.objects.filter(is_active=True).order_by('-last_activity')
    elif status == 'all':
        sessions = UserSession.objects.all().order_by('-created_at')
    else:  # ended
        sessions = UserSession.objects.filter(is_active=False, ended_at__isnull=False).order_by('-ended_at')
    
    # Filter by user
    user_id = request.GET.get('user')
    if user_id:
        sessions = sessions.filter(user_id=user_id)
    
    # Pagination
    paginator = Paginator(sessions, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get counts for the template
    total_sessions = UserSession.objects.count()
    active_sessions = UserSession.objects.filter(is_active=True).count()
    
    context = {
        'status': status,
        'page_obj': page_obj,
        'page_title': 'User Sessions',
        'active_nav': 'user_sessions',
        'sessions_count': paginator.count,
        'total_sessions': total_sessions,
        'active_sessions': active_sessions,
    }
    
    return render(request, 'accounts/user_sessions.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def session_detail(request, session_key):
    """Detailed view of a user session"""
    
    session = get_object_or_404(UserSession, session_key=session_key)
    
    # Get activities for this session
    session_activities = UserActivity.objects.filter(
        session_key=session_key
    ).select_related('user').order_by('-timestamp')[:50]
    
    context = {
        'session': session,
        'session_activities': session_activities,
        'page_title': f'Session Details - {session_key}',
        'active_nav': 'user_sessions',
    }
    
    return render(request, 'accounts/session_detail.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def activity_statistics(request):
    """Activity statistics and analytics"""
    
    # Get time range
    time_range = request.GET.get('time_range', '7d')
    
    # Calculate time period
    now = timezone.now()
    if time_range == '1d':
        start_time = now - timedelta(days=1)
    elif time_range == '7d':
        start_time = now - timedelta(days=7)
    elif time_range == '30d':
        start_time = now - timedelta(days=30)
    elif time_range == '90d':
        start_time = now - timedelta(days=90)
    else:
        start_time = now - timedelta(days=7)
    
    # User statistics
    active_users_stats = UserActivity.objects.filter(
        timestamp__gte=start_time
    ).values('user__username').annotate(
        activity_count=Count('id')
    ).order_by('-activity_count')[:20]
    
    # Module statistics
    module_stats = UserActivity.objects.filter(
        timestamp__gte=start_time
    ).values('module').annotate(
        activity_count=Count('id')
    ).order_by('-activity_count')[:15]
    
    # Risk level statistics
    risk_stats = UserActivity.objects.filter(
        timestamp__gte=start_time
    ).values('activity_level').annotate(
        count=Count('id')
    ).order_by('activity_level')
    
    # Hourly activity patterns
    hourly_stats = UserActivity.objects.filter(
        timestamp__gte=start_time
    ).extra({
        'hour': "strftime('%%H', timestamp)"
    }).values('hour').annotate(
        count=Count('id')
    ).order_by('hour')
    
    # Error statistics
    error_stats = UserActivity.objects.filter(
        timestamp__gte=start_time,
        action_type='error'
    ).values('description').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Alert statistics
    alert_stats = ActivityAlert.objects.filter(
        created_at__gte=start_time
    ).values('alert_type', 'severity').annotate(
        count=Count('id')
    ).order_by('-count')[:15]
    
    # Calculate total counts for template
    total_risk_activities = sum(item['count'] for item in risk_stats)
    total_alerts = sum(item['count'] for item in alert_stats)
    
    context = {
        'time_range': time_range,
        'active_users_stats': active_users_stats,
        'module_stats': module_stats,
        'risk_stats': risk_stats,
        'hourly_stats': hourly_stats,
        'error_stats': error_stats,
        'alert_stats': alert_stats,
        'total_risk_activities': total_risk_activities,
        'total_alerts': total_alerts,
        'page_title': 'Activity Statistics',
        'active_nav': 'activity_statistics',
    }
    
    return render(request, 'accounts/activity_statistics.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def export_activities(request):
    """Export user activities as CSV"""
    import csv
    from django.http import HttpResponse
    
    # Get filtered activities
    activities = UserActivity.objects.select_related('user').all()
    
    # Apply same filters as activity list
    user_id = request.GET.get('user')
    if user_id:
        activities = activities.filter(user_id=user_id)
    
    action_type = request.GET.get('action_type')
    if action_type:
        activities = activities.filter(action_type=action_type)
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__gte=date_from)
        except ValueError:
            pass
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__lte=date_to)
        except ValueError:
            pass
    
    activities = activities.order_by('-timestamp')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="user_activities.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'User', 'Action Type', 'Activity Level', 'Description', 
        'Module', 'IP Address', 'Timestamp', 'Response Time (ms)', 'Status Code'
    ])
    
    for activity in activities:
        writer.writerow([
            activity.id,
            activity.user.username if activity.user else 'Anonymous',
            activity.get_action_type_display(),
            activity.get_activity_level_display(),
            activity.description,
            activity.module,
            activity.ip_address or '',
            activity.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            activity.response_time_ms or '',
            activity.status_code or '',
        ])
    
    return response


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def live_activity_monitor(request):
    """Live activity monitoring with real-time updates"""
    
    # Get recent activities (last 100)
    recent_activities = UserActivity.objects.select_related('user').order_by('-timestamp')[:100]
    
    # Get active sessions
    active_sessions = UserSession.objects.filter(
        is_active=True
    ).select_related('user').order_by('-last_activity')
    
    # Get unresolved alerts
    open_alerts = ActivityAlert.objects.filter(
        is_resolved=False
    ).select_related('user').order_by('-created_at')[:20]
    
    context = {
        'recent_activities': recent_activities,
        'active_sessions': active_sessions,
        'open_alerts': open_alerts,
        'page_title': 'Live Activity Monitor',
        'active_nav': 'live_monitor',
    }
    
    return render(request, 'accounts/live_activity_monitor.html', context)


# API views for live updates
@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def api_recent_activities(request):
    """API endpoint for recent activities"""
    
    limit = int(request.GET.get('limit', 50))
    
    activities = UserActivity.objects.select_related('user').order_by('-timestamp')[:limit]
    
    data = []
    for activity in activities:
        data.append({
            'id': activity.id,
            'user': activity.user.username if activity.user else 'Anonymous',
            'user_id': activity.user.id if activity.user else None,
            'action_type': activity.get_action_type_display(),
            'activity_level': activity.get_activity_level_display(),
            'description': activity.description,
            'module': activity.module,
            'ip_address': activity.ip_address,
            'timestamp': activity.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'response_time_ms': activity.response_time_ms,
            'status_code': activity.status_code,
        })
    
    return JsonResponse(data, safe=False)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def api_system_status(request):
    """API endpoint for system status"""
    
    now = timezone.now()
    five_minutes_ago = now - timedelta(minutes=5)
    
    stats = {
        'active_users': UserActivity.objects.filter(
            timestamp__gte=five_minutes_ago,
            user__isnull=False
        ).values('user').distinct().count(),
        'total_activities_last_hour': UserActivity.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=1)
        ).count(),
        'active_sessions': UserSession.objects.filter(
            is_active=True,
            last_activity__gte=five_minutes_ago
        ).count(),
        'open_alerts': ActivityAlert.objects.filter(
            is_resolved=False
        ).count(),
        'high_risk_activities': UserActivity.objects.filter(
            timestamp__gte=five_minutes_ago,
            activity_level__in=['high', 'critical']
        ).count(),
        'failed_attempts': UserActivity.objects.filter(
            timestamp__gte=five_minutes_ago,
            status_code__gte=400
        ).count(),
    }
    
    return JsonResponse(stats)
