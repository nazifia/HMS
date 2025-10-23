from django import template

register = template.Library()

@register.filter
def user_can_edit(user, dispensary):
    """Template filter to check if user can edit dispensary"""
    # Import here to avoid circular imports
    from ..views import user_can_edit_dispensary
    return user_can_edit_dispensary(user, dispensary)
