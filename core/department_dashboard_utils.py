"""
Utility functions for department dashboards
Provides reusable functions for building department dashboard contexts
"""

from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Count, Q, Avg, F, ExpressionWrapper, DurationField
from django.db.models.functions import TruncDate
from consultations.models import Referral
import json


def model_has_field(model, field_name):
    """
    Check if a Django model has a specific field

    Args:
        model: Django model class
        field_name: Name of the field to check

    Returns:
        bool: True if field exists, False otherwise
    """
    if field_name is None:
        return False

    try:
        # Get all field names from the model
        field_names = [f.name for f in model._meta.get_fields()]
        return field_name in field_names
    except Exception:
        return False


def get_user_department(user):
    """
    Get the department assigned to a user
    
    Args:
        user: CustomUser instance
        
    Returns:
        Department instance or None
    """
    if hasattr(user, 'profile') and user.profile and user.profile.department:
        return user.profile.department
    return None


def verify_department_access(user, required_department_name):
    """
    Verify that a user has access to a specific department
    
    Args:
        user: CustomUser instance
        required_department_name: String name of the department (case-insensitive)
        
    Returns:
        tuple: (has_access: bool, user_department: Department or None)
    """
    user_department = get_user_department(user)
    
    if not user_department:
        return False, None
    
    # Case-insensitive comparison
    if user_department.name.upper() == required_department_name.upper():
        return True, user_department
    
    # Superusers have access to all departments
    if user.is_superuser:
        return True, user_department
    
    return False, user_department


def get_department_referral_statistics(department):
    """
    Get referral statistics for a department
    
    Args:
        department: Department instance
        
    Returns:
        dict: Statistics about referrals to this department
    """
    referrals = Referral.objects.filter(referred_to_department=department)
    
    stats = {
        'total_referrals': referrals.count(),
        'pending_referrals': referrals.filter(status='pending').count(),
        'accepted_referrals': referrals.filter(status='accepted').count(),
        'completed_referrals': referrals.filter(status='completed').count(),
        'cancelled_referrals': referrals.filter(status='cancelled').count(),
        
        # Authorization statistics
        'requiring_authorization': referrals.filter(
            requires_authorization=True,
            authorization_status__in=['required', 'pending']
        ).count(),
        'authorized_referrals': referrals.filter(
            authorization_status='authorized'
        ).count(),
        'rejected_authorizations': referrals.filter(
            authorization_status='rejected'
        ).count(),
    }
    
    return stats


def get_pending_referrals(department, limit=None):
    """
    Get pending referrals for a department with full related data
    
    Args:
        department: Department instance
        limit: Optional limit on number of referrals to return
        
    Returns:
        QuerySet: Pending referrals with related data
    """
    referrals = Referral.objects.filter(
        referred_to_department=department,
        status='pending'
    ).select_related(
        'patient',
        'referring_doctor',
        'referring_doctor__profile',
        'referring_doctor__profile__department',
        'assigned_doctor',
        'authorization_code'
    ).order_by('-referral_date')
    
    if limit:
        referrals = referrals[:limit]
    
    return referrals


def get_department_time_periods():
    """
    Get common time period boundaries for statistics
    
    Returns:
        dict: Dictionary with today, week_start, month_start, year_start
    """
    today = timezone.now().date()
    
    return {
        'today': today,
        'week_start': today - timedelta(days=today.weekday()),
        'month_start': today.replace(day=1),
        'year_start': today.replace(month=1, day=1),
    }


def build_department_dashboard_context(
    department,
    record_model,
    record_queryset=None,
    additional_stats=None
):
    """
    Build a standardized context dictionary for department dashboards
    
    Args:
        department: Department instance
        record_model: Model class for department records (e.g., DentalRecord)
        record_queryset: Optional custom queryset for records (defaults to all)
        additional_stats: Optional dict of additional statistics to include
        
    Returns:
        dict: Context dictionary for dashboard template
    """
    time_periods = get_department_time_periods()
    
    # Get base queryset
    if record_queryset is None:
        record_queryset = record_model.objects.all()
    
    # Calculate record statistics
    total_records = record_queryset.count()
    records_today = record_queryset.filter(
        created_at__date=time_periods['today']
    ).count()
    records_this_week = record_queryset.filter(
        created_at__date__gte=time_periods['week_start']
    ).count()
    records_this_month = record_queryset.filter(
        created_at__date__gte=time_periods['month_start']
    ).count()
    
    # Get recent records
    recent_records = record_queryset.select_related('patient').order_by('-created_at')[:10]
    
    # Get referral statistics
    referral_stats = get_department_referral_statistics(department)
    pending_referrals = get_pending_referrals(department, limit=20)
    
    # Build context
    context = {
        'department': department,
        'department_name': department.name,
        
        # Time periods
        'today': time_periods['today'],
        'week_start': time_periods['week_start'],
        'month_start': time_periods['month_start'],
        
        # Record statistics
        'total_records': total_records,
        'records_today': records_today,
        'records_this_week': records_this_week,
        'records_this_month': records_this_month,
        'recent_records': recent_records,
        
        # Referral statistics
        'referral_stats': referral_stats,
        'pending_referrals': pending_referrals,
        'pending_referrals_count': referral_stats['pending_referrals'],
        'pending_authorizations': referral_stats['requiring_authorization'],
        
        # Page metadata
        'page_title': f'{department.name} Department Dashboard',
        'active_nav': 'dashboard',
    }
    
    # Add any additional statistics
    if additional_stats:
        context.update(additional_stats)
    
    return context


