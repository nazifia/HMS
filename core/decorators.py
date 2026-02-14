from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.core.cache import cache


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
                return redirect("accounts:login")

            # Allow superusers to access everything without role restrictions
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Get user's roles from many-to-many and legacy profile field
            user_roles = list(request.user.roles.values_list("name", flat=True))
            profile_role = getattr(getattr(request.user, "profile", None), "role", None)
            if profile_role and profile_role not in user_roles:
                user_roles.append(profile_role)

            # Check if user has any of the required roles
            if not any(role in allowed_roles for role in user_roles):
                messages.error(
                    request, "You don't have permission to access this page."
                )
                return redirect("dashboard:dashboard")

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
    return role_required(["admin"])(view_func)


def doctor_required(view_func):
    """
    Decorator to restrict view access to doctors only.

    Usage:
        @doctor_required
        def doctor_only_view(request):
            ...
    """
    return role_required(["doctor", "admin"])(view_func)


def pharmacist_required(view_func):
    """
    Decorator to restrict view access to pharmacists only.

    Usage:
        @pharmacist_required
        def pharmacist_only_view(request):
            ...
    """
    return role_required(["pharmacist", "admin"])(view_func)


def lab_technician_required(view_func):
    """
    Decorator to restrict view access to lab technicians only.

    Usage:
        @lab_technician_required
        def lab_technician_only_view(request):
            ...
    """
    return role_required(["lab_technician", "admin"])(view_func)


def nurse_required(view_func):
    """
    Decorator to restrict view access to nurses only.

    Usage:
        @nurse_required
        def nurse_only_view(request):
            ...
    """
    return role_required(["nurse", "admin"])(view_func)


def accountant_required(view_func):
    """
    Decorator to restrict view access to accountants only.

    Usage:
        @accountant_required
        def accountant_only_view(request):
            ...
    """
    return role_required(["accountant", "admin"])(view_func)


def receptionist_required(view_func):
    """
    Decorator to restrict view access to receptionists only.

    Usage:
        @receptionist_required
        def receptionist_only_view(request):
            ...
    """
    return role_required(["receptionist", "health_record_officer", "admin"])(view_func)


