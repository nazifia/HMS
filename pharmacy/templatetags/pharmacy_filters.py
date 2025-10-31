from django import template

register = template.Library()

@register.filter
def can_edit_dispensary(user, dispensary):
    """Check if user can edit the specified dispensary"""
    # Import inside function to avoid circular imports
    from ..views import user_has_dispensary_edit_permission
    return user_has_dispensary_edit_permission(user, dispensary)

@register.filter
def multiply(value, arg):
    """Multiply two numbers in template"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
