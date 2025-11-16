from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def radiology_status_badge(status):
    """
    Return a Bootstrap badge for radiology order status
    Usage: {{ order.status|radiology_status_badge }}
    """
    status_classes = {
        'pending': 'bg-warning',
        'awaiting_payment': 'bg-info',
        'payment_confirmed': 'bg-primary',
        'scheduled': 'bg-info',
        'completed': 'bg-success',
        'cancelled': 'bg-danger',
    }
    
    status_labels = {
        'pending': 'Pending',
        'awaiting_payment': 'Awaiting Payment',
        'payment_confirmed': 'Payment Confirmed',
        'scheduled': 'Scheduled',
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
    Usage: {{ order.priority|priority_badge }}
    """
    priority_classes = {
        'normal': 'bg-secondary',
        'urgent': 'bg-warning',
        'emergency': 'bg-danger',
    }
    
    priority_labels = {
        'normal': 'Normal',
        'urgent': 'Urgent',
        'emergency': 'Emergency',
    }
    
    css_class = priority_classes.get(priority, 'bg-secondary')
    label = priority_labels.get(priority, priority.replace('_', ' ').title())
    
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')

@register.filter
def result_status_badge(is_abnormal):
    """
    Return a Bootstrap badge for radiology result status
    Usage: {{ result.is_abnormal|result_status_badge }}
    """
    if is_abnormal:
        return mark_safe('<span class="badge bg-danger">Abnormal</span>')
    else:
        return mark_safe('<span class="badge bg-success">Normal</span>')
