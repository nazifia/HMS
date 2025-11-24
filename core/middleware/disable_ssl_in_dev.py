"""
Middleware to disable SSL redirects in development mode.
This prevents "You're accessing the development server over HTTPS" errors.
"""
from django.conf import settings


class DisableSSLInDevMiddleware:
    """
    Middleware that disables SSL redirects when DEBUG is True.
    This allows the development server to work properly even if
    SECURE_SSL_REDIRECT is accidentally set to True.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # In development, don't enforce HTTPS
        if settings.DEBUG:
            # Remove HTTPS enforcement headers
            request.META.pop('HTTP_X_FORWARDED_PROTO', None)
            request.META.pop('HTTP_X_FORWARDED_SSL', None)

        response = self.get_response(request)

        # In development, remove HSTS headers
        if settings.DEBUG and 'Strict-Transport-Security' in response:
            del response['Strict-Transport-Security']

        return response
