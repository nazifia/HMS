from django import template

register = template.Library()

@register.filter
def get_all_permission_names(permissions_queryset):
    """
    Extract permission codenames from a queryset or set of Permission objects.
    
    Usage: {{ role.get_all_permissions|get_all_permission_names }}
    """
    if not permissions_queryset:
        return []
    
    try:
        return [perm.codename for perm in permissions_queryset]
    except AttributeError:
        # If the objects don't have codename attribute, try to get string representation
        return [str(perm) for perm in permissions_queryset]

@register.filter
def role_icon(role_name):
    """
    Get appropriate FontAwesome icon for a role name.
    
    Usage: {{ role.name|role_icon }}
    """
    role_icons = {
        'admin': 'fa-user-shield',
        'doctor': 'fa-user-md',
        'nurse': 'fa-user-nurse',
        'receptionist': 'fa-user-tie',
        'pharmacist': 'fa-pills',
        'lab_technician': 'fa-flask',
        'radiology_staff': 'fa-x-ray',
        'accountant': 'fa-calculator',
        'health_record_officer': 'fa-file-medical',
    }
    
    return role_icons.get(role_name.lower(), 'fa-user')

@register.filter
def action_type_badge_class(action_type):
    """Get Bootstrap badge class for action type"""
    badge_classes = {
        'failed_login': 'danger',
        'permission_denied': 'warning',
        'login': 'success',
        'logout': 'secondary',
        'create': 'primary',
        'update': 'info',
        'delete': 'danger',
        'view': 'light',
        'export': 'info',
        'import': 'info',
        'print': 'secondary',
        'search': 'light',
        'filter': 'light',
        'sort': 'light',
        'download': 'info',
        'upload': 'info',
        'authorize': 'success',
        'approve': 'success',
        'reject': 'danger',
        'cancel': 'warning',
        'reschedule': 'warning',
        'transfer': 'info',
        'dispense': 'success',
        'prescribe': 'info',
        'admit': 'primary',
        'discharge': 'warning',
        'settle': 'success',
        'refund': 'warning',
    }
    return badge_classes.get(action_type, 'secondary')

@register.filter
def activity_level_badge_class(level):
    """Get Bootstrap badge class for activity level"""
    level_classes = {
        'debug': 'secondary',
        'info': 'info',
        'warning': 'warning',
        'error': 'danger',
        'critical': 'danger',
        'low': 'light',
        'medium': 'warning',
        'high': 'danger',
    }
    return level_classes.get(level, 'secondary')

@register.filter
def timeago(timestamp):
    """Simple time ago filter (placeholder implementation)"""
    from django.utils import timezone
    import datetime
    
    if not timestamp:
        return "N/A"
    
    now = timezone.now()
    diff = now - timestamp
    
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}h ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}m ago"
    else:
        return "Just now"

@register.tag
def set(parser, token):
    """
    Set a variable in the template context.
    
    Usage: {% set var_name = value %}
    """
    bits = token.split_contents()
    if len(bits) != 4 or bits[2] != '=':
        raise template.TemplateSyntaxError(
            "'set' tag must be of the form: {% set var_name = value %}"
        )
    var_name = bits[1]
    value = bits[3]
    return SetNode(var_name, value)

class SetNode(template.Node):
    def __init__(self, var_name, value):
        self.var_name = var_name
        self.value = value
    
    def render(self, context):
        try:
            value = template.Variable(self.value).resolve(context)
        except template.VariableDoesNotExist:
            value = ''
        context[self.var_name] = value
        return ''

@register.filter
def replace(value, args):
    """
    Replace all occurrences of a substring in a string with another substring.
    
    Usage: {{ variable|replace:"old:new" }}
    """
    if not value:
        return value
    
    try:
        old, new = args.split(':', 1)
        return value.replace(old, new)
    except (ValueError, AttributeError):
        return value

