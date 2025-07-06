from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone

register = template.Library()

@register.filter
def prescription_status_badge(status):
    """
    Return a Bootstrap badge for prescription status
    Usage: {{ prescription.status|prescription_status_badge }}
    """
    status_classes = {
        'pending': 'bg-warning',
        'processing': 'bg-info',
        'completed': 'bg-success',
        'cancelled': 'bg-danger',
    }
    
    status_labels = {
        'pending': 'Pending',
        'processing': 'Processing',
        'completed': 'Completed',
        'cancelled': 'Cancelled',
    }
    
    css_class = status_classes.get(status, 'bg-secondary')
    label = status_labels.get(status, status.replace('_', ' ').title())
    
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')

@register.simple_tag
def calculate_total_price(quantity, price):
    """
    Calculate total price from quantity and unit price
    Usage: {% calculate_total_price item.quantity item.medication.price %}
    """
    try:
        return float(quantity) * float(price)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item(list_data, index):
    try:
        return list_data[int(index)] # Ensure index is an integer
    except (IndexError, TypeError, ValueError):
        return None

@register.filter
def timeuntil_days(value):
    """
    Calculates the number of days until a date, or days since if in the past.
    Returns an integer.
    """
    if not value:
        return None
    today = timezone.now().date()
    delta = value - today
    return delta.days

@register.filter
def abs_val(value):
    """
    Returns the absolute value of the input.
    """
    return abs(value)
