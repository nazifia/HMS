"""
Context processors for HMS.

Permission/role context moved to accounts.context_processors.page_user_context
(three processors merged into one cache read per page).
"""

from django.conf import settings


def browser_reload(request):
    """Expose whether django_browser_reload is active (dev + installed)."""
    return {"BROWSER_RELOAD": getattr(settings, "BROWSER_RELOAD", False)}
