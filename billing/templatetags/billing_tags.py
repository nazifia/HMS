from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def currency(value):
    """
    Format a value as currency (Nigerian Naira)
    Usage: {{ value|currency }}
    """
    try:
        value = float(value)
        return f"₦{value:,.2f}"
    except (ValueError, TypeError):
        return "₦0.00"

@register.filter
def payment_status_badge(status):
    """
    Return a Bootstrap badge for payment status
    Usage: {{ invoice.status|payment_status_badge }}
    """
    status_classes = {
        'paid': 'bg-success',
        'partially_paid': 'bg-warning',
        'pending': 'bg-info',
        'overdue': 'bg-danger',
        'cancelled': 'bg-secondary',
        'draft': 'bg-light text-dark',
    }

    status_labels = {
        'paid': 'Paid',
        'partially_paid': 'Partially Paid',
        'pending': 'Pending',
        'overdue': 'Overdue',
        'cancelled': 'Cancelled',
        'draft': 'Draft',
    }

    css_class = status_classes.get(status, 'bg-secondary')
    label = status_labels.get(status, status.replace('_', ' ').title())

    return mark_safe(f'<span class="badge {css_class}">{label}</span>')

@register.filter
def percentage(value, decimal_places=1):
    """
    Format a value as percentage
    Usage: {{ value|percentage }}
    """
    try:
        value = float(value)
        return f"{value:.{decimal_places}f}%"
    except (ValueError, TypeError):
        return "0%"

@register.simple_tag
def calculate_subtotal(quantity, unit_price):
    """
    Calculate subtotal from quantity and unit price
    Usage: {% calculate_subtotal item.quantity item.unit_price %}
    """
    try:
        return float(quantity) * float(unit_price)
    except (ValueError, TypeError):
        return 0