@register.filter
def split(value, separator):
    """
    Split a string into a list by separator.
    
    Usage: {{ string|split:"," }}
    """
    if not value:
        return []
    return value.split(separator)

@register.filter
def sum(queryset, field):
    """
    Sum values of a specific field in a list of dictionaries.

    Usage: {{ trends|sum:'total_revenue' }}
    """
    try:
        # Use built-in sum with explicit reference to avoid recursion
        total = 0
        for item in queryset:
            if item:
                total += float(item.get(field, 0))
        return total
    except (ValueError, TypeError):
        return 0

@register.filter
def filter(value, condition):
    """
    Filter list based on a simple condition.
    Currently supports field>value format.

    Usage: {{ trends|filter:'total_revenue>0' }}
    """
    try:
        # Handle both 'field>value' and 'field > value' formats
        if '>' in condition:
            parts = condition.split('>')
            field = parts[0].strip()
            val = parts[1].strip()
            return [item for item in value
                    if item and
                    float(item.get(field, 0)) > float(val)]
        else:
            return value
    except (ValueError, AttributeError, IndexError):
        return value

@register.filter
def length(value):
    """
    Get length of a list.
    
    Usage: {{ list|length }}
    """
    if hasattr(value, '__len__'):
        return len(value)
    return 0

@register.filter
def lookup(dictionary, key):
    """
    Look up a key in a dictionary.
    
    Usage: {{ dict|lookup:"key" }}
    """
    try:
        return dictionary.get(key, '')
    except (AttributeError, TypeError):
        return ''

@register.filter
def first(value):
    """
    Get first item from a list.
    
    Usage: {{ list|first }}
    """
    try:
        return value[0] if value else None
    except (IndexError, TypeError):
        return None

@register.filter
def last(value):
    """
    Get last item from a list.
    
    Usage: {{ list|last }}
    """
    try:
        return value[-1] if value else None
    except (IndexError, TypeError):
        return None

@register.simple_tag
def calculate_average(data_list, field):
    """
    Calculate average of a field in a list of dictionaries.
    
    Usage: {% calculate_average trends 'total_revenue' %}
    """
    try:
        if not data_list:
            return "0.00"
        total = sum(float(item.get(field, 0)) for item in data_list if item)
        avg = total / len([item for item in data_list if item])
        return f"{avg:,.2f}"
    except (ValueError, TypeError):
        return "0.00"

@register.simple_tag
def calculate_growth_rate(first_value, last_value):
    """
    Calculate growth rate between two values.
    
    Usage: {% calculate_growth_rate first last %}
    """
    try:
        first_val = float(first_value or 0)
        last_val = float(last_value or 0)
        if first_val == 0:
            return 0.0
        growth = ((last_val - first_val) / first_val) * 100
        return round(growth, 2)
    except (ValueError, TypeError):
        return 0.0

@register.simple_tag
def get_first_field_value(data_list, field):
    """
    Get field value from first item in list.
    
    Usage: {% get_first_field_value trends 'total_revenue' %}
    """
    try:
        if data_list and len(data_list) > 0:
            return data_list[0].get(field, 0)
        return 0
    except (IndexError, AttributeError):
        return 0

@register.simple_tag
def get_last_field_value(data_list, field):
    """
    Get field value from last item in list.
    
    Usage: {% get_last_field_value trends 'total_revenue' %}
    """
    try:
        if data_list and len(data_list) > 0:
            return data_list[-1].get(field, 0)
        return 0
    except (IndexError, AttributeError):
        return 0

@register.filter
def intcomma(value):
    """
    Convert an integer to a string containing commas every three digits.
    
    Usage: {{ value|intcomma }}
    """
    try:
        if not value:
            return value
        # Convert to string and add commas
        s = str(int(float(value)))
        if len(s) <= 3:
            return s
        else:
            groups = []
            while s:
                groups.append(s[-3:])
                s = s[:-3]
            return ','.join(reversed(groups))
    except (ValueError, TypeError):
        return value

