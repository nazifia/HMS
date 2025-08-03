
"""
Enhanced Security Middleware for HMS
"""
import logging
from django.http import HttpResponseForbidden

logger = logging.getLogger('security')

class SecurityEnhancementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log security events
        if request.method == 'POST':
            logger.info(f"POST request to {request.path} from {request.META.get('REMOTE_ADDR')}")
        
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
