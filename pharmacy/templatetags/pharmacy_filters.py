from django import template
from ..views import user_has_dispensary_edit_permission

register = template.Library()

@register.filter
def can_edit_dispensary(user, dispensary):
    """Check if user can edit the specified dispensary"""
    return user_has_dispensary_edit_permission(user, dispensary)
