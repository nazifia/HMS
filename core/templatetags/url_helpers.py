from django import template
from django.urls import reverse, NoReverseMatch
from django.shortcuts import resolve_url
from core.utils import safe_reverse, safe_reverse_or_default
import logging

register = template.Library()
logger = logging.getLogger(__name__)

@register.simple_tag(takes_context=True)
def safe_url(context, url_name, *args, **kwargs):
    """
    Generate a URL safely, returning None if the URL cannot be resolved.
    
    Usage in templates:
    {% load url_helpers %}
    {% safe_url 'pharmacy:simple_revenue_statistics' as revenue_url %}
    {% if revenue_url %}
        <a href="{{ revenue_url }}">Revenue Statistics</a>
    {% endif %}
    
    Args:
        context: Template context (automatically provided)
        url_name: Name of the URL pattern
        *args: Positional arguments for the URL
        **kwargs: Keyword arguments for the URL
        
    Returns:
        URL string if successful, None if URL cannot be resolved
    """
    return safe_reverse(url_name, *args, **kwargs)

@register.simple_tag(takes_context=True)
def safe_url_or_default(context, url_name, default_url='#', *args, **kwargs):
    """
    Generate a URL safely, returning a default URL if the URL cannot be resolved.
    
    Usage in templates:
    {% load url_helpers %}
    <a href="{% safe_url_or_default 'pharmacy:simple_revenue_statistics' '#' %}">Revenue Statistics</a>
    
    Args:
        context: Template context (automatically provided)
        url_name: Name of the URL pattern
        default_url: URL to return if resolution fails (default: '#')
        *args: Positional arguments for the URL
        **kwargs: Keyword arguments for the URL
        
    Returns:
        URL string if successful, default_url if URL cannot be resolved
    """
    return safe_reverse_or_default(url_name, default_url, *args, **kwargs)

@register.filter
def resolve_url_or_none(url):
    """
    Resolve a URL string to a full URL path, returning None if it fails.
    
    Usage in templates:
    {% load url_helpers %}
    {{ some_url_string|resolve_url_or_none }}
    
    Args:
        url: URL string to resolve
        
    Returns:
        Resolved URL path if successful, None if URL cannot be resolved
    """
    try:
        return resolve_url(url)
    except Exception as e:
        logger.warning(f"URL resolution failed for '{url}': {e}")
        return None