@register.simple_tag(takes_context=True)
def get_growth_rate_class(context, data_list, field):
    """
    Get growth rate and CSS class for first vs last values.

    Usage: {% get_growth_rate_class trends 'total_revenue' as growth_info %}
    """
    try:
        if not data_list or len(data_list) < 2:
            context['growth_rate'] = 0.0
            context['growth_class'] = 'growth-positive'
            return ''

        first_val = float(data_list[0].get(field, 0))
        last_val = float(data_list[-1].get(field, 0))

        if first_val == 0:
            growth_rate = 0.0
        else:
            growth_rate = ((last_val - first_val) / first_val) * 100

        growth_class = 'growth-positive' if growth_rate >= 0 else 'growth-negative'

        context['growth_rate'] = round(growth_rate, 2)
        context['growth_class'] = growth_class
        return ''
    except (ValueError, TypeError, IndexError, AttributeError):
        context['growth_rate'] = 0.0
        context['growth_class'] = 'growth-positive'
        return ''

@register.filter
def currency(value):
    """
    Format a monetary value with Naira symbol and thousand separators.

    Usage: {{ amount|currency }}
    Output: ₦ 1,234.56

    Args:
        value: Numeric value (int, float, Decimal, or string)

    Returns:
        Formatted currency string
    """
    try:
        if value is None or value == '':
            return '₦ 0.00'

        # Convert to float for processing
        numeric_value = float(value)

        # Handle negative values
        is_negative = numeric_value < 0
        numeric_value = abs(numeric_value)

        # Format with 2 decimal places
        formatted_value = f"{numeric_value:,.2f}"

        # Add currency symbol
        result = f"₦ {formatted_value}"

        # Add negative sign if needed
        if is_negative:
            result = f"-{result}"

        return result
    except (ValueError, TypeError, AttributeError):
        return '₦ 0.00'

@register.filter
def mul(value, arg):
    """Multiply value by argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def currency_no_symbol(value):
    """
    Format a monetary value with thousand separators but without currency symbol.
    Useful for input fields or when you want to add the symbol separately.

    Usage: {{ amount|currency_no_symbol }}
    Output: 1,234.56

    Args:
        value: Numeric value (int, float, Decimal, or string)

    Returns:
        Formatted number string
    """
    try:
        if value is None or value == '':
            return '0.00'

        # Convert to float for processing
        numeric_value = float(value)

        # Format with 2 decimal places and thousand separators
        return f"{numeric_value:,.2f}"
    except (ValueError, TypeError, AttributeError):
        return '0.00'

@register.filter
def subtract(value, arg):
    """
    Subtract arg from value. Useful for calculating differences.

    Usage: {{ total|subtract:paid }}

    Args:
        value: First numeric value
        arg: Value to subtract

    Returns:
        Result of subtraction
    """
    try:
        return float(value or 0) - float(arg or 0)
    except (ValueError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    """
    Multiply value by arg.

    Usage: {{ price|multiply:quantity }}

    Args:
        value: First numeric value
        arg: Multiplier

    Returns:
        Result of multiplication
    """
    try:
        return float(value or 0) * float(arg or 0)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """
    Divide value by arg.

    Usage: {{ total|div:count }}

    Args:
        value: Dividend
        arg: Divisor

    Returns:
        Result of division, or 0 if division by zero
    """
    try:
        divisor = float(arg or 0)
        if divisor == 0:
            return 0
        return float(value or 0) / divisor
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """
    Calculate percentage of value relative to total.

    Usage: {{ part|percentage:whole }}

    Args:
        value: Part value
        total: Total value

    Returns:
        Percentage with 1 decimal place
    """
    try:
        total_val = float(total or 0)
        if total_val == 0:
            return '0.0%'
        part_val = float(value or 0)
        pct = (part_val / total_val) * 100
        return f"{pct:.1f}%"
    except (ValueError, TypeError):
        return '0.0%'
