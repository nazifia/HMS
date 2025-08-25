# core/utils.py
from django.core.mail import send_mail
from django.urls import reverse, NoReverseMatch
from django.shortcuts import resolve_url
import logging

logger = logging.getLogger(__name__)

def send_notification_email(subject, message, recipient_list, from_email=None):
    # Basic wrapper for Django's send_mail
    send_mail(subject, message, from_email or None, recipient_list)

def send_sms_notification(phone_number, message):
    # Stub for SMS sending logic (integrate with SMS gateway as needed)
    print(f"SMS to {phone_number}: {message}")
    # Implement actual SMS sending here

def safe_reverse(url_name, *args, **kwargs):
    """
    Safely reverse a URL, returning None if the URL cannot be resolved.
    
    Args:
        url_name: Name of the URL pattern
        *args: Positional arguments for the URL
        **kwargs: Keyword arguments for the URL
        
    Returns:
        URL string if successful, None if URL cannot be resolved
    """
    try:
        return reverse(url_name, *args, **kwargs)
    except NoReverseMatch as e:
        logger.warning(f"URL resolution failed for '{url_name}': {e}")
        return None

def safe_reverse_or_default(url_name, default_url='#', *args, **kwargs):
    """
    Safely reverse a URL, returning a default URL if the URL cannot be resolved.
    
    Args:
        url_name: Name of the URL pattern
        default_url: URL to return if resolution fails (default: '#')
        *args: Positional arguments for the URL
        **kwargs: Keyword arguments for the URL
        
    Returns:
        URL string if successful, default_url if URL cannot be resolved
    """
    try:
        return reverse(url_name, *args, **kwargs)
    except NoReverseMatch as e:
        logger.warning(f"URL resolution failed for '{url_name}': {e}")
        return default_url