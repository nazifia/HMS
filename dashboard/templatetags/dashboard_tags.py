from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def trend_indicator(value, previous_value):
    """
    Return a trend indicator icon based on value comparison
    Usage: {{ current_value|trend_indicator:previous_value }}
    """
    if not value or not previous_value:
        return ''
    
    try:
        value = float(value)
        previous_value = float(previous_value)
        
        if value > previous_value:
            return mark_safe('<i class="fas fa-arrow-up text-success"></i>')
        elif value < previous_value:
            return mark_safe('<i class="fas fa-arrow-down text-danger"></i>')
        else:
            return mark_safe('<i class="fas fa-equals text-secondary"></i>')
    except (ValueError, TypeError):
        return ''

@register.filter
def percentage_change(value, previous_value):
    """
    Calculate percentage change between two values
    Usage: {{ current_value|percentage_change:previous_value }}
    """
    if not value or not previous_value:
        return 0
    
    try:
        value = float(value)
        previous_value = float(previous_value)
        
        if previous_value == 0:
            return 100 if value > 0 else 0
        
        change = ((value - previous_value) / previous_value) * 100
        return round(change, 1)
    except (ValueError, TypeError):
        return 0

@register.filter
def format_large_number(value):
    """
    Format large numbers with K, M, B suffixes
    Usage: {{ large_number|format_large_number }}
    """
    if not value:
        return '0'
    
    try:
        value = float(value)
        
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f}B"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        elif value >= 1_000:
            return f"{value / 1_000:.1f}K"
        else:
            return str(int(value))
    except (ValueError, TypeError):
        return str(value)

@register.simple_tag
def get_date_range(period):
    """
    Get start and end dates for a period
    Usage: {% get_date_range 'week' as dates %}
    """
    today = timezone.now().date()
    
    if period == 'today':
        return {
            'start': today,
            'end': today,
            'label': 'Today'
        }
    elif period == 'yesterday':
        yesterday = today - timedelta(days=1)
        return {
            'start': yesterday,
            'end': yesterday,
            'label': 'Yesterday'
        }
    elif period == 'week':
        start = today - timedelta(days=today.weekday())
        return {
            'start': start,
            'end': today,
            'label': f"{start.strftime('%b %d')} - {today.strftime('%b %d')}"
        }
    elif period == 'month':
        start = today.replace(day=1)
        return {
            'start': start,
            'end': today,
            'label': today.strftime('%B %Y')
        }
    elif period == 'year':
        start = today.replace(month=1, day=1)
        return {
            'start': start,
            'end': today,
            'label': today.strftime('%Y')
        }
    else:
        return {
            'start': today,
            'end': today,
            'label': 'Custom'
        }
