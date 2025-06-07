from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone
from datetime import datetime, timedelta

register = template.Library()

@register.filter
def appointment_status_badge(status):
    """
    Return a Bootstrap badge for appointment status
    Usage: {{ appointment.status|appointment_status_badge }}
    """
    status_classes = {
        'scheduled': 'bg-primary',
        'confirmed': 'bg-info',
        'completed': 'bg-success',
        'cancelled': 'bg-danger',
        'no_show': 'bg-warning',
    }
    
    status_labels = {
        'scheduled': 'Scheduled',
        'confirmed': 'Confirmed',
        'completed': 'Completed',
        'cancelled': 'Cancelled',
        'no_show': 'No Show',
    }
    
    css_class = status_classes.get(status, 'bg-secondary')
    label = status_labels.get(status, status.replace('_', ' ').title())
    
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')

@register.filter
def priority_badge(priority):
    """
    Return a Bootstrap badge for priority
    Usage: {{ appointment.priority|priority_badge }}
    """
    priority_classes = {
        'normal': 'bg-success',
        'urgent': 'bg-warning',
        'emergency': 'bg-danger',
    }
    
    css_class = priority_classes.get(priority, 'bg-secondary')
    label = priority.replace('_', ' ').title()
    
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')

@register.filter
def format_time(time_obj):
    """
    Format a time object to 12-hour format
    Usage: {{ appointment.appointment_time|format_time }}
    """
    if not time_obj:
        return ''
    
    return time_obj.strftime('%I:%M %p')

@register.filter
def is_past_due(appointment_date):
    """
    Check if an appointment date is in the past
    Usage: {% if appointment.appointment_date|is_past_due %}...{% endif %}
    """
    today = timezone.now().date()
    return appointment_date < today

@register.filter
def is_today(appointment_date):
    """
    Check if an appointment date is today
    Usage: {% if appointment.appointment_date|is_today %}...{% endif %}
    """
    today = timezone.now().date()
    return appointment_date == today

@register.filter
def days_until(appointment_date):
    """
    Calculate days until an appointment
    Usage: {{ appointment.appointment_date|days_until }}
    """
    today = timezone.now().date()
    delta = appointment_date - today
    return delta.days

@register.simple_tag
def get_week_dates(year, week_number):
    """
    Get a list of dates for a specific week
    Usage: {% get_week_dates year week_number as dates %}
    """
    first_day_of_year = datetime(year, 1, 1)
    first_monday = first_day_of_year + timedelta(days=(7 - first_day_of_year.weekday()) % 7)
    week_start = first_monday + timedelta(weeks=week_number-1)
    
    dates = []
    for i in range(7):
        dates.append(week_start.date() + timedelta(days=i))
    
    return dates
