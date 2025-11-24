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

def format_currency(value, symbol=True):
    """
    Format a monetary value with Naira symbol and thousand separators.

    This function provides consistent currency formatting across Python code,
    matching the template filter behavior.

    Args:
        value: Numeric value (int, float, Decimal, or string)
        symbol: Whether to include the currency symbol (default: True)

    Returns:
        Formatted currency string (e.g., "₦ 1,234.56" or "1,234.56")

    Examples:
        >>> format_currency(1234.56)
        '₦ 1,234.56'
        >>> format_currency(1234.56, symbol=False)
        '1,234.56'
        >>> format_currency(-500)
        '-₦ 500.00'
    """
    try:
        if value is None or value == '':
            return '₦ 0.00' if symbol else '0.00'

        # Convert to float for processing
        numeric_value = float(value)

        # Handle negative values
        is_negative = numeric_value < 0
        numeric_value = abs(numeric_value)

        # Format with 2 decimal places and thousand separators
        formatted_value = f"{numeric_value:,.2f}"

        # Add currency symbol if requested
        if symbol:
            result = f"₦ {formatted_value}"
        else:
            result = formatted_value

        # Add negative sign if needed
        if is_negative:
            result = f"-{result}"

        return result
    except (ValueError, TypeError, AttributeError):
        return '₦ 0.00' if symbol else '0.00'

def parse_currency(value):
    """
    Parse a currency string back to a numeric value.

    Removes currency symbols, commas, and whitespace to extract the numeric value.
    Useful for processing user input or stored formatted values.

    Args:
        value: Currency string or numeric value

    Returns:
        float value or 0.0 if parsing fails

    Examples:
        >>> parse_currency("₦ 1,234.56")
        1234.56
        >>> parse_currency("-₦ 500.00")
        -500.0
        >>> parse_currency(1234.56)
        1234.56
    """
    try:
        if value is None or value == '':
            return 0.0

        # If already numeric, return as float
        if isinstance(value, (int, float)):
            return float(value)

        # Convert to string and clean up
        str_value = str(value)

        # Check for negative sign
        is_negative = str_value.strip().startswith('-')

        # Remove currency symbols, commas, and whitespace
        clean_value = str_value.replace('₦', '').replace(',', '').replace(' ', '').strip()

        # Convert to float
        numeric_value = float(clean_value)

        return numeric_value
    except (ValueError, TypeError, AttributeError):
        logger.warning(f"Failed to parse currency value: {value}")
        return 0.0

def calculate_percentage(part, total, decimal_places=1):
    """
    Calculate percentage of part relative to total.

    Args:
        part: Part value
        total: Total value
        decimal_places: Number of decimal places (default: 1)

    Returns:
        Formatted percentage string (e.g., "25.5%")

    Examples:
        >>> calculate_percentage(25, 100)
        '25.0%'
        >>> calculate_percentage(1234, 5000, 2)
        '24.68%'
    """
    try:
        total_val = float(total or 0)
        if total_val == 0:
            return f"0.{'0' * decimal_places}%"

        part_val = float(part or 0)
        percentage = (part_val / total_val) * 100

        return f"{percentage:.{decimal_places}f}%"
    except (ValueError, TypeError):
        return f"0.{'0' * decimal_places}%"