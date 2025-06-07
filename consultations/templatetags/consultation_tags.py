from django import template

register = template.Library()

@register.filter
def priority_color(priority):
    """
    Map priority value to a Bootstrap color name (or similar).
    Example: 'high' -> 'danger', 'medium' -> 'warning', 'low' -> 'success'
    """
    mapping = {
        'high': 'danger',
        'medium': 'warning',
        'low': 'success',
    }
    return mapping.get(priority, 'secondary')
