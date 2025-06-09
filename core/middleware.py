from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class LoginRequiredMiddleware:
    """
    Middleware to ensure all pages (except public ones) require authentication.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # URL patterns that are accessible without authentication
        self.public_urls = [
            reverse('accounts:login'),
            reverse('accounts:logout'),
            reverse('accounts:password_reset'),
            reverse('accounts:password_reset_done'),
            # Use string patterns for URLs with parameters
            'accounts/reset/',  # Password reset confirm URLs
            reverse('accounts:password_reset_complete'),
            reverse('accounts:phone_auth_guide'),
            '/static/',
            '/media/',
            '/admin/login/',
        ]

    def __call__(self, request):
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            # Allow access to the home page
            if request.path == '/' or request.path == '':
                return self.get_response(request)

            # Check if the current URL is in the public URLs list
            for url in self.public_urls:
                if request.path.startswith(url):
                    return self.get_response(request)

            # Redirect to login page with a message
            messages.warning(request, "Please log in to access this page.")
            return redirect('accounts:login')

        # Continue with the request if user is authenticated
        return self.get_response(request)


class RoleBasedAccessMiddleware:
    """
    Middleware to handle role-based access control across the application.
    This middleware checks if a user has the required role to access certain URL patterns.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # URL patterns that require specific roles
        # Format: (url_pattern, [allowed_roles])
        # Note: Django admin URLs are excluded from role-based access control
        self.role_required_urls = [
            # Application admin URLs (not Django admin)
            ('accounts/staff/', ['admin']),
            ('accounts/department/', ['admin']),
            ('hr/', ['admin']),
            ('reporting/', ['admin']),

            # Doctor-specific URLs
            ('appointments/doctor/', ['doctor', 'admin']),
            ('doctors/schedule/', ['doctor', 'admin']),
            ('doctors/leave-request/', ['doctor', 'admin']),

            # Nurse-specific URLs
            ('inpatient/vitals/', ['nurse', 'doctor', 'admin']),
            ('inpatient/care-plan/', ['nurse', 'doctor', 'admin']),

            # Receptionist and Health Record Officer URLs
            ('patients/register/', ['receptionist', 'health_record_officer', 'admin']),
            ('appointments/create/', ['receptionist', 'health_record_officer', 'doctor', 'admin']),

            # Pharmacy-specific URLs
            ('pharmacy/inventory/', ['pharmacist', 'admin']),
            ('pharmacy/prescriptions/', ['pharmacist', 'doctor', 'admin']),
            ('pharmacy/dispense/', ['pharmacist', 'admin']),

            # Laboratory-specific URLs
            ('laboratory/', ['lab_technician', 'doctor', 'admin']),
            ('laboratory/results/create/', ['lab_technician', 'admin']),

            # Billing-specific URLs
            ('billing/', ['accountant', 'admin']),
            ('billing/create/', ['accountant', 'receptionist', 'admin']),
            ('billing/payments/', ['accountant', 'receptionist', 'admin']),

            # Inpatient-specific URLs
            ('inpatient/', ['nurse', 'doctor', 'admin']),
            ('inpatient/admission/', ['doctor', 'receptionist', 'admin']),
            ('inpatient/discharge/', ['doctor', 'admin']),
        ]

    def __call__(self, request):
        # Skip middleware if user is not authenticated
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Skip middleware for login/logout URLs
        if request.path.startswith(reverse('accounts:login')) or request.path.startswith(reverse('accounts:logout')):
            return self.get_response(request)

        # Skip middleware for Django admin URLs - admin has its own permission system
        if request.path.startswith('/admin/'):
            return self.get_response(request)

        # Check if the current URL requires a specific role
        for url_pattern, allowed_roles in self.role_required_urls:
            if url_pattern in request.path:
                # Get user's role
                user_role = request.user.roles.first()

                # Allow superusers to access everything (application level)
                if request.user.is_superuser:
                    break

                # Check if user has the required role
                if user_role not in allowed_roles:
                    messages.error(request, "You don't have permission to access this page.")
                    return redirect('dashboard:dashboard')

        # Continue with the request
        return self.get_response(request)
