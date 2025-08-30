"""
Enhanced error handling utilities for HMS
"""

import logging
import traceback
from django.http import JsonResponse, HttpResponseServerError
from django.shortcuts import render
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError, DatabaseError
from .exceptions import *
from .models import AuditLog

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware:
    """Middleware to handle errors gracefully across the application"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            return self.handle_exception(request, e)
    
    def handle_exception(self, request, exception):
        """Handle different types of exceptions"""
        
        # Log the error
        self.log_error(request, exception)
        
        # Handle specific exception types
        if isinstance(exception, PatientNotFoundException):
            return self.handle_patient_not_found(request, exception)
        elif isinstance(exception, InsufficientInventoryException):
            return self.handle_inventory_error(request, exception)
        elif isinstance(exception, PaymentProcessingException):
            return self.handle_payment_error(request, exception)
        elif isinstance(exception, AuthorizationException):
            return self.handle_authorization_error(request, exception)
        elif isinstance(exception, ValidationError):
            return self.handle_validation_error(request, exception)
        elif isinstance(exception, IntegrityError):
            return self.handle_database_error(request, exception)
        else:
            return self.handle_generic_error(request, exception)
    
    def log_error(self, request, exception):
        """Log error details"""
        try:
            user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
            ip_address = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            AuditLog.objects.create(
                user=user,
                action=f"ERROR: {type(exception).__name__}",
                details=f"Path: {request.path}, Error: {str(exception)}",
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as log_error:
            logger.error(f"Failed to log error: {log_error}")
        
        # Also log to standard logger
        logger.error(f"HMS Error: {exception}", exc_info=True)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def handle_patient_not_found(self, request, exception):
        """Handle patient not found errors"""
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'error': 'Patient not found',
                'message': str(exception)
            }, status=404)
        
        messages.error(request, f"Patient not found: {exception}")
        return render(request, 'errors/patient_not_found.html', status=404)
    
    def handle_inventory_error(self, request, exception):
        """Handle inventory errors"""
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'error': 'Insufficient inventory',
                'message': str(exception)
            }, status=400)
        
        messages.error(request, f"Inventory error: {exception}")
        return render(request, 'errors/inventory_error.html', status=400)
    
    def handle_payment_error(self, request, exception):
        """Handle payment processing errors"""
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'error': 'Payment processing failed',
                'message': str(exception)
            }, status=400)
        
        messages.error(request, f"Payment error: {exception}")
        return render(request, 'errors/payment_error.html', status=400)
    
    def handle_authorization_error(self, request, exception):
        """Handle authorization errors"""
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'error': 'Access denied',
                'message': str(exception)
            }, status=403)
        
        messages.error(request, f"Access denied: {exception}")
        return render(request, 'errors/access_denied.html', status=403)
    
    def handle_validation_error(self, request, exception):
        """Handle validation errors"""
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'error': 'Validation failed',
                'message': str(exception)
            }, status=400)
        
        messages.error(request, f"Validation error: {exception}")
        return render(request, 'errors/validation_error.html', status=400)
    
    def handle_database_error(self, request, exception):
        """Handle database errors"""
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'error': 'Database error',
                'message': 'A database error occurred. Please try again.'
            }, status=500)
        
        messages.error(request, "A database error occurred. Please try again.")
        return render(request, 'errors/database_error.html', status=500)
    
    def handle_generic_error(self, request, exception):
        """Handle generic errors"""
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred. Please try again.'
            }, status=500)
        
        messages.error(request, "An unexpected error occurred. Please try again.")
        return render(request, 'errors/generic_error.html', status=500)


def handle_404(request, exception):
    """Custom 404 handler"""
    return render(request, 'errors/404.html', status=404)


def handle_500(request):
    """Custom 500 handler"""
    return render(request, 'errors/500.html', status=500)


def handle_403(request, exception):
    """Custom 403 handler"""
    return render(request, 'errors/403.html', status=403)


def handle_400(request, exception):
    """Custom 400 handler"""
    return render(request, 'errors/400.html', status=400)
