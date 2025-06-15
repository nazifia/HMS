from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden

def role_required(allowed_roles):
    """
    Decorator to restrict view access based on user role.
    Superusers have unrestricted access to all views.

    Args:
        allowed_roles: List of role names that are allowed to access the view

    Usage:
        @role_required(['admin', 'doctor'])
        def some_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                messages.error(request, "You must be logged in to access this page.")
                return redirect('accounts:login')

            # Allow superusers to access everything without role restrictions
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Get user's roles (many-to-many relationship)
            user_roles = list(request.user.roles.values_list('name', flat=True))

            # Check if user has any of the required roles
            if not any(role in allowed_roles for role in user_roles):
                messages.error(request, "You don't have permission to access this page.")
                return redirect('dashboard:dashboard')

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def admin_required(view_func):
    """
    Decorator to restrict view access to admin users only.

    Usage:
        @admin_required
        def admin_only_view(request):
            ...
    """
    return role_required(['admin'])(view_func)

def doctor_required(view_func):
    """
    Decorator to restrict view access to doctors only.

    Usage:
        @doctor_required
        def doctor_only_view(request):
            ...
    """
    return role_required(['doctor', 'admin'])(view_func)

def pharmacist_required(view_func):
    """
    Decorator to restrict view access to pharmacists only.

    Usage:
        @pharmacist_required
        def pharmacist_only_view(request):
            ...
    """
    return role_required(['pharmacist', 'admin'])(view_func)

def lab_technician_required(view_func):
    """
    Decorator to restrict view access to lab technicians only.

    Usage:
        @lab_technician_required
        def lab_technician_only_view(request):
            ...
    """
    return role_required(['lab_technician', 'admin'])(view_func)

def nurse_required(view_func):
    """
    Decorator to restrict view access to nurses only.

    Usage:
        @nurse_required
        def nurse_only_view(request):
            ...
    """
    return role_required(['nurse', 'admin'])(view_func)

def accountant_required(view_func):
    """
    Decorator to restrict view access to accountants only.

    Usage:
        @accountant_required
        def accountant_only_view(request):
            ...
    """
    return role_required(['accountant', 'admin'])(view_func)

def receptionist_required(view_func):
    """
    Decorator to restrict view access to receptionists only.

    Usage:
        @receptionist_required
        def receptionist_only_view(request):
            ...
    """
    return role_required(['receptionist', 'admin'])(view_func)

def health_record_officer_required(view_func):
    """
    Decorator to restrict view access to health record officers only.

    Usage:
        @health_record_officer_required
        def health_record_officer_only_view(request):
            ...
    """
    return role_required(['health_record_officer', 'admin'])(view_func)

def api_role_required(allowed_roles):
    """
    Decorator for API views to restrict access based on user role.
    Returns 403 Forbidden instead of redirecting.

    Args:
        allowed_roles: List of role names that are allowed to access the API

    Usage:
        @api_role_required(['admin', 'doctor'])
        def some_api_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Allow superusers to access everything
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check if user is authenticated
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Authentication required")

            # Get user's roles (many-to-many relationship)
            user_roles = list(request.user.roles.values_list('name', flat=True))

            # Check if user has any of the required roles
            if not any(role in allowed_roles for role in user_roles):
                return HttpResponseForbidden("Permission denied")

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
