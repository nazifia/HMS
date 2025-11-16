"""
Middleware to protect all pharmacy URLs with role-based access control.
This ensures only admins and pharmacists can access pharmacy views.
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve


class PharmacyAccessMiddleware:
    """
    Middleware to restrict access to pharmacy URLs to authorized users only.
    Authorized roles: admin, pharmacist, superuser
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for a pharmacy URL
        if request.path.startswith('/pharmacy/'):
            # Allow if user is not authenticated (login_required will handle it)
            if not request.user.is_authenticated:
                return self.get_response(request)

            # Allow superusers
            if request.user.is_superuser:
                return self.get_response(request)

            # Check if user has admin or pharmacist role
            user_roles = list(request.user.roles.values_list('name', flat=True))

            # Also check profile role for backward compatibility
            if hasattr(request.user, 'profile') and request.user.profile:
                profile_role = request.user.profile.role
                if profile_role and profile_role not in user_roles:
                    user_roles.append(profile_role)

            # Allow if user has admin or pharmacist role
            if 'admin' in user_roles or 'pharmacist' in user_roles:
                return self.get_response(request)

            # Deny access - user doesn't have required role
            messages.error(
                request,
                "You don't have permission to access the Pharmacy module. "
                "Only pharmacists and administrators can access this area."
            )
            return redirect('dashboard:dashboard')

        # Not a pharmacy URL, proceed normally
        return self.get_response(request)