def get_authorized_referrals(department, limit=None):
    """
    Get referrals that are authorized and ready to be acted upon
    
    Args:
        department: Department instance
        limit: Optional limit on number of referrals
        
    Returns:
        QuerySet: Authorized pending referrals
    """
    referrals = Referral.objects.filter(
        referred_to_department=department,
        status='pending',
        authorization_status__in=['authorized', 'not_required']
    ).select_related(
        'patient',
        'referring_doctor',
        'authorization_code'
    ).order_by('-referral_date')
    
    if limit:
        referrals = referrals[:limit]
    
    return referrals


def get_unauthorized_referrals(department, limit=None):
    """
    Get referrals that require authorization but haven't been authorized yet
    
    Args:
        department: Department instance
        limit: Optional limit on number of referrals
        
    Returns:
        QuerySet: Unauthorized pending referrals
    """
    referrals = Referral.objects.filter(
        referred_to_department=department,
        status='pending',
        requires_authorization=True,
        authorization_status__in=['required', 'pending']
    ).select_related(
        'patient',
        'referring_doctor',
        'authorization_code'
    ).order_by('-referral_date')
    
    if limit:
        referrals = referrals[:limit]
    
    return referrals


def categorize_referrals(department):
    """
    Categorize referrals by their authorization and status

    Args:
        department: Department instance

    Returns:
        dict: Categorized referrals including pending and accepted
    """
    # Get pending referrals
    pending_referrals = Referral.objects.filter(
        referred_to_department=department,
        status='pending'
    ).select_related(
        'patient',
        'patient__nhia_info',
        'referring_doctor',
        'referring_doctor__profile',
        'referring_doctor__profile__department',
        'authorization_code',
        'assigned_doctor'
    ).order_by('-referral_date')

    # Get accepted referrals (patients under care)
    accepted_referrals = Referral.objects.filter(
        referred_to_department=department,
        status='accepted'
    ).select_related(
        'patient',
        'patient__nhia_info',
        'referring_doctor',
        'referring_doctor__profile',
        'referring_doctor__profile__department',
        'authorization_code',
        'assigned_doctor'
    ).order_by('-referral_date')

    categorized = {
        'ready_to_accept': [],  # Authorized or not requiring authorization (pending)
        'awaiting_authorization': [],  # Requires authorization but not yet authorized (pending)
        'rejected_authorization': [],  # Authorization was rejected (pending)
        'under_care': [],  # Accepted referrals - patients currently under department care
    }

    # Categorize pending referrals
    for referral in pending_referrals:
        if referral.authorization_status == 'rejected':
            categorized['rejected_authorization'].append(referral)
        elif referral.authorization_status in ['authorized', 'not_required']:
            categorized['ready_to_accept'].append(referral)
        elif referral.requires_authorization and referral.authorization_status in ['required', 'pending']:
            categorized['awaiting_authorization'].append(referral)
        else:
            # Default to ready to accept for any other case
            categorized['ready_to_accept'].append(referral)

    # Add accepted referrals to under_care
    categorized['under_care'] = list(accepted_referrals)

    return categorized


# ============================================================================
# DASHBOARD ENHANCEMENT FUNCTIONS
# ============================================================================

