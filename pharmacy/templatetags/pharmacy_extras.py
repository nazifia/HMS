from django import template
from ..views import user_can_edit_dispensary

register = template.Library()

@register.filter
def user_can_edit(user, dispensary):
    """Template filter to check if user can edit dispensary"""
    return user_can_edit_dispensary(user, dispensary)
