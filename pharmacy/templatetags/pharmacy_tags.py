from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone

register = template.Library()

@register.filter
def stock_status_badge(medication):
    """
    Return a Bootstrap badge for medication stock status
    Usage: {{ medication|stock_status_badge }}
    """
    if medication.stock_quantity == 0:
        return mark_safe('<span class="badge bg-danger">Out of Stock</span>')
    elif medication.stock_quantity <= medication.reorder_level:
        return mark_safe('<span class="badge bg-warning">Low Stock</span>')
    else:
        return mark_safe('<span class="badge bg-success">In Stock</span>')

@register.filter
def expiry_status_badge(expiry_date):
    """
    Return a Bootstrap badge for medication expiry status
    Usage: {{ medication.expiry_date|expiry_status_badge }}
    """
    if not expiry_date:
        return mark_safe('<span class="badge bg-secondary">No Expiry</span>')
    
    today = timezone.now().date()
    
    if expiry_date < today:
        return mark_safe('<span class="badge bg-danger">Expired</span>')
    elif (expiry_date - today).days <= 30:
        return mark_safe('<span class="badge bg-warning">Expiring Soon</span>')
    else:
        return mark_safe('<span class="badge bg-success">Valid</span>')

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

@register.filter
def days_until_expiry(expiry_date):
    """
    Calculate days until medication expires
    Usage: {{ medication.expiry_date|days_until_expiry }}
    """
    if not expiry_date:
        return None
    
    today = timezone.now().date()
    delta = expiry_date - today
    return delta.days

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
