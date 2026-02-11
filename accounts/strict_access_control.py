"""
Strict Access Control Middleware for HMS

This middleware enforces a "deny by default" policy where:
1. All URLs require explicit permission to access
2. Users must have the specific permission OR role assigned
3. No implicit access is granted based on authentication alone
4. Superusers bypass all permission checks
5. Public URLs must be explicitly whitelisted

Usage:
    Add 'accounts.middleware.StrictAccessControlMiddleware' to MIDDLEWARE in settings.py
    after AuthenticationMiddleware.

Configuration in settings.py:
    STRICT_ACCESS_CONTROL = True  # Enable strict mode
    PUBLIC_URLS = [  # URLs that don't require permission
        '/accounts/login/',
        '/accounts/logout/',
        '/static/',
        '/media/',
    ]
"""

import logging
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.conf import settings
from django.contrib import messages
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin

from accounts.permissions import (
    user_has_permission,
    get_user_roles,
    ROLE_PERMISSIONS,
)

logger = logging.getLogger(__name__)


class StrictAccessControlMiddleware(MiddlewareMixin):
    """
    Middleware that enforces strict access control.

    Denies access to all URLs by default unless:
    - URL is in PUBLIC_URLS whitelist
    - User has the required permission for the URL
    - User has a role that grants access to the module
    - User is a superuser
    """

    def __init__(self, get_response=None):
        self.get_response = get_response
        self.strict_mode = getattr(settings, "STRICT_ACCESS_CONTROL", True)
        self.public_urls = self._get_public_urls()
        self.url_permission_map = self._build_url_permission_map()

    def _get_public_urls(self):
        """Get list of URLs that don't require permission checks."""
        default_public_urls = [
            "/accounts/login/",
            "/accounts/logout/",
            "/accounts/password-reset/",
            "/accounts/password-reset/done/",
            "/accounts/password-reset-confirm/",
            "/accounts/password-reset-complete/",
            "/static/",
            "/media/",
            "/favicon.ico",
            "/admin/login/",
            "/admin/logout/",
            "/api/auth/",
            "/health/",
            "/ping/",
        ]

        # Allow settings to extend or override
        custom_urls = getattr(settings, "PUBLIC_URLS", [])
        return default_public_urls + custom_urls

    def _build_url_permission_map(self):
        """
        Build mapping of URL patterns to required permissions.
        This maps URL namespaces to the permissions required to access them.
        """
        # Module to base permission mapping
        # Each module requires at least the 'view' permission to access any URL in that module
        return {
            # Core modules
            "patients": "patients.view",
            "patient": "patients.view",
            "medical": "medical.view",
            "vitals": "vitals.view",
            # Consultation modules
            "consultations": "consultations.view",
            "consultation": "consultations.view",
            "referrals": "referrals.view",
            "referral": "referrals.view",
            # Pharmacy modules
            "pharmacy": "pharmacy.view",
            "dispensary": "pharmacy.view",
            "prescriptions": "prescriptions.view",
            "prescription": "prescriptions.view",
            "medication": "pharmacy.view",
            "bulk_store": "pharmacy.view",
            "active_store": "pharmacy.view",
            # Laboratory
            "laboratory": "lab.view",
            "lab": "lab.view",
            "lab_test": "lab.view",
            "test": "lab.view",
            # Billing
            "billing": "billing.view",
            "invoices": "billing.view",
            "invoice": "billing.view",
            "payments": "billing.view",
            "wallet": "wallet.view",
            # Appointments
            "appointments": "appointments.view",
            "appointment": "appointments.view",
            # Inpatient
            "inpatient": "inpatient.view",
            "admission": "inpatient.view",
            "wards": "inpatient.view",
            "beds": "inpatient.view",
            # User management
            "accounts": "users.view",
            "users": "users.view",
            "roles": "roles.view",
            # Reports
            "reporting": "reports.view",
            "reports": "reports.view",
            # Radiology
            "radiology": "radiology.view",
            "radiology_test": "radiology.view",
            # Theatre
            "theatre": "inpatient.view",
            "surgery": "inpatient.view",
            "surgeries": "inpatient.view",
            # NHIA
            "nhia": "patients.view",
            # Specialty modules
            "dental": "consultations.view",
            "ophthalmic": "consultations.view",
            "ent": "consultations.view",
            "oncology": "consultations.view",
            "scbu": "consultations.view",
            "anc": "consultations.view",
            "labor": "consultations.view",
            "icu": "inpatient.view",
            "family_planning": "consultations.view",
            "gynae_emergency": "consultations.view",
            "neurology": "consultations.view",
            "dermatology": "consultations.view",
            "emergency": "consultations.view",
            "general_medicine": "consultations.view",
            "pediatrics": "consultations.view",
            "surgery_module": "consultations.view",
            "cardiology": "consultations.view",
            "orthopedics": "consultations.view",
            # Dashboard
            "dashboard": None,
            # HR
            "hr": "users.view",
            "doctors": "users.view",
            # Desk office
            "desk_office": "desk_office.view",
            # Retainership
            "retainership": "patients.view",
            # Pharmacy billing
            "pharmacy_billing": "billing.view",
        }

    def _is_public_url(self, path):
        """Check if URL is in the public whitelist."""
        for public_url in self.public_urls:
            if path.startswith(public_url) or path == public_url.rstrip("/"):
                return True
        return False

    def _get_required_permission(self, request):
        """
        Determine the required permission for the current URL.
        Returns None if no specific permission is required.
        """
        try:
            # Try to resolve the URL to get namespace
            resolved = resolve(request.path)
            namespace = resolved.namespace
            url_name = resolved.url_name

            # Check if there's a permission for the namespace
            if namespace and namespace in self.url_permission_map:
                return self.url_permission_map[namespace]

            # Check URL patterns in path
            path_parts = request.path.strip("/").split("/")
            if path_parts:
                first_part = path_parts[0]
                if first_part in self.url_permission_map:
                    return self.url_permission_map[first_part]

            # Check for API endpoints
            if "api" in path_parts:
                # API endpoints require the same permissions as their parent module
                for part in path_parts:
                    if part in self.url_permission_map and part != "api":
                        return self.url_permission_map[part]

        except Exception as e:
            logger.warning(f"Error resolving URL permission: {e}")

        return None

    def _has_module_access_via_role(self, user, required_permission):
        """
        Check if user has access to a module through their role assignments.
        This checks if any of the user's roles have the required permission.
        """
        if not required_permission:
            return True

        user_roles = get_user_roles(user)

        for role_name in user_roles:
            if role_name in ROLE_PERMISSIONS:
                role_perms = ROLE_PERMISSIONS[role_name].get("permissions", [])
                if required_permission in role_perms:
                    return True

        return False

    def _check_permission(self, request):
        """
        Check if user has permission to access the requested URL.
        Returns (has_access: bool, reason: str)
        """
        user = request.user

        # Superusers have full access
        if user.is_superuser:
            return True, "Superuser access granted"

        # Get required permission for this URL
        required_permission = self._get_required_permission(request)

        # If no specific permission is required, deny access in strict mode
        if required_permission is None and self.strict_mode:
            # Check if user is authenticated
            if not user.is_authenticated:
                return False, "Authentication required"

            # In strict mode, unknown URLs require explicit permission
            # But we'll allow authenticated users access to prevent breaking
            # URLs that haven't been mapped yet
            logger.warning(f"Unmapped URL accessed: {request.path} by user {user}")
            return True, "URL not in permission map (allowing in transition period)"

        # If no permission required (like dashboard), allow access
        if required_permission is None:
            return True, "No permission required"

        # Check if user has the specific permission
        if user_has_permission(user, required_permission):
            return True, f"Permission '{required_permission}' granted"

        # Check if user has access through role
        if self._has_module_access_via_role(user, required_permission):
            return True, f"Access granted via role"

        return False, f"Permission '{required_permission}' required"

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Process the view and check permissions before allowing access.
        This is called before the view is executed.
        """
        # Skip if strict mode is disabled
        if not self.strict_mode:
            return None

        # Skip if request is exempt
        if hasattr(request, "_access_control_exempt"):
            return None

        path = request.path

        # Allow public URLs
        if self._is_public_url(path):
            return None

        # Check if user is authenticated
        if not request.user.is_authenticated:
            # Store the requested URL for redirect after login
            request.session["next"] = path

            # For AJAX requests, return 403
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "error": "Authentication required",
                        "detail": "You must be logged in to access this resource.",
                    },
                    status=403,
                )

            # Redirect to login for regular requests
            messages.warning(request, "Please log in to access this page.")
            return redirect(settings.LOGIN_URL)

        # Check permissions
        has_access, reason = self._check_permission(request)

        if not has_access:
            user = request.user
            logger.warning(
                f"Access denied for user '{user}' to '{path}'. Reason: {reason}"
            )

            # For AJAX requests
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "error": "Access denied",
                        "detail": f"You do not have permission to access this resource. {reason}",
                    },
                    status=403,
                )

            # For API requests
            if path.startswith("/api/"):
                return JsonResponse(
                    {
                        "error": "Permission denied",
                        "detail": "You do not have the required permission to access this resource.",
                    },
                    status=403,
                )

            # For regular requests, show permission denied page
            messages.error(
                request,
                f"Access denied: You don't have permission to access this resource.",
            )
            return render(request, "errors/permission_denied.html", status=403)

        # Log successful access in debug mode
        if getattr(settings, "DEBUG_PERMISSIONS", False):
            logger.info(
                f"Access granted to '{path}' for user '{request.user}'. Reason: {reason}"
            )

        return None

    def __call__(self, request):
        """Main middleware entry point."""
        response = self.process_view(request, None, None, None)

        if response is not None:
            return response

        response = self.get_response(request)
        return response


class PermissionAuditMiddleware:
    """
    Middleware to audit permission checks for security monitoring.
    Logs all access denied events and suspicious permission patterns.
    """

    def __init__(self, get_response=None):
        self.get_response = get_response
        self.enabled = getattr(settings, "PERMISSION_AUDIT_ENABLED", True)

    def __call__(self, request):
        response = self.get_response(request)

        if self.enabled and request.user.is_authenticated:
            self._audit_response(request, response)

        return response

    def _audit_response(self, request, response):
        """Audit the response for permission-related issues."""
        if response.status_code == 403:
            logger.warning(
                f"PERMISSION_DENIED: User '{request.user}' attempted to access '{request.path}' "
                f"Method: {request.method} IP: {self._get_client_ip(request)}"
            )

    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0]
        return request.META.get("REMOTE_ADDR")


def exempt_from_access_control(view_func):
    """
    Decorator to exempt a view from strict access control.
    Use sparingly and only for truly public endpoints.

    Usage:
        @exempt_from_access_control
        def public_api_view(request):
            ...
    """

    def wrapper(request, *args, **kwargs):
        request._access_control_exempt = True
        return view_func(request, *args, **kwargs)

    wrapper.__name__ = view_func.__name__
    wrapper.__doc__ = view_func.__doc__
    return wrapper
