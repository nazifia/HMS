"""
Admin views for enhanced permissions and activity logging
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.views.generic import ListView, DetailView
from django.utils.decorators import method_decorator
from django.db.models import Q, Count, Avg, Max
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse_lazy

from core.permissions import RolePermissionChecker, permission_required, get_client_ip
from core.decorators import admin_required, role_required
from core.activity_log import ActivityLog
from accounts.models import CustomUser, CustomUserProfile, Role

User = get_user_model()

def is_admin(user):
    """Check if user is admin"""
    return user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'admin')

@login_required
@user_passes_test(is_admin, login_url=reverse_lazy('dashboard:dashboard'))
def admin_dashboard(request):
    """Enhanced admin dashboard with activity overview"""
    
    # Get basic stats
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    recent_logins = User.objects.filter(last_login__gte=timezone.now() - timedelta(days=1)).count()
    
    # Get activity stats
    today = timezone.now().date()
    today_activities = ActivityLog.objects.filter(timestamp__date=today)
    
    # Activity by category
    activity_by_category = today_activities.values('category').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Recent activities
    recent_activities = ActivityLog.objects.select_related('user').order_by('-timestamp')[:10]
    
    # Failed login attempts (last 24 hours)
    failed_logins = ActivityLog.objects.filter(
        action_type='failed_login',
        timestamp__gte=timezone.now() - timedelta(hours=24)
    ).count()
    
    # Permission denied events (last 24 hours)
    permission_denied = ActivityLog.objects.filter(
        action_type='permission_denied',
        timestamp__gte=timezone.now() - timedelta(hours=24)
    ).count()
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'recent_logins': recent_logins,
        'total_activities_today': today_activities.count(),
        'activity_by_category': activity_by_category,
        'recent_activities': recent_activities,
        'failed_logins': failed_logins,
        'permission_denied': permission_denied,
        'page_title': 'Admin Dashboard',
    }
    
    return render(request, 'admin/admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin, login_url=reverse_lazy('dashboard:dashboard'))
def activity_log_view(request):
    """View and search activity logs"""
    
    # Get filter parameters
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    action_type = request.GET.get('action_type', '')
    level = request.GET.get('level', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    logs = ActivityLog.objects.select_related('user').order_by('-timestamp')
    
    # Apply filters
    if search:
        logs = logs.filter(
            Q(description__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    
    if category:
        logs = logs.filter(category=category)
    
    if action_type:
        logs = logs.filter(action_type=action_type)
    
    if level:
        logs = logs.filter(level=level)
    
    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__lte=date_to)
        except ValueError:
            pass
    
    # Pagination
    from django.core.paginator import Paginator
    page = request.GET.get('page', 1)
    paginator = Paginator(logs, 50)  # 50 logs per page
    logs_page = paginator.get_page(page)
    
    context = {
        'logs': logs_page,
        'categories': ActivityLog.CATEGORY_CHOICES,
        'action_types': ActivityLog.ACTION_TYPES,
        'levels': ActivityLog.LEVEL_CHOICES,
        'current_filters': {
            'search': search,
            'category': category,
            'action_type': action_type,
            'level': level,
            'date_from': date_from,
            'date_to': date_to,
        },
        'page_title': 'Activity Log',
    }
    
    return render(request, 'admin/activity_log.html', context)

@login_required
@user_passes_test(is_admin, login_url=reverse_lazy('dashboard:dashboard'))
def permission_management(request):
    """Manage user permissions and roles"""
    
    # Get all roles with user counts
    roles = Role.objects.annotate(user_count=Count('users'))
    
    # Role statistics
    total_permissions = Permission.objects.count()
    total_users_in_roles = sum(role.user_count for role in roles)
    
    context = {
        'roles': roles,
        'total_permissions': total_permissions,
        'total_users_in_roles': total_users_in_roles,
        'page_title': 'Permission Management',
    }
    
    return render(request, 'admin/permission_management.html', context)

@login_required
@user_passes_test(is_admin, login_url=reverse_lazy('dashboard:dashboard'))
def user_permissions_detail(request, user_id):
    """View and edit user permissions"""
    
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    
    # Get permission checker
    checker = RolePermissionChecker(user)
    
    # Get all permissions by category
    from core.permissions import APP_PERMISSIONS
    user_permissions = checker.get_permissions_by_category('all') if hasattr(checker, 'get_permissions_by_category') else set()
    
    context = {
        'target_user': user,
        'user_roles': user.roles.all(),
        'user_permissions': user_permissions,
        'app_permissions': APP_PERMISSIONS,
        'page_title': f'User Permissions - {user.get_full_name()}',
    }
    
    return render(request, 'admin/user_permissions_detail.html', context)

@login_required
@user_passes_test(is_admin, login_url=reverse_lazy('dashboard:dashboard'))
def security_overview(request):
    """Security monitoring and alerts"""
    
    # Security stats (last 24 hours)
    last_24h = timezone.now() - timedelta(hours=24)
    
    failed_logins_count = ActivityLog.objects.filter(
        action_type='failed_login',
        timestamp__gte=last_24h
    ).count()
    
    permission_denied_count = ActivityLog.objects.filter(
        action_type='permission_denied',
        timestamp__gte=last_24h
    ).count()
    
    suspicious_activities = ActivityLog.objects.filter(
        timestamp__gte=last_24h,
        level__in=['error', 'critical']
    ).count()
    
    # Recent security events
    security_events = ActivityLog.objects.filter(
        Q(action_type='failed_login') |
        Q(action_type='permission_denied') |
        Q(category='security'),
        timestamp__gte=last_24h
    ).select_related('user').order_by('-timestamp')[:20]
    
    # User session information
    active_sessions = ActivityLog.objects.filter(
        action_type='login',
        success=True,
        timestamp__gte=timezone.now() - timedelta(hours=2)
    ).values('user__username', 'ip_address').annotate(
        last_activity=Max('timestamp')
    ).order_by('-last_activity')
    
    context = {
        'failed_logins_count': failed_logins_count,
        'permission_denied_count': permission_denied_count,
        'suspicious_activities': suspicious_activities,
        'security_events': security_events,
        'active_sessions': active_sessions,
        'page_title': 'Security Overview',
    }
    
    return render(request, 'admin/security_overview.html', context)

@login_required
@user_passes_test(is_admin, login_url=reverse_lazy('dashboard:dashboard'))
def user_activity_timeline(request, user_id):
    """View detailed activity timeline for a specific user"""
    
    user = get_object_or_404(User, id=user_id)
    
    # Get user activities
    activities = ActivityLog.objects.filter(user=user).select_related(
        'content_type'
    ).order_by('-timestamp')
    
    # Filter by date range if provided
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__lte=date_to)
        except ValueError:
            pass
    
    # Pagination
    from django.core.paginator import Paginator
    page = request.GET.get('page', 1)
    paginator = Paginator(activities, 100)
    activities_page = paginator.get_page(page)
    
    # Statistics
    total_activities = activities.count()
    today_activities = activities.filter(timestamp__date=timezone.now().date()).count()
    
    # Activity breakdown by category
    activity_by_category = activities.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'target_user': user,
        'activities': activities_page,
        'total_activities': total_activities,
        'today_activities': today_activities,
        'activity_by_category': activity_by_category,
        'page_title': f'Activity Timeline - {user.get_full_name()}',
    }
    
    return render(request, 'admin/user_activity_timeline.html', context)

@login_required
@user_passes_test(is_admin, login_url=reverse_lazy('dashboard:dashboard'))
def audit_report(request):
    """Generate audit reports"""
    
    # Get time periods for reports
    today = timezone.now().date()
    this_week = today - timedelta(days=7)
    this_month = today - timedelta(days=30)
    
    # Generate statistics for different periods
    report_data = {
        'today': {
            'logins': ActivityLog.objects.filter(action_type='login', timestamp__date=today).count(),
            'failed_logins': ActivityLog.objects.filter(action_type='failed_login', timestamp__date=today).count(),
            'user_actions': ActivityLog.objects.filter(~Q(action_type__in=['login', 'logout']), timestamp__date=today).count(),
            'permission_denied': ActivityLog.objects.filter(action_type='permission_denied', timestamp__date=today).count(),
        },
        'this_week': {
            'logins': ActivityLog.objects.filter(action_type='login', timestamp__date__gte=this_week).count(),
            'failed_logins': ActivityLog.objects.filter(action_type='failed_login', timestamp__date__gte=this_week).count(),
            'user_actions': ActivityLog.objects.filter(~Q(action_type__in=['login', 'logout']), timestamp__date__gte=this_week).count(),
            'permission_denied': ActivityLog.objects.filter(action_type='permission_denied', timestamp__date__gte=this_week).count(),
        },
        'this_month': {
            'logins': ActivityLog.objects.filter(action_type='login', timestamp__date__gte=this_month).count(),
            'failed_logins': ActivityLog.objects.filter(action_type='failed_login', timestamp__date__gte=this_month).count(),
            'user_actions': ActivityLog.objects.filter(~Q(action_type__in=['login', 'logout']), timestamp__date__gte=this_month).count(),
            'permission_denied': ActivityLog.objects.filter(action_type='permission_denied', timestamp__date__gte=this_month).count(),
        },
    }
    
    # Top users by activity
    top_users = ActivityLog.objects.values('user__username', 'user__first_name', 'user__last_name').filter(
        timestamp__gte=this_week,
        user__isnull=False
    ).annotate(activity_count=Count('id')).order_by('-activity_count')[:10]
    
    # Most active categories
    top_categories = ActivityLog.objects.filter(
        timestamp__gte=this_week
    ).values('category').annotate(count=Count('id')).order_by('-count')[:10]
    
    # Security events
    security_events = ActivityLog.objects.filter(
        timestamp__gte=this_week,
        category='security'
    ).count()
    
    context = {
        'report_data': report_data,
        'top_users': top_users,
        'top_categories': top_categories,
        'security_events': security_events,
        'page_title': 'Audit Report',
    }
    
    return render(request, 'admin/audit_report.html', context)

# API Endpoints for AJAX
@login_required
@user_passes_test(is_admin)
def api_activity_stats(request):
    """API endpoint for activity statistics"""
    
    time_period = request.GET.get('period', 'today')
    
    if time_period == 'today':
        start_date = timezone.now().date()
    elif time_period == 'week':
        start_date = timezone.now().date() - timedelta(days=7)
    elif time_period == 'month':
        start_date = timezone.now().date() - timedelta(days=30)
    else:
        start_date = timezone.now().date() - timedelta(days=1)
    
    activities = ActivityLog.objects.filter(timestamp__date__gte=start_date)
    
    stats = {
        'total': activities.count(),
        'logins': activities.filter(action_type='login').count(),
        'failed_logins': activities.filter(action_type='failed_login').count(),
        'permission_denied': activities.filter(action_type='permission_denied').count(),
        'errors': activities.filter(level='error').count(),
        'warnings': activities.filter(level='warning').count(),
    }
    
    return JsonResponse(stats)

@login_required
@user_passes_test(is_admin)
def api_user_permissions(request):
    """API endpoint for user permissions"""
    
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'User ID required'}, status=400)
    
    try:
        user = User.objects.get(id=user_id)
        checker = RolePermissionChecker(user)
        
        permissions = checker.get_user_permissions()
        categories = {}
        
        for permission in permissions:
            # Categorize permissions
            category = permission.split('_')[0] + '_management'
            if category not in categories:
                categories[category] = []
            categories[category].append(permission)
        
        return JsonResponse({
            'user_id': user_id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'roles': list(user.roles.values_list('name', flat=True)),
            'permissions_by_category': categories,
            'total_permissions': len(permissions),
        })
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