def health_record_officer_required(view_func):
    """
    Decorator to restrict view access to health record officers only.

    Usage:
        @health_record_officer_required
        def health_record_officer_only_view(request):
            ...
    """
    return role_required(["health_record_officer", "receptionist", "admin"])(view_func)


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

            # Get user's roles from many-to-many and legacy profile field
            user_roles = list(request.user.roles.values_list("name", flat=True))
            profile_role = getattr(getattr(request.user, "profile", None), "role", None)
            if profile_role and profile_role not in user_roles:
                user_roles.append(profile_role)

            # Check if user has any of the required roles
            if not any(role in allowed_roles for role in user_roles):
                return HttpResponseForbidden("Permission denied")

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def department_access_required(department_name):
    """
    Decorator to restrict view access to users assigned to a specific department.
    Superusers have unrestricted access to all departments.
    Users with appropriate permissions can also access without department assignment.
    Supports both single department and multiple departments assignment.

    Args:
        department_name: Name of the department (case-insensitive)

    Usage:
        @department_access_required('Dental')
        def dental_dashboard(request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                messages.error(request, "You must be logged in to access this page.")
                return redirect("accounts:login")

            # Allow superusers to access all departments
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Get user's department(s)
            user_departments = []

            # Check primary department (single department field - backward compatibility)
            if (
                hasattr(request.user, "profile")
                and request.user.profile
                and request.user.profile.department
            ):
                user_departments.append(request.user.profile.department)

            # Check multiple departments (ManyToMany field)
            if (
                hasattr(request.user, "profile")
                and request.user.profile
                and hasattr(request.user.profile, "departments")
            ):
                user_departments.extend(request.user.profile.departments.all())

            # Remove duplicates
            user_departments = list(set(user_departments))

            # Check if user has any department assigned
            if not user_departments:
                # Allow access if user has the role/permission for this department
                # Map department names to expected roles/permissions
                dept_role_map = {
                    "laboratory": ["lab_technician", "lab.view"],
                    "pharmacy": ["pharmacist", "pharmacy.view"],
                    "radiology": ["radiology_staff", "radiology.view"],
                    "dental": ["doctor", "dental.view"],
                    "ophthalmic": ["doctor", "ophthalmic.view"],
                    "ent": ["doctor", "ent.view"],
                    "neurology": ["doctor", "neurology.view"],
                    "oncology": ["doctor", "oncology.view"],
                    "dermatology": ["doctor", "dermatology.view"],
                    "cardiology": ["doctor", "cardiology.view"],
                    "orthopedics": ["doctor", "orthopedics.view"],
                    "pediatrics": ["doctor", "pediatrics.view"],
                    "surgery": ["doctor", "surgery.view"],
                    "emergency": ["doctor", "emergency.view"],
                    "general medicine": ["doctor", "general_medicine.view"],
                    "icu": ["doctor", "icu.view"],
                    "scbu": ["nurse", "scbu.view"],
                    "anc": ["doctor", "anc.view"],
                    "labor": ["doctor", "labor.view"],
                    "family planning": ["doctor", "family_planning.view"],
                    "gynae emergency": ["doctor", "gynae_emergency.view"],
                }

                allowed_roles_perms = dept_role_map.get(department_name.lower(), [])
                user_roles = []
                if hasattr(request.user, "roles"):
                    user_roles = list(request.user.roles.values_list("name", flat=True))

                # Check if user has any allowed role or permission
                has_access = False
                for role_perm in allowed_roles_perms:
                    if role_perm in user_roles:
                        has_access = True
                        break
                    # Check permission using user_has_permission
                    from accounts.permissions import user_has_permission

                    if user_has_permission(request.user, role_perm):
                        has_access = True
                        break

                if has_access:
                    return view_func(request, *args, **kwargs)

                messages.error(
                    request, "You must be assigned to a department to access this page."
                )
                return redirect("dashboard:dashboard")

            # Check if user's department(s) include the required department (case-insensitive)
            dept_names = [d.name.upper() for d in user_departments]
            if department_name.upper() not in dept_names:
                dept_list = ", ".join([d.name for d in user_departments])
                messages.error(
                    request,
                    f"Access denied. This page is for {department_name} department staff only. "
                    f"You are assigned to: {dept_list}.",
                )
                return redirect("dashboard:dashboard")

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def ui_permission_required(element_id, redirect_url="dashboard:dashboard"):
    """
    Decorator to restrict view access based on UI permissions.
    Superusers bypass all UI permission checks.

    Args:
        element_id: The UI permission element_id to check
        redirect_url: URL to redirect to if permission is denied (default: dashboard)

    Usage:
        @ui_permission_required('menu_pharmacy')
        def pharmacy_dashboard(request):
            ...

        @ui_permission_required('btn_create_invoice')
        def create_invoice(request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                messages.error(request, "You must be logged in to access this page.")
                return redirect("accounts:login")

            # Allow superusers to access everything
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check cache first for performance
            cache_key = f"ui_perm_{request.user.id}_{element_id}"
            has_permission = cache.get(cache_key)

            if has_permission is None:
                # Import here to avoid circular imports
                from core.models import UIPermission

                try:
                    ui_perm = UIPermission.objects.get(
                        element_id=element_id, is_active=True
                    )
                    has_permission = ui_perm.user_can_access(request.user)
                    # Cache the result for 5 minutes
                    cache.set(cache_key, has_permission, 300)
                except UIPermission.DoesNotExist:
                    # If permission doesn't exist, allow access (backward compatible)
                    has_permission = True
                    cache.set(cache_key, has_permission, 300)

            if not has_permission:
                messages.error(
                    request,
                    "You don't have permission to access this page. "
                    "Please contact your administrator if you believe this is an error.",
                )
                return redirect(redirect_url)

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def api_ui_permission_required(element_id):
    """
    Decorator for API views to restrict access based on UI permissions.
    Returns 403 Forbidden instead of redirecting.

    Args:
        element_id: The UI permission element_id to check

    Usage:
        @api_ui_permission_required('menu_pharmacy')
        def pharmacy_api_view(request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Authentication required")

            # Allow superusers to access everything
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check cache first for performance
            cache_key = f"ui_perm_{request.user.id}_{element_id}"
            has_permission = cache.get(cache_key)

            if has_permission is None:
                # Import here to avoid circular imports
                from core.models import UIPermission

                try:
                    ui_perm = UIPermission.objects.get(
                        element_id=element_id, is_active=True
                    )
                    has_permission = ui_perm.user_can_access(request.user)
                    # Cache the result for 5 minutes
                    cache.set(cache_key, has_permission, 300)
                except UIPermission.DoesNotExist:
                    # If permission doesn't exist, allow access (backward compatible)
                    has_permission = True
                    cache.set(cache_key, has_permission, 300)

            if not has_permission:
                return HttpResponseForbidden(
                    "You don't have permission to access this resource"
                )

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
