from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.forms import BoundField

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Add a CSS class to a Django form field
    Usage: {{ form.field|add_class:"form-control" }}
    """
    if hasattr(field, 'as_widget') and isinstance(field, BoundField):
        return field.as_widget(attrs={"class": css_class})
    elif hasattr(field, 'as_widget'):
        try:
            return field.as_widget(attrs={"class": css_class})
        except (AttributeError, TypeError):
            return field
    else:
        return field

@register.filter(name='add_placeholder')
def add_placeholder(field, placeholder_text):
    """
    Add a placeholder to a Django form field
    Usage: {{ form.field|add_placeholder:"Enter text here" }}
    """
    if hasattr(field, 'as_widget') and isinstance(field, BoundField):
        current_attrs = field.field.widget.attrs.copy()
        current_attrs['placeholder'] = placeholder_text
        return field.as_widget(attrs=current_attrs)
    elif hasattr(field, 'as_widget'):
        try:
            current_attrs = getattr(field.field.widget, 'attrs', {}).copy()
            current_attrs['placeholder'] = placeholder_text
            return field.as_widget(attrs=current_attrs)
        except (AttributeError, TypeError):
            return field
    else:
        return field

@register.filter(name='add_rows')
def add_rows(field, rows):
    """
    Add rows attribute to a Django form field (for textareas)
    Usage: {{ form.field|add_rows:"3" }}
    """
    if hasattr(field, 'as_widget') and isinstance(field, BoundField):
        current_attrs = field.field.widget.attrs.copy()
        current_attrs['rows'] = rows
        return field.as_widget(attrs=current_attrs)
    elif hasattr(field, 'as_widget'):
        try:
            current_attrs = getattr(field.field.widget, 'attrs', {}).copy()
            current_attrs['rows'] = rows
            return field.as_widget(attrs=current_attrs)
        except (AttributeError, TypeError):
            return field
    else:
        return field

@register.filter
def add(value, arg):
    """
    Add two numbers together in template
    Usage: {{ value|add:arg }}
    """
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """
    Divides the value by the argument.
    Usage: {{ value|div:arg }}
    """
    try:
        return float(value) / float(arg) if float(arg) != 0 else 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def mul(value, arg):
    """
    Multiplies the value by the argument.
    Usage: {{ value|mul:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def sub(value, arg):
    """
    Subtracts the argument from the value.
    Usage: {{ value|sub:arg }}
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

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

@register.filter
def commas(value):
    """
    Format a number with commas as thousands separators.
    Usage: {{ value|commas }}
    """
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value
