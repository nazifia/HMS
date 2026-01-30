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


@register.simple_tag
def can_accept_referral(referral, user):
    """
    Check if a user can accept a referral.
    Usage: {% can_accept_referral referral request.user as can_accept %}
    """
    if referral and hasattr(referral, 'can_be_accepted_by'):
        return referral.can_be_accepted_by(user)
    return False
