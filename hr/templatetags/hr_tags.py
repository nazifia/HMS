from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone

register = template.Library()

@register.filter
def leave_status_badge(status):
    """
    Return a Bootstrap badge for leave status
    Usage: {{ leave.status|leave_status_badge }}
    """
    status_classes = {
        'pending': 'bg-warning',
        'approved': 'bg-success',
        'rejected': 'bg-danger',
        'cancelled': 'bg-secondary',
    }
    
    status_labels = {
        'pending': 'Pending',
        'approved': 'Approved',
        'rejected': 'Rejected',
        'cancelled': 'Cancelled',
    }
    
    css_class = status_classes.get(status, 'bg-secondary')
    label = status_labels.get(status, status.replace('_', ' ').title())
    
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')

@register.filter
def attendance_status_badge(status):
    """
    Return a Bootstrap badge for attendance status
    Usage: {{ attendance.status|attendance_status_badge }}
    """
    status_classes = {
        'present': 'bg-success',
        'absent': 'bg-danger',
        'half_day': 'bg-warning',
        'late': 'bg-info',
        'leave': 'bg-secondary',
    }
    
    status_labels = {
        'present': 'Present',
        'absent': 'Absent',
        'half_day': 'Half Day',
        'late': 'Late',
        'leave': 'Leave',
    }
    
    css_class = status_classes.get(status, 'bg-secondary')
    label = status_labels.get(status, status.replace('_', ' ').title())
    
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')

@register.filter
def payroll_status_badge(status):
    """
    Return a Bootstrap badge for payroll status
    Usage: {{ payroll.status|payroll_status_badge }}
    """
    status_classes = {
        'pending': 'bg-warning',
        'paid': 'bg-success',
        'cancelled': 'bg-danger',
    }
    
    status_labels = {
        'pending': 'Pending',
        'paid': 'Paid',
        'cancelled': 'Cancelled',
    }
    
    css_class = status_classes.get(status, 'bg-secondary')
    label = status_labels.get(status, status.replace('_', ' ').title())
    
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')

@register.filter
def format_shift_time(shift):
    """
    Format shift times
    Usage: {{ shift|format_shift_time }}
    """
    if not shift or not shift.start_time or not shift.end_time:
        return ''
    
    start = shift.start_time.strftime('%I:%M %p')
    end = shift.end_time.strftime('%I:%M %p')
    return f"{start} - {end}"

@register.filter
def leave_duration(leave):
    """
    Calculate leave duration in days
    Usage: {{ leave|leave_duration }}
    """
    if not leave or not leave.start_date or not leave.end_date:
        return 0
    
    delta = leave.end_date - leave.start_date
    return delta.days + 1  # Include both start and end dates

@register.simple_tag
def get_attendance_count(user, status, month=None, year=None):
    """
    Get attendance count for a user by status
    Usage: {% get_attendance_count user 'present' month year %}
    """
    from hr.models import Attendance
    
    query = Attendance.objects.filter(staff=user, status=status)
    
    if month and year:
        query = query.filter(date__month=month, date__year=year)
    elif year:
        query = query.filter(date__year=year)
    
    return query.count()