def get_daily_trend_data(record_model, days=7, date_field='created_at'):
    """
    Get daily trend data for charts

    Args:
        record_model: Django model class
        days: Number of days to include (default: 7)
        date_field: Name of the date field to use (default: 'created_at')

    Returns:
        dict: {
            'labels': ['Mon', 'Tue', ...],
            'data': [10, 15, 12, ...],
            'dates': ['2025-01-01', '2025-01-02', ...]
        }
    """
    today = timezone.now().date()
    start_date = today - timedelta(days=days-1)

    # Get daily counts
    daily_data = (
        record_model.objects
        .filter(**{f'{date_field}__date__gte': start_date})
        .annotate(date=TruncDate(date_field))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    # Create a complete date range
    date_range = [start_date + timedelta(days=x) for x in range(days)]
    data_dict = {item['date']: item['count'] for item in daily_data}

    # Fill in missing dates with 0
    labels = []
    data = []
    dates = []

    for date in date_range:
        labels.append(date.strftime('%a'))  # Mon, Tue, Wed, etc.
        data.append(data_dict.get(date, 0))
        dates.append(date.strftime('%Y-%m-%d'))

    return {
        'labels': json.dumps(labels),
        'data': json.dumps(data),
        'dates': dates,
    }


def get_status_distribution(record_model, status_field='status'):
    """
    Get status distribution for pie/doughnut charts

    Args:
        record_model: Django model class
        status_field: Name of the status field (default: 'status', can be None)

    Returns:
        dict: {
            'labels': ['Pending', 'Completed', ...],
            'data': [10, 25, ...],
            'colors': ['#ffc107', '#28a745', ...]
        }
        Returns empty data if status_field is None
    """
    # Return empty data if no status field
    if status_field is None:
        return {
            'labels': json.dumps([]),
            'data': json.dumps([]),
            'colors': json.dumps([]),
        }

    status_data = (
        record_model.objects
        .values(status_field)
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Color mapping for common statuses
    color_map = {
        'pending': '#ffc107',  # Yellow
        'in_progress': '#17a2b8',  # Blue
        'processing': '#17a2b8',  # Blue
        'completed': '#28a745',  # Green
        'cancelled': '#dc3545',  # Red
        'rejected': '#dc3545',  # Red
        'planned': '#6c757d',  # Gray
        'scheduled': '#007bff',  # Primary blue
        'awaiting_payment': '#fd7e14',  # Orange
    }

    labels = []
    data = []
    colors = []

    for item in status_data:
        status = item[status_field]
        if status:
            labels.append(status.replace('_', ' ').title())
            data.append(item['count'])
            colors.append(color_map.get(status, '#6c757d'))

    return {
        'labels': json.dumps(labels),
        'data': json.dumps(data),
        'colors': json.dumps(colors),
    }


def calculate_trend_percentage(current_value, previous_value):
    """
    Calculate percentage change between two values

    Args:
        current_value: Current period value
        previous_value: Previous period value

    Returns:
        dict: {
            'percentage': 15.5,
            'direction': 'up',  # 'up', 'down', or 'neutral'
            'icon': 'fa-arrow-up',
            'color': 'success'  # 'success', 'danger', or 'secondary'
        }
    """
    if previous_value == 0:
        if current_value > 0:
            return {
                'percentage': 100.0,
                'direction': 'up',
                'icon': 'fa-arrow-up',
                'color': 'success'
            }
        return {
            'percentage': 0.0,
            'direction': 'neutral',
            'icon': 'fa-minus',
            'color': 'secondary'
        }

    percentage = ((current_value - previous_value) / previous_value) * 100

    if percentage > 0:
        direction = 'up'
        icon = 'fa-arrow-up'
        color = 'success'
    elif percentage < 0:
        direction = 'down'
        icon = 'fa-arrow-down'
        color = 'danger'
    else:
        direction = 'neutral'
        icon = 'fa-minus'
        color = 'secondary'

    return {
        'percentage': abs(round(percentage, 1)),
        'direction': direction,
        'icon': icon,
        'color': color
    }


def get_urgent_items(record_model, priority_field='priority', urgent_values=['urgent', 'emergency'], limit=10):
    """
    Get urgent/priority items requiring immediate attention

    Args:
        record_model: Django model class
        priority_field: Name of the priority field (can be None)
        urgent_values: List of values considered urgent
        limit: Maximum number of items to return

    Returns:
        QuerySet: Urgent records (empty queryset if priority_field is None)
    """
    # Return empty queryset if no priority field
    if priority_field is None:
        return record_model.objects.none()

    filter_kwargs = {f'{priority_field}__in': urgent_values}

    try:
        return (
            record_model.objects
            .filter(**filter_kwargs)
            .select_related('patient', 'doctor')
            .order_by('-created_at')[:limit]
        )
    except Exception:
        # If select_related fails (missing relations), try without it
        return (
            record_model.objects
            .filter(**filter_kwargs)
            .order_by('-created_at')[:limit]
        )


def calculate_completion_rate(record_model, status_field='status', completed_status='completed', days=30, date_field='created_at'):
    """
    Calculate completion rate for records

    Args:
        record_model: Django model class
        status_field: Name of the status field (can be None)
        completed_status: Value indicating completed status
        days: Number of days to consider (default: 30)
        date_field: Name of the date field to filter by (default: 'created_at')

    Returns:
        dict: {
            'total': 100,
            'completed': 85,
            'rate': 85.0,
            'pending': 15
        }
        Returns zeros if status_field is None
    """
    # Return zeros if no status field
    if status_field is None:
        return {
            'total': 0,
            'completed': 0,
            'rate': 0.0,
            'pending': 0
        }

    start_date = timezone.now() - timedelta(days=days)

    filter_kwargs = {f'{date_field}__gte': start_date}
    total = record_model.objects.filter(**filter_kwargs).count()

    completed_filter = {**filter_kwargs, status_field: completed_status}
    completed = record_model.objects.filter(**completed_filter).count()

    rate = (completed / total * 100) if total > 0 else 0

    return {
        'total': total,
        'completed': completed,
        'rate': round(rate, 1),
        'pending': total - completed
    }


def get_active_staff(department, hours=24):
    """
    Get staff members who have been active in the last N hours

    Args:
        department: Department instance
        hours: Number of hours to look back (default: 24)

    Returns:
        QuerySet: Active staff members
    """
    from accounts.models import CustomUserProfile
    from core.models import AuditLog

    cutoff_time = timezone.now() - timedelta(hours=hours)

    # Get users who have audit log entries in the time period
    active_user_ids = (
        AuditLog.objects
        .filter(timestamp__gte=cutoff_time)
        .values_list('user_id', flat=True)
        .distinct()
    )

    # Get profiles for these users in the department
    active_staff = (
        CustomUserProfile.objects
        .filter(
            user_id__in=active_user_ids,
            department=department
        )
        .select_related('user')
        .order_by('user__first_name')
    )

    return active_staff


def get_performance_metrics(record_model, date_field='created_at', days=30):
    """
    Calculate various performance metrics

    Args:
        record_model: Django model class
        date_field: Name of the date field
        days: Number of days to analyze

    Returns:
        dict: Performance metrics
    """
    start_date = timezone.now() - timedelta(days=days)
    records = record_model.objects.filter(**{f'{date_field}__gte': start_date})

    total_records = records.count()
    avg_per_day = total_records / days if days > 0 else 0

    # Get today's count
    today = timezone.now().date()
    today_count = record_model.objects.filter(**{f'{date_field}__date': today}).count()

    # Get yesterday's count for comparison
    yesterday = today - timedelta(days=1)
    yesterday_count = record_model.objects.filter(**{f'{date_field}__date': yesterday}).count()

    # Calculate trend
    trend = calculate_trend_percentage(today_count, yesterday_count)

    return {
        'total_records': total_records,
        'avg_per_day': round(avg_per_day, 1),
        'today_count': today_count,
        'yesterday_count': yesterday_count,
        'trend': trend,
    }


def build_enhanced_dashboard_context(department, record_model, record_queryset=None,
                                     additional_stats=None, priority_field=None,
                                     status_field='status', completed_status='completed',
                                     date_field='created_at'):
    """
    Build an enhanced context dictionary for department dashboards with charts and trends

    This is a flexible function that gracefully handles missing fields by accepting None values.

    Args:
        department: Department instance
        record_model: Django model class for the department records
        record_queryset: Optional pre-filtered queryset
        additional_stats: Optional dict of additional statistics
        priority_field: Name of priority field (can be None if model doesn't have priority)
        status_field: Name of status field (can be None if model doesn't have status)
        completed_status: Value indicating completed status
        date_field: Name of the date field to use for filtering (default: 'created_at')

    Returns:
        dict: Enhanced context with all dashboard data
    """
    # Validate that the fields actually exist in the model
    # If they don't exist, set them to None so downstream functions handle gracefully
    if status_field and not model_has_field(record_model, status_field):
        status_field = None

    if priority_field and not model_has_field(record_model, priority_field):
        priority_field = None

    # Get base context
    base_context = build_department_dashboard_context(
        department=department,
        record_model=record_model,
        record_queryset=record_queryset,
        additional_stats=additional_stats
    )

    # Add chart data (with correct date field)
    base_context['daily_trend'] = get_daily_trend_data(record_model, days=7, date_field=date_field)

    # Add status distribution (only if status field exists)
    base_context['status_distribution'] = get_status_distribution(record_model, status_field)

    # Add performance metrics (with correct date field)
    base_context['performance'] = get_performance_metrics(record_model, date_field=date_field)

    # Add completion rate (only if status field exists)
    base_context['completion_rate'] = calculate_completion_rate(
        record_model, status_field, completed_status, date_field=date_field
    )

    # Add urgent items (only if priority field exists)
    base_context['urgent_items'] = get_urgent_items(record_model, priority_field)

    # Add active staff
    base_context['active_staff'] = get_active_staff(department)

    return base_context

