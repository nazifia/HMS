from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def test_request_status_badge(status):
    """
    Return a Bootstrap badge for test request status
    Usage: {{ test_request.status|test_request_status_badge }}
    """
    status_classes = {
        'pending': 'bg-warning',
        'collected': 'bg-info',
        'processing': 'bg-primary',
        'completed': 'bg-success',
        'cancelled': 'bg-danger',
    }
    
    status_labels = {
        'pending': 'Pending',
        'collected': 'Sample Collected',
        'processing': 'Processing',
        'completed': 'Completed',
        'cancelled': 'Cancelled',
    }
    
    css_class = status_classes.get(status, 'bg-secondary')
    label = status_labels.get(status, status.replace('_', ' ').title())
    
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')

@register.filter
def priority_badge(priority):
    """
    Return a Bootstrap badge for priority
    Usage: {{ test_request.priority|priority_badge }}
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
def result_status_badge(is_normal):
    """
    Return a Bootstrap badge for test result status
    Usage: {{ parameter.is_normal|result_status_badge }}
    """
    if is_normal:
        return mark_safe('<span class="badge bg-success">Normal</span>')
    else:
        return mark_safe('<span class="badge bg-danger">Abnormal</span>')

@register.filter
def format_result_value(value, parameter):
    """
    Format a test result value with appropriate styling
    Usage: {{ result.value|format_result_value:result.parameter }}
    """
    if not value:
        return ''
    
    normal_range = parameter.normal_range if parameter else ''
    unit = parameter.unit if parameter else ''
    
    if parameter and parameter.is_normal:
        return mark_safe(f'<span class="text-success">{value} {unit}</span>')
    else:
        return mark_safe(f'<span class="text-danger">{value} {unit}</span>')

@register.simple_tag
def is_value_in_range(value, normal_range):
    """
    Check if a value is within a normal range
    Usage: {% is_value_in_range result.value parameter.normal_range as is_normal %}
    """
    if not value or not normal_range:
        return True
    
    try:
        value = float(value)
        
        # Handle different range formats
        if '-' in normal_range:
            min_val, max_val = normal_range.split('-')
            min_val = float(min_val.strip())
            max_val = float(max_val.strip())
            return min_val <= value <= max_val
        elif '<' in normal_range:
            max_val = float(normal_range.replace('<', '').strip())
            return value < max_val
        elif '>' in normal_range:
            min_val = float(normal_range.replace('>', '').strip())
            return value > min_val
        else:
            return value == float(normal_range.strip())
    except (ValueError, TypeError):
        return True
