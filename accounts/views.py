import logging
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import CustomUserProfile, Department, Role, AuditLog, CustomUser
from .forms import (
    CustomLoginForm,
    UserProfileForm,
    StaffCreationForm,
    DepartmentForm,
    UserRegistrationForm,
    RoleForm,
    UserRoleAssignmentForm,
    BulkUserActionForm,
    PermissionFilterForm,
    AdvancedUserSearchForm,
)
from core.models import InternalNotification
from core.activity_log import ActivityLog
from django.utils import timezone
from django.db import models
from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.urls import reverse

# Import permission decorators
from accounts.permissions import (
    permission_required,
    role_required,
    user_has_permission,
    user_in_role,
    check_user_management_access,
    get_user_roles,
)


# Custom decorators for backward compatibility
def user_passes_test(test_func):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not test_func(request.user):
                from django.contrib.auth.decorators import PermissionDenied

                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.roles.filter(name="admin").exists()
    )


def is_admin_or_staff(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


from django.conf import settings

User = get_user_model()
logger = logging.getLogger(__name__)


# Helper function to check if user is admin
def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.roles.filter(name="admin").exists()
    )


# def user_dashboard(request):
#     users = User.objects.all()  # Now using the correct model
#     return render(request, 'accounts/user_dashboard.html', {'users': users})


# def custom_login_view(request):

#     if request.method == 'POST':
#         form = CustomLoginForm(request=request, data=request.POST)
#         if form.is_valid():
#             username = form.cleaned_data['username']
#             password = form.cleaned_data['password']
#             user = authenticate(request, username=username, password=password)
#             if user is not None:
#                 login(request, user)  # ✅ This avoids the backend error
#                 return redirect('dashboard:dashboard')  # Replace with your homepage or dashboard
#             else:
#                 form.add_error(None, 'Invalid login credentials')
#     else:
#         form = CustomLoginForm()

#     return render(request, 'accounts/login.html', {'form': form})


from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.urls import reverse


# Custom decorators for backward compatibility
def user_passes_test(test_func):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not test_func(request.user):
                from django.contrib.auth.decorators import PermissionDenied

                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.roles.filter(name="admin").exists()
    )


def is_admin_or_staff(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


from django.http import JsonResponse
from .forms import CustomLoginForm
from .auth_wrapper import safe_authenticate


def custom_login_view(request):
    """
    Custom login view for application users (using phone numbers).
    Admin users should use /admin/ directly.
    Uses safe_authenticate to prevent Windows OSError [Errno 22].
    """
    # Redirect if already logged in - with safety check for request.user
    if hasattr(request, "user") and request.user.is_authenticated:
        return redirect("dashboard:dashboard")

    # Handle auto logout scenarios
    auto_logout = request.GET.get("auto_logout")
    logout_reason = request.GET.get("reason", "unknown")

    if auto_logout:
        if logout_reason == "inactivity":
            messages.warning(
                request,
                "Your session has expired due to inactivity. Please log in again to continue.",
            )
        elif logout_reason == "security":
            messages.error(
                request,
                "You have been logged out for security reasons. Please log in again.",
            )
        elif logout_reason == "concurrent":
            messages.info(
                request,
                "You have been logged out because your account was accessed from another location.",
            )
        else:
            messages.info(
                request, "Your session has ended. Please log in again to continue."
            )

    if request.method == "POST":
        form = CustomLoginForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]  # This will be phone number
            password = form.cleaned_data["password"]

            # Use safe authentication to prevent Windows console errors
            user = safe_authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_active:
                    # Clear any existing pharmacy dispensary session on new login
                    if "selected_dispensary_id" in request.session:
                        del request.session["selected_dispensary_id"]
                    if "selected_dispensary_name" in request.session:
                        del request.session["selected_dispensary_name"]

                    login(request, user)

                    # Success message based on context
                    if auto_logout:
                        messages.success(
                            request,
                            f"Welcome back, {user.get_full_name()}! You have been successfully logged in again.",
                        )
                    else:
                        messages.success(
                            request, f"Welcome back, {user.get_full_name()}!"
                        )

                    # Redirect to next page or dashboard
                    next_page = request.GET.get("next", "dashboard:dashboard")
                    return redirect(next_page)
                else:
                    messages.error(
                        request,
                        "Your account has been deactivated. Please contact support.",
                    )
            else:
                messages.error(
                    request, "Invalid phone number or password. Please try again."
                )
    else:
        form = CustomLoginForm()

    # Prepare context with auto logout information
    context = {
        "form": form,
        "title": "Login",
        "page_title": "HMS - Login",
        "auto_logout": auto_logout,
        "logout_reason": logout_reason,
        "show_session_expired_alert": auto_logout == "1"
        and logout_reason == "inactivity",
    }
    return render(request, "accounts/login.html", context)


def custom_logout_view(request):
    """
    Custom logout view that handles auto logout scenarios and AJAX requests
    """
    # Get logout reason from request
    logout_reason = request.GET.get("reason", "manual")
    auto_logout = request.GET.get("auto_logout", "0")

    # Log the logout event
    if hasattr(request, "user") and request.user.is_authenticated:
        username = request.user.username
        user_id = request.user.id

        # Log to application logs instead of print to avoid Windows OSError
        logger.info(
            f"User {username} (ID: {user_id}) logged out. Reason: {logout_reason}"
        )

    # Clear pharmacy dispensary session before logout
    if "selected_dispensary_id" in request.session:
        del request.session["selected_dispensary_id"]
    if "selected_dispensary_name" in request.session:
        del request.session["selected_dispensary_name"]

    # Perform logout
    logout(request)

    # Handle AJAX requests (from auto logout)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "message": "Logged out successfully",
                "redirect_url": f"/accounts/login/?auto_logout=1&reason={logout_reason}",
            }
        )

    # Handle regular requests
    if auto_logout == "1":
        # Redirect to login with auto logout parameters
        return redirect(f"/accounts/login/?auto_logout=1&reason={logout_reason}")
    else:
        # Regular logout - redirect to login with success message
        messages.success(request, "You have been successfully logged out.")
        return redirect("accounts:login")


def dashboard_view(request):
    return render(request, "dashboard/dashboard.html")


@login_required
def profile(request):
    """View for user profile. Allows viewing own or others' profiles if authorized."""
    user_id_param = request.GET.get("user_id")
    target_user_for_view = None  # Initialize

    if user_id_param:
        # Check if the logged-in user is authorized to view another profile
        if not (
            request.user.is_staff
            or request.user.is_superuser
            or str(request.user.id) == user_id_param
        ):
            messages.error(request, "You are not authorized to view this profile.")
            # Redirect to logged-in user's own profile or dashboard
            return redirect(
                reverse("accounts:profile")
                if hasattr(request.user, "id")
                else "dashboard:dashboard"
            )

        try:
            # Fetch the user whose profile is being viewed
            target_user_for_view = User.objects.select_related("profile").get(
                pk=user_id_param
            )
        except User.DoesNotExist:
            messages.error(request, "The requested user profile was not found.")
            return redirect("dashboard:dashboard")  # Or a more appropriate redirect
    else:
        # Viewing own profile, ensure request.user is fully loaded with profile relation
        # Note: request.user is a SimpleLazyObject. Accessing its attributes resolves it.
        # We fetch it again with select_related to ensure profile is efficiently loaded.
        target_user_for_view = User.objects.select_related("profile").get(
            pk=request.user.pk
        )

    # At this point, target_user_for_view is a CustomUser instance.
    # Access its profile using the @property 'profile'
    user_profile_instance = target_user_for_view.profile

    if user_profile_instance is None:
        # This case means the CustomUser exists, but their CustomUserProfile record does not.
        # This could be due to a signal failure or manual DB operation.
        # You might want to log this or even create a profile on-the-fly.
        messages.warning(
            request,
            f"Profile data for {target_user_for_view.username} is incomplete or missing.",
        )
        # Optionally, create one if it makes sense for your application:
        # user_profile_instance, _ = CustomUserProfile.objects.get_or_create(user=target_user_for_view)

    context = {
        "viewed_user_profile": user_profile_instance,  # This is the CustomUserProfile instance (or None)
        "viewed_user_object": target_user_for_view,  # This is the CustomUser instance
    }
    return render(request, "accounts/profile.html", context)


@login_required
def edit_profile(request):
    user_id_to_edit = request.GET.get("user_id")
    target_user = None

    # Determine which user's profile to edit
    if user_id_to_edit:
        # Allow staff/superusers to edit others, or users to edit their own
        if not (
            request.user.is_staff
            or request.user.is_superuser
            or str(request.user.id) == user_id_to_edit
        ):
            messages.error(request, "You are not authorized to edit this profile.")
            # Redirect to their own profile or a safe page
            return redirect(
                reverse("accounts:profile")
                + (f"?user_id={request.user.id}" if request.user.id else "")
            )

        try:
            # Fetch the CustomUser instance directly
            target_user = User.objects.get(pk=user_id_to_edit)
        except User.DoesNotExist:
            messages.error(request, "User to edit not found.")
            return redirect(
                reverse("dashboard:dashboard")
            )  # Or a more appropriate page
    else:
        # If no user_id, edit the logged-in user's profile
        target_user = request.user

    # target_user is now the CustomUser instance whose profile is being edited.
    # The form's __init__ will handle accessing target_user.profile.

    if request.method == "POST":
        # Check if username is empty in the POST data and set it to the current username
        post_data = request.POST.copy()  # Make a mutable copy of the POST data
        if not post_data.get("username") and target_user:
            post_data["username"] = target_user.username

        # Pass the modified POST data to the form
        form = UserProfileForm(
            post_data, request.FILES, instance=target_user, request_user=request.user
        )
        if form.is_valid():
            form.save()  # The form's save method now handles saving both User and Profile
            messages.success(
                request,
                f"{target_user.username}'s profile has been updated successfully!",
            )
            return redirect(reverse("accounts:profile") + f"?user_id={target_user.id}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pass the CustomUser instance (target_user) to the form
        form = UserProfileForm(instance=target_user, request_user=request.user)

    context = {
        "form": form,
        "profile_user_object": target_user,  # Pass the user object for template context
        "page_title": f"Edit Profile: {target_user.username}",
        # Add a flag for template to conditionally show admin fields
        "can_edit_admin_fields": request.user.is_staff or request.user.is_superuser,
    }
    return render(request, "accounts/edit_profile.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def staff_list(request):
    """View for listing all staff members (admin only)"""
    staff = CustomUserProfile.objects.all().order_by("role", "user__phone_number")
    context = {"staff": staff}
    return render(request, "accounts/staff_list.html", context)


def send_staff_onboarding_task_to_mcp(user):
    """
    Simulate sending a staff onboarding task to context7 MCP/Taskmaster.
    Replace with real MCP/Taskmaster API integration as needed.
    """
    payload = {
        "task_type": "staff_onboarding",
        "user_id": user.id,
        "username": user.username,
        "full_name": user.get_full_name(),
        "role": user.profile.role,
        "department": user.profile.department,
        "employee_id": user.profile.employee_id,
        "created_at": str(user.date_joined),
        "status": "new",
        "source": "accounts",
    }
    import logging

    logger = logging.getLogger("accounts.mcp")
    logger.info(f"[MCP/Taskmaster] Staff onboarding task payload: {payload}")
    # You could also use Django messages for demo:
    # from django.contrib import messages
    # messages.info(None, f"[Taskmaster/MCP] Staff onboarding task sent for {user.username} via MCP/Taskmaster.")


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def add_staff(request):
    """View for adding new staff member (admin only)"""
    if request.method == "POST":
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_staff_onboarding_task_to_mcp(user)
            messages.success(request, f"Account created for {user.username}!")
            return redirect("accounts:staff_list")
    else:
        form = StaffCreationForm()

    context = {"form": form, "title": "Add Staff Member"}
    return render(request, "accounts/staff_form.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def edit_staff(request, staff_id):
    """View for editing staff member (admin only)"""
    user_profile = get_object_or_404(CustomUserProfile, id=staff_id)
    user = user_profile.user

    if request.method == "POST":
        form = UserProfileForm(
            request.POST, request.FILES, instance=user, request_user=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, f"{user.username}'s profile has been updated!")
            return redirect("accounts:staff_list")
    else:
        form = UserProfileForm(instance=user, request_user=request.user)

    context = {"form": form, "title": f"Edit {user.username}", "staff_id": staff_id}
    return render(request, "accounts/staff_form.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def delete_staff(request, staff_id):
    """View for deleting staff member (admin only)"""
    user_profile = get_object_or_404(CustomUserProfile, id=staff_id)
    user = user_profile.user

    if request.method == "POST":
        # Instead of deleting, we can deactivate the user
        user.is_active = False
        user.save()
        user_profile.is_active = False
        user_profile.save()
        messages.success(request, f"{user.username} has been deactivated!")
        return redirect("accounts:staff_list")

    context = {"user_profile": user_profile}
    return render(request, "accounts/delete_staff.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def department_list(request):
    """View for listing all departments (admin only)"""
    departments = Department.objects.all().order_by("name")
    context = {"departments": departments}
    return render(request, "accounts/department_list.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def add_department(request):
    """View for adding new department (admin only)"""
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department has been added successfully!")
            return redirect("accounts:department_list")
    else:
        form = DepartmentForm()

    context = {"form": form, "title": "Add Department"}
    return render(request, "accounts/department_form.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def edit_department(request, department_id):
    """View for editing department (admin only)"""
    department = get_object_or_404(Department, id=department_id)

    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, f"Department {department.name} has been updated!")
            return redirect("accounts:department_list")
    else:
        form = DepartmentForm(instance=department)

    context = {
        "form": form,
        "title": f"Edit {department.name}",
        "department_id": department_id,
    }
    return render(request, "accounts/department_form.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def delete_department(request, department_id):
    """View for deleting department (admin only)"""
    department = get_object_or_404(Department, id=department_id)

    if request.method == "POST":
        department.delete()
        messages.success(request, f"Department {department.name} has been deleted!")
        return redirect("accounts:department_list")

    context = {"department": department}
    return render(request, "accounts/delete_department.html", context)


@login_required
def api_users(request):
    """API view for getting user information"""
    role = request.GET.get("role", None)

    users_query = User.objects.filter(is_active=True)

    if role:
        # Support both many-to-many roles and profile role
        users_query = users_query.filter(
            Q(roles__name__iexact=role) | Q(profile__role__iexact=role)
        ).distinct()

    users = users_query.select_related("profile").prefetch_related("roles")

    results = []
    for user in users:
        user_roles = list(user.roles.values_list("name", flat=True))
        results.append(
            {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": user.get_full_name(),
                "roles": user_roles,
                "department": user.profile.department.name
                if (user.profile and user.profile.department)
                else None,
            }
        )

    return JsonResponse(results, safe=False)


def register(request):
    """User registration view using phone number as authentication."""
    from .forms import UserRegistrationForm

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Optionally create CustomUserProfile and set phone_number here
            profile = user.get_profile
            profile.phone_number = form.cleaned_data["phone_number"]
            profile.save()
            # Assign selected module (role) to user
            selected_role = form.cleaned_data["module"]
            user.roles.set(
                [selected_role]
            )  # Remove any other roles, only assign selected
            # Assign permissions from the selected role
            user.user_permissions.set(selected_role.permissions.all())
            user.save()
            messages.success(
                request, "Your account has been created. You can now log in."
            )
            return redirect("accounts:login")
        else:
            logger.debug("Registration form errors: %s", form.errors.as_json())
    else:
        form = UserRegistrationForm()
    return render(
        request, "accounts/register.html", {"form": form, "title": "Register"}
    )


@login_required
@permission_required("roles.create")
def create_role(request):
    if request.method == "POST":
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Role created successfully.")
            return redirect("accounts:role_management")
    else:
        form = RoleForm()
    context = {"form": form, "page_title": "Create Role"}
    return render(request, "accounts/role_form.html", context)


@login_required
def role_demo(request):
    return render(request, "accounts/role_demo.html", {"page_title": "Role Demo"})


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def audit_logs(request):
    logs = AuditLog.objects.all().order_by("-timestamp")
    form = AuditLogFilterForm(request.GET)
    if form.is_valid():
        user = form.cleaned_data.get("user")
        action = form.cleaned_data.get("action")
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")

        if user:
            logs = logs.filter(user=user)
        if action:
            logs = logs.filter(action=action)
        if start_date:
            logs = logs.filter(timestamp__gte=start_date)
        if end_date:
            logs = logs.filter(timestamp__lte=end_date)

    paginator = Paginator(logs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {"logs": page_obj, "form": form, "page_title": "Audit Logs"}
    return render(request, "accounts/audit_logs.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def permission_management(request):
    permissions = Permission.objects.all()
    form = PermissionFilterForm(request.GET)
    if form.is_valid():
        content_type = form.cleaned_data.get("content_type")
        if content_type:
            permissions = permissions.filter(content_type=content_type)

    context = {
        "permissions": permissions,
        "form": form,
        "page_title": "Permission Management",
    }
    return render(request, "accounts/permission_management.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_user_actions(request):
    if request.method == "POST":
        form = BulkUserActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]
            users = form.cleaned_data["users"]
            if action == "activate":
                users.update(is_active=True)
            elif action == "deactivate":
                users.update(is_active=False)
            elif action == "assign_role":
                role = form.cleaned_data["role"]
                for user in users:
                    user.roles.set([role])
            messages.success(
                request, f'Bulk action "{action}" applied to {users.count()} users.'
            )
            return redirect("accounts:user_dashboard")
    return redirect("accounts:user_dashboard")


@login_required
@permission_required("users.edit")
def user_privileges(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        form = UserRoleAssignmentForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(
                request, f"Roles for {user.username} updated successfully."
            )
            return redirect("accounts:user_dashboard")
    else:
        form = UserRoleAssignmentForm(instance=user)
    context = {
        "form": form,
        "user": user,
        "page_title": f"Manage Roles for {user.username}",
    }
    return render(request, "accounts/user_privileges.html", context)


@login_required
@permission_required("roles.edit")
def delete_role(request, role_id):
    role = get_object_or_404(Role, id=role_id)
    if request.method == "POST":
        role.delete()
        messages.success(request, "Role deleted successfully.")
        return redirect("accounts:role_management")
    context = {"role": role, "page_title": f"Delete Role: {role.name}"}
    return render(request, "accounts/role_confirm_delete.html", context)


@login_required
@permission_required("users.view")
def user_dashboard(request):
    """Admin user management dashboard: filter, search, bulk actions, CSV export."""
    users = User.objects.all().select_related("profile")
    # Filters
    search = request.GET.get("search", "")
    role = request.GET.get("role", "")
    is_active = request.GET.get("is_active", "")
    if search:
        users = users.filter(
            Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
        )
    if role:
        users = users.filter(profile__role=role)
    if is_active == "true":
        users = users.filter(is_active=True)
    elif is_active == "false":
        users = users.filter(is_active=False)

    # Bulk actions
    if request.method == "POST" and "bulk_action" in request.POST:
        action = request.POST.get("bulk_action")
        selected_ids = request.POST.getlist("selected_users")
        if selected_ids:
            qs = User.objects.filter(id__in=selected_ids)

            # Prevent deletion of superusers and self in bulk operations
            if action == "delete":
                # Exclude superusers (except self) and current user from deletion
                deletable_users = qs.exclude(
                    Q(is_superuser=True) & ~Q(id=request.user.id)
                ).exclude(id=request.user.id)

                deleted_count = deletable_users.count()
                deleted_usernames = list(
                    deletable_users.values_list("username", flat=True)
                )
                deleted_ids = list(deletable_users.values_list("id", flat=True))

                # Get detailed info about objects that will be deleted for audit log
                deletion_audit_data = []
                for user_obj in deletable_users:
                    user_info = {
                        "id": user_obj.id,
                        "username": user_obj.username,
                        "email": user_obj.email,
                        "related_objects": {},
                    }

                    try:
                        user_info["related_objects"]["profile"] = str(user_obj.profile)
                    except:
                        user_info["related_objects"]["profile"] = None

                    user_info["related_objects"]["roles_count"] = user_obj.roles.count()

                    # Get other related counts if the models exist
                    if hasattr(user_obj, "user_sessions"):
                        user_info["related_objects"]["sessions_count"] = (
                            user_obj.user_sessions.count()
                        )
                    else:
                        user_info["related_objects"]["sessions_count"] = 0

                    if hasattr(user_obj, "user_activities"):
                        user_info["related_objects"]["activities_count"] = (
                            user_obj.user_activities.count()
                        )
                    else:
                        user_info["related_objects"]["activities_count"] = 0

                    if hasattr(user_obj, "notifications"):
                        user_info["related_objects"]["notifications_count"] = (
                            user_obj.notifications.count()
                        )
                    else:
                        user_info["related_objects"]["notifications_count"] = 0

                    deletion_audit_data.append(user_info)

                # Perform complete database deletion with cascade
                deletion_result = deletable_users.delete()

                # Verify complete deletion
                remaining_users = User.objects.filter(id__in=deleted_ids).count()
                if remaining_users > 0:
                    raise Exception(
                        f"{remaining_users} users still exist in database after bulk deletion attempt"
                    )

                from django.contrib import messages

                messages.success(
                    request,
                    f"Successfully deleted {deleted_count} user(s) and all associated data from database.",
                )

                # Detailed audit log for bulk deletion
                AuditLog.objects.create(
                    user=request.user,
                    action="delete",
                    details={
                        "action": "bulk_user_deletion_complete",
                        "deleted_users_count": deleted_count,
                        "deleted_usernames": deleted_usernames,
                        "deleted_user_ids": deleted_ids,
                        "performed_by": request.user.username,
                        "total_objects_deleted": deletion_result[1]
                        if deletion_result and len(deletion_result) > 1
                        else "unknown",
                        "detailed_deletion_info": deletion_audit_data,
                        "timestamp": timezone.now().isoformat(),
                    },
                    timestamp=timezone.now(),
                )

                # Notify superusers about bulk deletion
                superusers = User.objects.filter(is_superuser=True)
                for superuser in superusers:
                    InternalNotification.objects.create(
                        user=superuser,
                        message=f"Bulk user deletion performed by {request.user.username}. {deleted_count} users and all their data were permanently removed from database.",
                    )

                return redirect("accounts:user_dashboard")

            elif action == "activate":
                qs.update(is_active=True)
            elif action == "deactivate":
                qs.update(is_active=False)

            # Role assignment (if provided)
            new_role = request.POST.get("assign_role")
            if action == "assign_role" and new_role:
                for user in qs:
                    user.get_profile.role = new_role
                    user.get_profile.save()

            from django.contrib import messages

            messages.success(
                request, f"Bulk action '{action}' applied to {qs.count()} user(s)."
            )
            # Audit log for user actions (view, bulk action)
            AuditLog.objects.create(
                user=request.user,
                action="user_bulk_action",
                details=f"Bulk action '{action}' applied to users: {selected_ids}",
                timestamp=timezone.now(),
            )
            # Optional: send notification to superusers
            # Get all superusers to notify them about bulk actions
            superusers = User.objects.filter(is_superuser=True)
            for superuser in superusers:
                InternalNotification.objects.create(
                    user=superuser,
                    message=f"Bulk user action '{action}' performed by {request.user.username}.",
                )
            return redirect("accounts:user_dashboard")

    # CSV export
    if "export" in request.GET:
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="user_dashboard.csv"'
        import csv

        writer = csv.writer(response)
        writer.writerow(["Username", "Full Name", "Email", "Role", "Status"])
        for user in users:
            writer.writerow(
                [
                    user.username,
                    user.get_full_name(),
                    user.email,
                    getattr(user.get_profile, "role", ""),
                    "Active" if user.is_active else "Inactive",
                ]
            )
        return response

    # Pagination
    paginator = Paginator(users.order_by("username"), 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "users": page_obj,
        "search": search,
        "role": role,
        "is_active": is_active,
        "roles": CustomUserProfile.ROLE_CHOICES,
        "page_title": "User Management Dashboard",
    }
    return render(request, "accounts/user_dashboard.html", context)


def delete_user(request, user_id):
    """Delete a user account with proper validation and complete database removal."""
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to delete users.")
        return redirect("accounts:user_dashboard")

    try:
        user_to_delete = User.objects.get(id=user_id)

        # Prevent deletion of superusers except by themselves
        if user_to_delete.is_superuser and user_to_delete != request.user:
            messages.error(request, "Cannot delete another superuser.")
            return redirect("accounts:user_dashboard")

        # Prevent self-deletion
        if user_to_delete == request.user:
            messages.error(request, "Cannot delete your own account.")
            return redirect("accounts:user_dashboard")

        # Store user info for audit log before deletion
        username = user_to_delete.username
        email = user_to_delete.email
        user_id_stored = user_to_delete.id

        # Get related objects before deletion for audit log
        related_objects = {
            "profile": None,
            "roles": [],
            "sessions": [],
            "activities": [],
            "notifications": [],
        }

        try:
            related_objects["profile"] = user_to_delete.profile
        except:
            pass

        related_objects["roles"] = list(user_to_delete.roles.all())
        related_objects["sessions"] = list(
            user_to_delete.user_sessions.all()
            if hasattr(user_to_delete, "user_sessions")
            else []
        )
        related_objects["activities"] = list(
            user_to_delete.user_activities.all()
            if hasattr(user_to_delete, "user_activities")
            else []
        )
        related_objects["notifications"] = list(
            user_to_delete.notifications.all()
            if hasattr(user_to_delete, "notifications")
            else []
        )

        # Perform complete database deletion with cascade
        # This will delete the user and all related objects due to CASCADE relationships
        deletion_result = user_to_delete.delete()

        # Verify complete deletion
        if User.objects.filter(id=user_id_stored).exists():
            raise Exception("User still exists in database after deletion attempt")

        # Log the complete deletion with details
        AuditLog.objects.create(
            user=request.user,
            action="delete",
            details={
                "action": "complete_user_deletion",
                "deleted_user": {
                    "id": user_id_stored,
                    "username": username,
                    "email": email,
                },
                "deleted_objects": {
                    "profile": str(related_objects["profile"])
                    if related_objects["profile"]
                    else None,
                    "roles_count": len(related_objects["roles"]),
                    "sessions_count": len(related_objects["sessions"]),
                    "activities_count": len(related_objects["activities"]),
                    "notifications_count": len(related_objects["notifications"]),
                    "total_objects_deleted": deletion_result[1]
                    if deletion_result and len(deletion_result) > 1
                    else "unknown",
                },
                "performed_by": request.user.username,
                "timestamp": timezone.now().isoformat(),
            },
            timestamp=timezone.now(),
        )

        messages.success(
            request,
            f"User '{username}' and all associated data have been permanently removed from the database.",
        )

    except User.DoesNotExist:
        messages.error(request, "User not found.")
    except Exception as e:
        messages.error(request, f"Error deleting user: {str(e)}")
        # Log the error
        AuditLog.objects.create(
            user=request.user,
            action="delete",
            details={
                "action": "user_deletion_error",
                "error": str(e),
                "target_user_id": user_id,
                "performed_by": request.user.username,
            },
            timestamp=timezone.now(),
        )

    return redirect("accounts:user_dashboard")


# @user_passes_test(lambda u: u.is_superuser or u.is_staff)
# def user_dashboard(request):
#     """Admin user management dashboard: filter, search, bulk actions, CSV export."""
#     users = User.objects.all().select_related('profile')
#     # Filters
#     search = request.GET.get('search', '')
#     role = request.GET.get('role', '')
#     is_active = request.GET.get('is_active', '')
#     if search:
#         users = users.filter(
#             Q(username__icontains=search) |
#             Q(first_name__icontains=search) |
#             Q(last_name__icontains=search) |
#             Q(email__icontains=search)
#         )
#     if role:
#         users = users.filter(profile__role=role)
#     if is_active == 'true':
#         users = users.filter(is_active=True)
#     elif is_active == 'false':
#         users = users.filter(is_active=False)

#     # Bulk actions
#     if request.method == 'POST' and 'bulk_action' in request.POST:
#         action = request.POST.get('bulk_action')
#         selected_ids = request.POST.getlist('selected_users')
#         if selected_ids:
#             qs = CustomUser.objects.filter(id__in=selected_ids)
#             if action == 'activate':
#                 qs.update(is_active=True)
#             elif action == 'deactivate':
#                 qs.update(is_active=False)
#             # Role assignment (if provided)
#             new_role = request.POST.get('assign_role')
#             if action == 'assign_role' and new_role:
#                 for user in qs:
#                     user.get_profile.role = new_role
#                     user.get_profile.save()
#             from django.contrib import messages
#             messages.success(request, f"Bulk action '{action}' applied to {qs.count()} user(s).")
#             # Audit log for user actions (view, bulk action)
#             AuditLog.objects.create(
#                 user=request.user,
#                 action='user_bulk_action',
#                 details=f"Bulk action '{action}' applied to users: {selected_ids}",
#                 timestamp=timezone.now()
#             )
#             # Optional: send notification to superusers
#             InternalNotification.objects.create(
#                 user=None,  # System-wide
#                 message=f"Bulk user action '{action}' performed by {request.user.username}."
#             )
#             return redirect('accounts:user_dashboard')

#     # CSV export
#     if 'export' in request.GET:
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="user_dashboard.csv"'
#         import csv
#         writer = csv.writer(response)
#         writer.writerow(['Username', 'Full Name', 'Email', 'Role', 'Status'])
#         for user in users:
#             writer.writerow([
#                 user.username,
#                 user.get_full_name(),
#                 user.email,
#                 getattr(user.get_profile, 'role', ''),
#                 'Active' if user.is_active else 'Inactive',
#             ])
#         return response

#     # Pagination
#     paginator = Paginator(users.order_by('username'), 25)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)

#     # Get all roles for filter dropdown
#     from accounts.models import CustomUserProfile as Profile
#     roles = Profile._meta.get_field('role').choices if hasattr(Profile, '_meta') else []

#     # Role-based analytics
#     role_counts = User.objects.values('profile__role').annotate(count=Count('id'))
#     active_count = User.objects.filter(is_active=True).count()
#     inactive_count = User.objects.filter(is_active=False).count()

#     # Audit log for user actions (view, bulk action)
#     if request.method == 'GET' and request.user.is_authenticated:
#         AuditLog.objects.create(
#             user=request.user,
#             action='user_dashboard_view',
#             details="Viewed user dashboard.",
#             timestamp=timezone.now()
#         )

#     context = {
#         'page_obj': page_obj,
#         'search': search,
#         'role': role,
#         'is_active': is_active,
#         'roles': roles,
#         'page_title': 'User Management',
#         'active_nav': 'user_dashboard',
#         'role_counts': role_counts,
#         'active_count': active_count,
#         'inactive_count': inactive_count,
#     }
#     return render(request, 'accounts/user_dashboard.html', context)


# accounts/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator  # Ensure Paginator is imported
from django.utils import timezone
from .models import CustomUserProfile, Department, Role, AuditLog
from .forms import (
    CustomLoginForm,
    UserProfileForm,
    StaffCreationForm,
    DepartmentForm,
    UserRegistrationForm,
)
from django.contrib.auth import get_user_model
from django.urls import reverse


# Custom decorators for backward compatibility
def user_passes_test(test_func):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not test_func(request.user):
                from django.contrib.auth.decorators import PermissionDenied

                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.roles.filter(name="admin").exists()
    )


def is_admin_or_staff(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


User = get_user_model()


# Helper function (ensure it's defined or imported)
def is_admin_or_staff(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


@login_required
@permission_required("users.view")
def user_dashboard(request):
    # Check if user can manage users
    can_manage_users = check_user_management_access(request.user)
    can_edit_users = user_has_permission(request.user, "users.edit")
    can_delete_users = user_has_permission(request.user, "users.delete")

    users_query = User.objects.all().prefetch_related("roles", "profile")

    search_query = request.GET.get("search", "")
    role_filter = request.GET.get("role", "")
    is_active_filter = request.GET.get("is_active", "")

    if search_query:
        users_query = users_query.filter(
            Q(username__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone_number__icontains=search_query)
        )

    if role_filter:
        users_query = users_query.filter(roles__name=role_filter)

    if is_active_filter == "true":
        users_query = users_query.filter(is_active=True)
    elif is_active_filter == "false":
        users_query = users_query.filter(is_active=False)

    # Bulk actions
    if request.method == "POST" and "bulk_action" in request.POST and can_edit_users:
        action = request.POST.get("bulk_action")
        selected_ids = request.POST.getlist("selected_users")
        if selected_ids:
            qs = User.objects.filter(id__in=selected_ids)
            if action == "activate" and user_has_permission(request.user, "users.edit"):
                qs.update(is_active=True)
            elif action == "deactivate" and user_has_permission(
                request.user, "users.edit"
            ):
                qs.update(is_active=False)
            elif action == "delete" and user_has_permission(
                request.user, "users.delete"
            ):
                # Prevent deletion of superusers and self in bulk operations
                deletable_users = qs.exclude(
                    Q(is_superuser=True) & ~Q(id=request.user.id)
                ).exclude(id=request.user.id)

                deleted_count = deletable_users.count()
                deleted_usernames = list(
                    deletable_users.values_list("username", flat=True)
                )
                deleted_ids = list(deletable_users.values_list("id", flat=True))

                if deleted_count > 0:
                    # Perform complete database deletion with cascade
                    deletion_result = deletable_users.delete()

                    # Verify complete deletion
                    remaining_users = User.objects.filter(id__in=deleted_ids).count()
                    if remaining_users > 0:
                        raise Exception(
                            f"{remaining_users} users still exist in database after bulk deletion attempt"
                        )

                    messages.success(
                        request,
                        f"Successfully deleted {deleted_count} user(s) and all associated data from database.",
                    )

                    # Detailed audit log for bulk deletion
                    AuditLog.objects.create(
                        user=request.user,
                        action="delete",
                        target_user=None,
                        details={
                            "action": "bulk_user_deletion_complete",
                            "deleted_users_count": deleted_count,
                            "deleted_usernames": deleted_usernames,
                            "deleted_user_ids": deleted_ids,
                            "performed_by": request.user.username,
                            "total_objects_deleted": deletion_result[1]
                            if deletion_result and len(deletion_result) > 1
                            else "unknown",
                            "timestamp": timezone.now().isoformat(),
                        },
                        timestamp=timezone.now(),
                    )

                    # Notify superusers about bulk deletion
                    superusers = User.objects.filter(is_superuser=True)
                    for superuser_obj in superusers:
                        InternalNotification.objects.create(
                            user=superuser_obj,
                            message=f"Bulk user deletion performed by {request.user.username}. {deleted_count} users and all their data were permanently removed from database.",
                        )

                    return redirect("accounts:user_dashboard")
                else:
                    messages.warning(
                        request,
                        "No users available for deletion (superusers and yourself cannot be deleted).",
                    )
                    return redirect("accounts:user_dashboard")
            elif action == "assign_role":
                new_role_name = request.POST.get("assign_role")
                if new_role_name:
                    try:
                        role_obj = Role.objects.get(name=new_role_name)
                        for user_obj in qs:
                            user_obj.roles.set(
                                [role_obj]
                            )  # Use set() to assign a single role, clear others
                            # Or .add() if multiple roles are allowed and you want to add this one
                    except Role.DoesNotExist:
                        messages.error(
                            request, f"Specified role '{new_role_name}' doesn't exist"
                        )

            if action != "delete":  # Don't overwrite the delete message
                messages.success(
                    request, f"Bulk action '{action}' applied to {qs.count()} user(s)."
                )
                AuditLog.objects.create(
                    user=request.user,
                    action="user_bulk_action",
                    target_user=None,
                    details={
                        "action": action,
                        "applied_to_user_ids": selected_ids,
                        "count": qs.count(),
                    },
                    ip_address=request.META.get("REMOTE_ADDR"),
                    timestamp=timezone.now(),
                )
            return redirect(
                "accounts:user_dashboard"
            )  # Ensure this URL name is correct

    # CSV export
    if "export" in request.GET:
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="user_dashboard.csv"'
        import csv

        writer = csv.writer(response)
        writer.writerow(["Username", "Full Name", "Email", "Phone", "Roles", "Status"])
        # Use the filtered users_query for export
        for user_obj in users_query.order_by("username"):
            writer.writerow(
                [
                    user_obj.username,
                    user_obj.get_full_name(),
                    user_obj.email,
                    user_obj.phone_number,
                    ", ".join([role.name for role in user_obj.roles.all()]),
                    "Active" if user_obj.is_active else "Inactive",
                ]
            )
        return response

    # Pagination
    paginator = Paginator(
        users_query.order_by("username"), 25
    )  # Apply ordering before pagination
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Prepare elided page range for pagination template
    # Adjust on_each_side and on_ends as per your preference
    elided_page_range = page_obj.paginator.get_elided_page_range(
        number=page_obj.number,
        on_each_side=2,  # e.g., 2 pages on each side of the current page
        on_ends=1,  # e.g., 1 page at the beginning and end
    )

    all_roles = Role.objects.all().order_by("name")
    role_counts_data = Role.objects.annotate(count=Count("customuser_role")).values(
        "name", "count"
    )
    active_count = User.objects.filter(
        is_active=True
    ).count()  # Consider filtering this by current query too if makes sense
    inactive_count = User.objects.filter(is_active=False).count()  # Same as above

    if request.method == "GET":  # Log only on initial load/filter, not POST actions
        # Convert is_active_filter to a boolean or None for better logging
        logged_is_active_filter = None
        if is_active_filter == "true":
            logged_is_active_filter = True
        elif is_active_filter == "false":
            logged_is_active_filter = False

        AuditLog.objects.create(
            user=request.user,
            action="user_dashboard_view",
            details={
                "filters": {
                    "search": search_query,
                    "role": role_filter,
                    "is_active": logged_is_active_filter,
                }
            },
            ip_address=request.META.get("REMOTE_ADDR"),
            timestamp=timezone.now(),
        )

    context = {
        "page_obj": page_obj,
        "elided_page_range": elided_page_range,  # Add this to context
        "search": search_query,
        "role": role_filter,  # This context variable name 'role' is used in template for selected role in filter
        "is_active": is_active_filter,
        "roles": all_roles,  # This context variable 'roles' is used for iterating Role objects in dropdowns
        "page_title": "User Management",
        "active_nav": "user_dashboard",
        "role_counts": list(role_counts_data),
        "active_count": active_count,
        "inactive_count": inactive_count,
    }
    return render(request, "accounts/user_dashboard.html", context)


# ============================================================================
# PRIVILEGE MANAGEMENT VIEWS
# ============================================================================


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def role_management(request):
    """View for managing roles and permissions"""
    roles = (
        Role.objects.all().prefetch_related("permissions", "children").order_by("name")
    )

    # Detect circular references
    circular_refs = []
    for role in roles:
        if role.check_circular_reference(role.parent):
            circular_refs.append(
                f"Role '{role.name}' has a circular reference with its parent chain"
            )

    # Handle bulk actions
    if request.method == "POST":
        action = request.POST.get("bulk_action")
        selected_role_ids = request.POST.getlist("selected_roles")

        if action and selected_role_ids:
            selected_roles = Role.objects.filter(id__in=selected_role_ids)
            count = selected_roles.count()

            if action == "delete":
                # Check if any roles have users or children
                roles_with_users = []
                roles_with_children = []
                for role in selected_roles:
                    if role.customuser_roles.exists():
                        roles_with_users.append(role.name)
                    if role.children.exists():
                        roles_with_children.append(role.name)

                if roles_with_users or roles_with_children:
                    error_msg = (
                        "Cannot delete roles that have assigned users or child roles: "
                    )
                    if roles_with_users:
                        error_msg += f"Users assigned: {', '.join(roles_with_users)}. "
                    if roles_with_children:
                        error_msg += (
                            f"Have child roles: {', '.join(roles_with_children)}"
                        )
                    messages.error(request, error_msg)
                else:
                    # Log before deletion
                    AuditLog.objects.create(
                        user=request.user,
                        action="bulk_delete",
                        details={
                            "role_names": list(
                                selected_roles.values_list("name", flat=True)
                            ),
                            "count": count,
                        },
                        ip_address=request.META.get("REMOTE_ADDR"),
                        timestamp=timezone.now(),
                    )
                    selected_roles.delete()
                    messages.success(request, f"Successfully deleted {count} role(s).")

            elif action == "assign_parent":
                parent_id = request.POST.get("parent_role")
                if parent_id:
                    try:
                        parent_role = Role.objects.get(id=parent_id)
                        # Check for circular references
                        for role in selected_roles:
                            if role.check_circular_reference(parent_role):
                                messages.error(
                                    request,
                                    f'Cannot assign parent: circular reference would be created for role "{role.name}".',
                                )
                                return redirect("accounts:role_management")
                            if role.id == parent_role.id:
                                messages.error(
                                    request, f"Cannot assign a role as its own parent."
                                )
                                return redirect("accounts:role_management")

                        # Check if parent is in selected roles
                        if parent_role.id in selected_role_ids:
                            messages.error(
                                request,
                                "Cannot assign a selected role as parent of itself.",
                            )
                        else:
                            updated = selected_roles.update(parent=parent_role)
                            AuditLog.objects.create(
                                user=request.user,
                                action="bulk_update",
                                details={
                                    "role_names": list(
                                        selected_roles.values_list("name", flat=True)
                                    ),
                                    "action": "assign_parent",
                                    "parent": parent_role.name,
                                    "count": updated,
                                },
                                ip_address=request.META.get("REMOTE_ADDR"),
                                timestamp=timezone.now(),
                            )
                            messages.success(
                                request,
                                f'Assigned parent "{parent_role.name}" to {updated} role(s).',
                            )
                    except Role.DoesNotExist:
                        messages.error(request, "Selected parent role does not exist.")

            elif action == "copy_permissions_from":
                source_id = request.POST.get("source_role")
                if source_id:
                    try:
                        source_role = Role.objects.get(id=source_id)
                        source_permissions = source_role.permissions.all()
                        permission_count = source_permissions.count()

                        for role in selected_roles:
                            role.permissions.set(source_permissions)
                            AuditLog.objects.create(
                                user=request.user,
                                action="bulk_update",
                                details={
                                    "role_name": role.name,
                                    "action": "copy_permissions",
                                    "source_role": source_role.name,
                                    "permission_count": permission_count,
                                },
                                ip_address=request.META.get("REMOTE_ADDR"),
                                timestamp=timezone.now(),
                            )
                        messages.success(
                            request,
                            f'Copied {permission_count} permissions from "{source_role.name}" to {count} role(s).',
                        )
                    except Role.DoesNotExist:
                        messages.error(request, "Selected source role does not exist.")

            return redirect("accounts:role_management")

    context = {
        "roles": roles,
        "circular_refs": circular_refs,
        "page_title": "Role Management",
        "active_nav": "role_management",
    }
    return render(request, "accounts/role_management.html", context)


@login_required
@permission_required("roles.create")
def create_role(request):
    """View for creating a new role"""
    if request.method == "POST":
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save()

            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action="create",
                details={
                    "role_name": role.name,
                    "permissions": list(
                        role.permissions.values_list("name", flat=True)
                    ),
                },
                ip_address=request.META.get("REMOTE_ADDR"),
                timestamp=timezone.now(),
            )

            messages.success(request, f'Role "{role.name}" created successfully.')
            return redirect("accounts:role_management")
    else:
        form = RoleForm()

    context = {
        "form": form,
        "is_edit": False,
        "role": None,
        "page_title": "Create Role",
        "active_nav": "role_management",
    }
    return render(request, "accounts/role_form.html", context)


@login_required
@permission_required("roles.edit")
def edit_role(request, role_id):
    """View for editing an existing role"""
    role = get_object_or_404(Role, id=role_id)
    logger = logging.getLogger(__name__)

    if request.method == "POST":
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            old_permissions = list(role.permissions.values_list("name", flat=True))
            logger.info(f"[Role Edit] Updating role '{role.name}' (ID: {role_id})")
            logger.info(f"[Role Edit] Old permissions: {old_permissions}")
            logger.info(f"[Role Edit] Form cleaned_data permissions: {list(form.cleaned_data.get('permissions', []).values_list('name', flat=True))}")

            role = form.save()
            new_permissions = list(role.permissions.values_list("name", flat=True))
            logger.info(f"[Role Edit] New permissions after save: {new_permissions}")

            # Clear permission cache for all users with this role
            User = get_user_model()
            users_with_role = User.objects.filter(roles=role)
            cache_cleared_count = 0
            for user in users_with_role:
                user.clear_permission_cache()
                cache_cleared_count += 1
            logger.info(f"[Role Edit] Cleared permission cache for {cache_cleared_count} users with role '{role.name}'")

            # Clear UI permission cache
            try:
                from django.core.cache import cache
                # Get all cache keys matching pattern
                cache_keys_to_delete = []
                try:
                    # Try to get cache keys if cache backend supports it
                    if hasattr(cache, 'keys'):
                        cache_keys_to_delete = [k for k in cache.keys('*') if k.startswith('ui_perm_')]
                        if cache_keys_to_delete:
                            cache.delete_many(cache_keys_to_delete)
                            logger.info(f"[Role Edit] Cleared {len(cache_keys_to_delete)} UI permission cache entries")
                except Exception as e:
                    logger.warning(f"[Role Edit] Could not clear UI cache: {e}")
            except Exception as e:
                logger.warning(f"[Role Edit] Error accessing cache: {e}")

            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action="update",
                details={
                    "role_name": role.name,
                    "old_permissions": old_permissions,
                    "new_permissions": new_permissions,
                },
                ip_address=request.META.get("REMOTE_ADDR"),
                timestamp=timezone.now(),
            )

            messages.success(request, f'Role "{role.name}" updated successfully. Permission cache cleared for {cache_cleared_count} users.')
            return redirect("accounts:role_management")
    else:
        form = RoleForm(instance=role)

    context = {
        "form": form,
        "role": role,
        "is_edit": True,
        "page_title": f"Edit Role: {role.name}",
        "active_nav": "role_management",
    }
    return render(request, "accounts/role_form.html", context)


@login_required
@permission_required("roles.edit")
def clone_role(request, role_id):
    """View for cloning an existing role"""
    original_role = get_object_or_404(Role, id=role_id)

    if request.method == "POST":
        form = RoleForm(request.POST)
        if form.is_valid():
            new_role = form.save()

            # Log the cloning action
            AuditLog.objects.create(
                user=request.user,
                action="create",
                details={
                    "role_name": new_role.name,
                    "cloned_from": original_role.name,
                    "permissions": list(
                        new_role.permissions.values_list("name", flat=True)
                    ),
                },
                ip_address=request.META.get("REMOTE_ADDR"),
                timestamp=timezone.now(),
            )

            messages.success(
                request,
                f'Role "{new_role.name}" created successfully (cloned from "{original_role.name}").',
            )
            return redirect("accounts:role_management")
    else:
        # Pre-fill form with original role data
        initial_data = {
            "name": f"{original_role.name} (Copy)",
            "description": original_role.description,
            "parent": original_role.parent,
            "permissions": original_role.permissions.all(),
        }
        form = RoleForm(initial=initial_data)

    context = {
        "form": form,
        "original_role": original_role,
        "is_edit": False,
        "page_title": f"Clone Role: {original_role.name}",
        "active_nav": "role_management",
    }
    return render(request, "accounts/role_form.html", context)


@login_required
@permission_required("roles.view")
def compare_roles(request):
    """View for comparing permissions between two roles"""
    roles = Role.objects.all().order_by("name")

    role_a = None
    role_b = None
    comparison_data = None

    if request.method == "GET":
        role_a_id = request.GET.get("role_a")
        role_b_id = request.GET.get("role_b")

        if role_a_id and role_b_id:
            try:
                role_a = Role.objects.get(id=role_a_id)
                role_b = Role.objects.get(id=role_b_id)

                # Calculate permission differences
                perms_a = role_a.get_all_permissions()
                perms_b = role_b.get_all_permissions()

                all_perms = perms_a | perms_b

                comparison_data = {
                    "role_a": role_a,
                    "role_b": role_b,
                    "only_in_a": sorted(
                        [p for p in perms_a if p not in perms_b],
                        key=lambda x: x.content_type.app_label,
                    ),
                    "only_in_b": sorted(
                        [p for p in perms_b if p not in perms_a],
                        key=lambda x: x.content_type.app_label,
                    ),
                    "in_both": sorted(
                        [p for p in perms_a if p in perms_b],
                        key=lambda x: x.content_type.app_label,
                    ),
                    "total_a": len(perms_a),
                    "total_b": len(perms_b),
                    "total_both": len(perms_a & perms_b),
                }
            except Role.DoesNotExist:
                messages.error(request, "One or both selected roles do not exist.")

    context = {
        "roles": roles,
        "role_a": role_a,
        "role_b": role_b,
        "comparison_data": comparison_data,
        "page_title": "Compare Roles",
        "active_nav": "role_management",
    }
    return render(request, "accounts/compare_roles.html", context)


@login_required
@permission_required("roles.edit")
def delete_role(request, role_id):
    """View for deleting a role"""
    role = get_object_or_404(Role, id=role_id)

    if request.method == "POST":
        role_name = role.name
        users_with_role = role.customuser_roles.count()

        if users_with_role > 0:
            messages.error(
                request,
                f'Cannot delete role "{role_name}" because it is assigned to {users_with_role} user(s).',
            )
        else:
            # Log the action before deletion
            AuditLog.objects.create(
                user=request.user,
                action="delete",
                details={
                    "role_name": role_name,
                    "permissions": list(
                        role.permissions.values_list("name", flat=True)
                    ),
                },
                ip_address=request.META.get("REMOTE_ADDR"),
                timestamp=timezone.now(),
            )

            role.delete()
            messages.success(request, f'Role "{role_name}" deleted successfully.')

        return redirect("accounts:role_management")

    context = {
        "role": role,
        "users_with_role": role.customuser_roles.count(),
        "page_title": f"Delete Role: {role.name}",
        "active_nav": "role_management",
    }
    return render(request, "accounts/delete_role.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def user_privileges(request, user_id):
    """View for managing user privileges (role assignments)"""
    target_user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = UserRoleAssignmentForm(request.POST, instance=target_user)
        if form.is_valid():
            old_roles = list(target_user.roles.values_list("name", flat=True))
            form.save()
            new_roles = list(target_user.roles.values_list("name", flat=True))

            # Log the action
            AuditLog.objects.create(
                user=request.user,
                target_user=target_user,
                action="privilege_change",
                details={"old_roles": old_roles, "new_roles": new_roles},
                ip_address=request.META.get("REMOTE_ADDR"),
                timestamp=timezone.now(),
            )

            messages.success(
                request, f'Privileges updated for user "{target_user.get_full_name()}".'
            )
            return redirect("accounts:user_dashboard")
    else:
        form = UserRoleAssignmentForm(instance=target_user)

    context = {
        "form": form,
        "target_user": target_user,
        "page_title": f"Manage Privileges: {target_user.get_full_name()}",
        "active_nav": "user_dashboard",
    }
    return render(request, "accounts/user_privileges.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def bulk_user_actions(request):
    """View for performing bulk actions on users"""
    if request.method == "POST":
        # Check if this is an AJAX/JSON request from the User Matrix
        changes_data = request.POST.get("changes")
        if changes_data:
            # Handle User Matrix AJAX submission
            try:
                import json

                user_changes = json.loads(changes_data)
                updated_count = 0

                for user_id, changes in user_changes.items():
                    try:
                        user = User.objects.get(id=user_id)

                        # Add roles
                        if changes.get("add"):
                            roles_to_add = Role.objects.filter(id__in=changes["add"])
                            user.roles.add(*roles_to_add)

                        # Remove roles
                        if changes.get("remove"):
                            roles_to_remove = Role.objects.filter(
                                id__in=changes["remove"]
                            )
                            user.roles.remove(*roles_to_remove)

                        updated_count += 1
                    except User.DoesNotExist:
                        continue

                # Log the bulk action
                AuditLog.objects.create(
                    user=request.user,
                    action="user_bulk_action",
                    details={
                        "action": "assign_role_matrix",
                        "affected_users": updated_count,
                        "changes": user_changes,
                    },
                    ip_address=request.META.get("REMOTE_ADDR"),
                    timestamp=timezone.now(),
                )

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": True,
                            "updated_count": updated_count,
                            "message": f"Successfully updated {updated_count} user(s)",
                        }
                    )

                messages.success(
                    request, f"Successfully updated {updated_count} user(s)."
                )
                return redirect("accounts:rbac_user_matrix")

            except json.JSONDecodeError:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {"success": False, "error": "Invalid JSON data"}
                    )
                messages.error(request, "Invalid data format.")
                return redirect("accounts:rbac_user_matrix")

        # Original bulk action handling
        form = BulkUserActionForm(request.POST)
        selected_users = request.POST.getlist("selected_users")

        if form.is_valid() and selected_users:
            action = form.cleaned_data["action"]
            role = form.cleaned_data.get("role")

            users = User.objects.filter(id__in=selected_users)
            affected_count = users.count()

            if action == "activate":
                users.update(is_active=True)
                messages.success(request, f"Activated {affected_count} user(s).")

            elif action == "deactivate":
                users.update(is_active=False)
                messages.success(request, f"Deactivated {affected_count} user(s).")

            elif action == "assign_role" and role:
                for user in users:
                    user.roles.add(role)
                messages.success(
                    request, f'Assigned role "{role.name}" to {affected_count} user(s).'
                )

            elif action == "remove_role" and role:
                for user in users:
                    user.roles.remove(role)
                messages.success(
                    request,
                    f'Removed role "{role.name}" from {affected_count} user(s).',
                )

            elif action == "delete":
                # Don't allow deletion of superusers or current user
                safe_users = users.exclude(is_superuser=True).exclude(
                    id=request.user.id
                )
                deleted_count = safe_users.count()
                safe_users.delete()
                messages.success(request, f"Deleted {deleted_count} user(s).")

            # Log the bulk action
            AuditLog.objects.create(
                user=request.user,
                action="user_bulk_action",
                details={
                    "action": action,
                    "affected_users": affected_count,
                    "role": role.name if role else None,
                },
                ip_address=request.META.get("REMOTE_ADDR"),
                timestamp=timezone.now(),
            )

        else:
            messages.error(
                request, "Please select users and provide valid action details."
            )

    return redirect("accounts:user_dashboard")


@login_required
@permission_required("roles.view")
def permission_management(request):
    """View for managing permissions"""
    from django.contrib.auth.models import Permission

    form = PermissionFilterForm(request.GET)
    permissions = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label", "content_type__model", "codename"
    )

    if form.is_valid():
        content_type = form.cleaned_data.get("content_type")
        search = form.cleaned_data.get("search")

        if content_type:
            permissions = permissions.filter(content_type=content_type)

        if search:
            permissions = permissions.filter(
                Q(name__icontains=search)
                | Q(codename__icontains=search)
                | Q(content_type__model__icontains=search)
            )

    # Group permissions by content type
    grouped_permissions = {}
    for permission in permissions:
        app_model = (
            f"{permission.content_type.app_label}.{permission.content_type.model}"
        )
        if app_model not in grouped_permissions:
            grouped_permissions[app_model] = []
        grouped_permissions[app_model].append(permission)

    context = {
        "form": form,
        "grouped_permissions": grouped_permissions,
        "page_title": "Permission Management",
        "active_nav": "permission_management",
    }
    return render(request, "accounts/permission_management.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def audit_logs(request):
    """View for displaying audit logs"""
    logs = AuditLog.objects.select_related("user", "target_user").order_by("-timestamp")

    # Filter by action type
    action_filter = request.GET.get("action")
    if action_filter:
        logs = logs.filter(action=action_filter)

    # Filter by user
    user_filter = request.GET.get("user")
    if user_filter:
        logs = logs.filter(user_id=user_filter)

    # Filter by date range
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)

    # Pagination
    paginator = Paginator(logs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Debugging: Log details of each log entry (using logger instead of print to avoid Windows OSError)
    for log_entry in page_obj:
        logger.debug(f"Audit Log ID: {log_entry.id}, Details: {log_entry.details}")

    context = {
        "page_obj": page_obj,
        "action_choices": AuditLog.ACTION_CHOICES,
        "users": User.objects.filter(is_active=True).order_by("username"),
        "page_title": "Audit Logs",
        "active_nav": "audit_logs",
    }
    return render(request, "accounts/audit_logs.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def role_demo(request):
    """Demo view showing the role system in action"""
    # Get all roles with user counts
    roles = Role.objects.annotate(user_count=Count("customuser_role")).prefetch_related(
        "permissions"
    )

    # Get users by role
    users_by_role = {}
    for role in roles:
        users_by_role[role.name] = (
            User.objects.filter(roles=role).select_related("profile").all()
        )

    # Get role statistics
    total_roles = roles.count()
    total_users = User.objects.count()
    users_with_roles = User.objects.filter(roles__isnull=False).distinct().count()
    users_without_roles = total_users - users_with_roles

    # Get permission statistics
    total_permissions = Permission.objects.count()
    permissions_in_use = (
        Permission.objects.filter(role__isnull=False).distinct().count()
    )

    context = {
        "roles": roles,
        "users_by_role": users_by_role,
        "total_roles": total_roles,
        "total_users": total_users,
        "users_with_roles": users_with_roles,
        "users_without_roles": users_without_roles,
        "total_permissions": total_permissions,
        "permissions_in_use": permissions_in_use,
        "page_title": "HMS Role System Demo",
        "active_nav": "role_demo",
    }
    return render(request, "accounts/role_demo.html", context)


# =============================================================================
# SUPERUSER-ONLY VIEWS
# =============================================================================


def superuser_required(view_func):
    """Decorator to ensure only superusers can access these views"""

    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "Access denied. Superuser privileges required.")
            return redirect("accounts:login")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


@superuser_required
def superuser_user_profiles(request):
    """View for superusers to edit any user profile"""
    users = User.objects.select_related("profile").order_by("username")

    # Search functionality
    query = request.GET.get("q", "")
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(phone_number__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(profile__phone_number__icontains=query)
        )

    # Pagination
    paginator = Paginator(users, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "accounts/superuser/user_profiles.html",
        {
            "page_obj": page_obj,
            "query": query,
            "page_title": "User Profile Management",
            "active_nav": "user_profiles",
        },
    )


@superuser_required
def toggle_user_active_status(request, user_id):
    """Toggle user active/inactive status"""
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("accounts:superuser_user_profiles")

    try:
        user = User.objects.get(id=user_id)

        # Prevent superusers from deactivating themselves
        if user.id == request.user.id:
            messages.error(request, "You cannot deactivate your own account.")
            return redirect("accounts:superuser_user_profiles")

        # Toggle the active status
        was_active = user.is_active
        user.is_active = not user.is_active
        user.save()

        # Create audit log
        action_type = "update" if user.is_active else "deactivate"
        action_description = "activated" if user.is_active else "deactivated"
        AuditLog.objects.create(
            user=request.user,
            target_user=user,
            action=action_type,
            details={
                "action": f"User {action_description}",
                "username": user.username,
                "previous_status": "active" if was_active else "inactive",
                "new_status": "active" if user.is_active else "inactive",
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
            },
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        messages.success(
            request, f"User {user.username} has been {action_description} successfully."
        )

    except User.DoesNotExist:
        messages.error(request, "User not found.")
    except Exception as e:
        messages.error(request, f"Error updating user status: {str(e)}")

    # Preserve search query in redirect
    query = request.GET.get("q", "")
    page = request.GET.get("page", "")
    redirect_url = reverse("accounts:superuser_user_profiles")
    params = []
    if query:
        params.append(f"q={query}")
    if page:
        params.append(f"page={page}")
    if params:
        redirect_url += "?" + "&".join(params)

    return redirect(redirect_url)


@superuser_required
def superuser_dashboard(request):
    """Main superuser dashboard with system overview"""
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta

    # Get system statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    staff_users = User.objects.filter(is_staff=True).count()
    superusers = User.objects.filter(is_superuser=True).count()

    # Recent activity
    recent_users = User.objects.order_by("-date_joined")[:5]
    recent_logs = AuditLog.objects.select_related("user").order_by("-timestamp")[:10]

    # User status breakdown
    user_stats = {
        "total": total_users,
        "active": active_users,
        "inactive": total_users - active_users,
        "staff": staff_users,
        "superusers": superusers,
        "regular": total_users - staff_users,
    }

    # Login activity (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_logins = AuditLog.objects.filter(
        action__icontains="login", timestamp__gte=seven_days_ago
    ).count()

    # Failed login attempts (last 7 days)
    failed_logins = AuditLog.objects.filter(
        action__icontains="failed login", timestamp__gte=seven_days_ago
    ).count()

    context = {
        "user_stats": user_stats,
        "recent_users": recent_users,
        "recent_logs": recent_logs,
        "recent_logins": recent_logins,
        "failed_logins": failed_logins,
        "page_title": "Superuser Dashboard",
        "active_nav": "dashboard",
    }
    return render(request, "accounts/superuser/dashboard.html", context)


@superuser_required
def superuser_edit_user_profile(request, user_id):
    """Edit any user's profile as superuser"""
    user = get_object_or_404(User, id=user_id)
    profile = getattr(user, "profile", None)

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=user, request_user=request.user)
        user_form = StaffCreationForm(request.POST, instance=user)

        if form.is_valid() and user_form.is_valid():
            # Save user basic info
            user_form.save()

            # Save or update profile
            if profile:
                form.save()
            else:
                profile = form.save(commit=False)
                profile.user = user
                profile.save()

            messages.success(
                request, f"Profile for {user.username} updated successfully."
            )
            return redirect("accounts:superuser_user_profiles")
    else:
        form = UserProfileForm(instance=user, request_user=request.user)
        user_form = StaffCreationForm(instance=user)

    return render(
        request,
        "accounts/superuser/edit_user_profile.html",
        {
            "form": form,
            "user_form": user_form,
            "target_user": user,
            "page_title": f"Edit Profile: {user.username}",
            "active_nav": "user_profiles",
        },
    )


@superuser_required
def superuser_password_reset(request):
    """View to reset any user's password"""
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if user_id and new_password:
            user = get_object_or_404(User, id=user_id)

            if new_password == confirm_password:
                user.set_password(new_password)
                user.save()

                # Log the password reset
                AuditLog.objects.create(
                    user=request.user,
                    action=f"Password reset for user {user.username}",
                    details=f"Superuser {request.user.username} reset password for {user.username}",
                    timestamp=timezone.now(),
                )

                messages.success(
                    request,
                    f"Password for {user.username} has been reset successfully.",
                )
            else:
                messages.error(request, "Passwords do not match.")
        else:
            messages.error(request, "Please provide user ID and new password.")

    users = User.objects.order_by("username")
    return render(
        request,
        "accounts/superuser/password_reset.html",
        {
            "users": users,
            "page_title": "Reset User Passwords",
            "active_nav": "user_password_reset",
        },
    )


@superuser_required
def superuser_reset_user_password(request, user_id):
    """Direct password reset for a specific user"""
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password and new_password == confirm_password:
            user.set_password(new_password)
            user.save()

            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action=f"Password reset for {user.username}",
                details=f"Superuser {request.user.username} reset password for {user.username}",
                timestamp=timezone.now(),
            )

            messages.success(request, f"Password for {user.username} has been reset.")
            return redirect("accounts:superuser_password_reset")
        else:
            messages.error(request, "Passwords do not match.")

    return render(
        request,
        "accounts/superuser/reset_user_password.html",
        {
            "target_user": user,
            "page_title": f"Reset Password: {user.username}",
            "active_nav": "user_password_reset",
        },
    )


@superuser_required
def superuser_bulk_operations(request):
    """Bulk operations on users"""
    if request.method == "POST":
        operation = request.POST.get("operation")
        user_ids = request.POST.getlist("user_ids")

        if operation and user_ids:
            users = User.objects.filter(id__in=user_ids)

            if operation == "activate":
                users.update(is_active=True)
                messages.success(request, f"Activated {len(users)} users.")
            elif operation == "deactivate":
                users.update(is_active=False)
                messages.success(request, f"Deactivated {len(users)} users.")
            elif operation == "delete":
                # Be careful with deletion
                count = users.count()
                users.delete()
                messages.success(request, f"Deleted {count} users.")
            elif operation == "assign_role":
                role_id = request.POST.get("role_id")
                if role_id:
                    role = Role.objects.get(id=role_id)
                    for user in users:
                        profile = getattr(user, "profile", None)
                        if profile:
                            profile.role = role
                            profile.save()
                    messages.success(request, f"Assigned role to {len(users)} users.")

    users = User.objects.select_related("profile").order_by("username")
    roles = Role.objects.all()

    return render(
        request,
        "accounts/superuser/bulk_operations_fixed.html",
        {
            "users": users,
            "roles": roles,
            "page_title": "Bulk User Operations",
            "active_nav": "user_bulk_operations",
        },
    )


@login_required
@permission_required("users.view")
def superuser_user_permissions(request):
    """Manage user permissions - accessible to users with users.view permission"""
    users = User.objects.select_related("profile").order_by("username")
    permissions = Permission.objects.select_related("content_type").order_by(
        "content_type__model", "name"
    )

    return render(
        request,
        "accounts/superuser/user_permissions.html",
        {
            "users": users,
            "permissions": permissions,
            "page_title": "Manage User Permissions",
            "active_nav": "user_permissions",
        },
    )


@login_required
@permission_required("users.edit")
def superuser_manage_user_permissions(request, user_id):
    """Manage permissions for a specific user - accessible to users with users.edit permission"""
    from core.permissions import APP_PERMISSIONS
    from accounts.models import Role
    from accounts.permissions import ROLE_PERMISSIONS

    user = get_object_or_404(User, id=user_id)
    user_permissions = user.user_permissions.all()

    # Get all available roles
    all_roles = Role.objects.all().order_by("name")

    # Get user's current roles
    user_roles = user.roles.all()
    user_role_ids = list(user_roles.values_list("id", flat=True))

    # Get all permissions, prioritizing custom HMS permissions
    all_permissions = Permission.objects.select_related("content_type").all()

    # Separate custom HMS permissions from Django model permissions
    custom_permission_codenames = set()
    for category_perms in APP_PERMISSIONS.values():
        custom_permission_codenames.update(category_perms.keys())

    custom_permissions = []
    model_permissions = []

    for perm in all_permissions:
        if perm.codename in custom_permission_codenames:
            custom_permissions.append(perm)
        else:
            model_permissions.append(perm)

    # Sort custom permissions by category (using APP_PERMISSIONS order)
    custom_permissions.sort(key=lambda p: p.name)
    model_permissions.sort(key=lambda p: (p.content_type.model, p.name))

    # Combine: custom permissions first, then model permissions
    ordered_permissions = custom_permissions + model_permissions

    if request.method == "POST":
        # Handle role assignment
        role_ids = request.POST.getlist("roles")
        user.roles.set(role_ids)

        # Handle permission assignment
        permission_ids = request.POST.getlist("permissions")
        user.user_permissions.set(permission_ids)

        # Update legacy profile role if a single role is selected
        if len(role_ids) == 1:
            selected_role = Role.objects.filter(id=role_ids[0]).first()
            if selected_role and hasattr(user, "profile") and user.profile:
                user.profile.role = selected_role.name
                user.profile.save()

        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action=f"Updated roles and permissions for {user.username}",
            details=f"Superuser {request.user.username} updated roles ({len(role_ids)}) and permissions ({len(permission_ids)}) for {user.username}",
            timestamp=timezone.now(),
        )

        messages.success(
            request, f"Roles and permissions for {user.username} updated successfully."
        )
        return redirect("accounts:superuser_user_permissions")

    return render(
        request,
        "accounts/superuser/manage_user_permissions.html",
        {
            "target_user": user,
            "user_permissions": user_permissions,
            "all_permissions": ordered_permissions,
            "custom_permissions": custom_permissions,
            "model_permissions": model_permissions,
            "app_permissions": APP_PERMISSIONS,
            "all_roles": all_roles,
            "user_roles": user_roles,
            "user_role_ids": user_role_ids,
            "role_permissions_json": json.dumps(ROLE_PERMISSIONS),
            "page_title": f"Manage Permissions: {user.username}",
            "active_nav": "user_permissions",
        },
    )


@superuser_required
def superuser_system_config(request):
    """System configuration panel"""
    from django.conf import settings

    # Get basic system info
    system_info = {
        "debug_mode": settings.DEBUG,
        "database_engine": settings.DATABASES["default"]["ENGINE"],
        "installed_apps": settings.INSTALLED_APPS,
        "middleware": settings.MIDDLEWARE,
        "static_url": settings.STATIC_URL,
        "media_url": settings.MEDIA_URL,
    }

    return render(
        request,
        "accounts/superuser/system_config.html",
        {
            "system_info": system_info,
            "page_title": "System Configuration",
            "active_nav": "system_config",
        },
    )


@superuser_required
def superuser_database_management(request):
    """Database management operations"""
    from django.db import connection

    # Get table information - SQLite compatible query
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        # Get table counts and other info
        table_info = []
        total_records = 0
        largest_table_count = 0
        non_empty_tables = 0
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            table_info.append({"name": table, "row_count": count})
            total_records += count
            if count > largest_table_count:
                largest_table_count = count
            if count > 0:
                non_empty_tables += 1

    return render(
        request,
        "accounts/superuser/database_management.html",
        {
            "tables": table_info,
            "total_records": total_records,
            "largest_table_count": largest_table_count,
            "non_empty_tables": non_empty_tables,
            "page_title": "Database Management",
            "active_nav": "database_management",
        },
    )


@superuser_required
def view_table_details(request, table_name):
    """AJAX endpoint to view table structure and sample data"""
    from django.db import connection
    import json

    try:
        with connection.cursor() as cursor:
            # Get table structure
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]

            # Get sample data (first 10 rows)
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 10")
            sample_data = cursor.fetchall()

            # Format column information
            column_info = []
            for col in columns:
                column_info.append(
                    {
                        "cid": col[0],
                        "name": col[1],
                        "type": col[2],
                        "notnull": col[3],
                        "default": col[4],
                        "pk": col[5],
                    }
                )

            # Format sample data
            sample_rows = []
            for row in sample_data:
                sample_rows.append(list(row))

            response_data = {
                "success": True,
                "table_name": table_name,
                "row_count": row_count,
                "columns": column_info,
                "sample_data": sample_rows,
            }

            return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@superuser_required
def export_table(request, table_name):
    """Export table data to CSV"""
    import csv
    from django.db import connection

    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("accounts:superuser_database_management")

    try:
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{table_name}_export.csv"'
        )

        with connection.cursor() as cursor:
            # Get column names
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]

            # Get all data
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()

            # Write to CSV
            writer = csv.writer(response)
            writer.writerow(columns)  # Header
            writer.writerows(rows)  # Data

        messages.success(request, f'Table "{table_name}" exported successfully.')
        return response

    except Exception as e:
        messages.error(request, f"Error exporting table: {str(e)}")
        return redirect("accounts:superuser_database_management")


@superuser_required
def clear_table(request, table_name):
    """Clear all records from a table"""
    from django.db import connection

    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("accounts:superuser_database_management")

    # Prevent clearing system tables
    protected_tables = [
        "auth_permission",
        "django_content_type",
        "django_migrations",
        "django_session",
        "sqlite_sequence",
    ]

    if any(protected in table_name.lower() for protected in protected_tables):
        messages.error(request, f"Cannot clear protected system table: {table_name}")
        return redirect("accounts:superuser_database_management")

    try:
        with connection.cursor() as cursor:
            # Get count before deletion
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]

            # Delete all records
            cursor.execute(f"DELETE FROM {table_name}")

            # Reset auto-increment for SQLite
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")

        messages.success(
            request, f'Successfully cleared {count} records from table "{table_name}".'
        )

    except Exception as e:
        messages.error(request, f"Error clearing table: {str(e)}")

    return redirect("accounts:superuser_database_management")


@superuser_required
def superuser_security_audit(request):
    """Security audit panel"""
    # Get recent security-related logs
    security_logs = ActivityLog.objects.filter(
        Q(action_type__in=["login", "logout", "failed_login", "permission_denied"])
    ).order_by("-timestamp")[:100]

    # Get failed login attempts
    failed_logins = ActivityLog.objects.filter(action_type="failed_login").order_by(
        "-timestamp"
    )[:50]

    # Calculate statistics
    successful_logins = ActivityLog.objects.filter(action_type="login").count()

    password_changes = ActivityLog.objects.filter(
        action_type__icontains="password"
    ).count()

    return render(
        request,
        "accounts/superuser/security_audit.html",
        {
            "security_logs": security_logs,
            "failed_logins": failed_logins,
            "successful_logins": successful_logins,
            "password_changes": password_changes,
            "page_title": "Security Audit",
            "active_nav": "security_audit",
        },
    )


@superuser_required
def superuser_backup_restore(request):
    """Backup and restore operations"""
    return render(
        request,
        "accounts/superuser/backup_restore.html",
        {
            "page_title": "Backup & Restore",
            "active_nav": "backup_restore",
        },
    )


@superuser_required
def create_backup(request):
    """Create database backup"""
    import subprocess
    import os
    from django.conf import settings
    from django.utils import timezone
    import json
    from django.core.management import call_command
    from django.http import HttpResponse

    if request.method == "POST":
        try:
            backup_name = request.POST.get("backup_name", "")
            backup_description = request.POST.get("backup_description", "")
            include_media = request.POST.get("include_media") == "on"

            # Create backup directory if it doesn't exist
            backup_dir = os.path.join(settings.BASE_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)

            # Generate backup filename
            timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
            if backup_name:
                filename = f"{backup_name}_{timestamp}.sql"
            else:
                filename = f"backup_{timestamp}.sql"

            backup_path = os.path.join(backup_dir, filename)

            # Create database backup using Django management command
            with open(backup_path, "w") as f:
                call_command("dumpdata", stdout=f)

            # Store backup metadata
            metadata = {
                "filename": filename,
                "name": backup_name or f"Backup_{timestamp}",
                "description": backup_description,
                "created_at": timezone.now().isoformat(),
                "include_media": include_media,
                "size": os.path.getsize(backup_path),
                "user": request.user.username,
            }

            metadata_path = os.path.join(backup_dir, f"{filename}.meta")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            messages.success(
                request, f"Backup '{metadata['name']}' created successfully!"
            )
            return redirect("accounts:superuser_backup_restore")

        except Exception as e:
            messages.error(request, f"Error creating backup: {str(e)}")

    return redirect("accounts:superuser_backup_restore")


@superuser_required
def restore_backup(request):
    """Restore database from backup"""
    import subprocess
    import os
    from django.conf import settings
    import json

    if request.method == "POST":
        try:
            backup_file = request.FILES.get("backup_file")
            confirm_restore = request.POST.get("confirm_restore") == "on"

            if not backup_file:
                messages.error(request, "Please select a backup file.")
                return redirect("accounts:superuser_backup_restore")

            if not confirm_restore:
                messages.error(
                    request,
                    "Please confirm that you understand the restore will overwrite current data.",
                )
                return redirect("accounts:superuser_backup_restore")

            # Save uploaded file temporarily
            temp_dir = os.path.join(settings.BASE_DIR, "temp_restore")
            os.makedirs(temp_dir, exist_ok=True)

            temp_path = os.path.join(temp_dir, backup_file.name)
            with open(temp_path, "wb+") as destination:
                for chunk in backup_file.chunks():
                    destination.write(chunk)

            # Process restore (simplified version - in production, you'd want more sophisticated restore)
            messages.warning(
                request,
                "Restore functionality needs to be implemented with proper database migration handling.",
            )
            messages.info(
                request,
                f"File '{backup_file.name}' uploaded successfully. Manual restore required.",
            )

            # Clean up temporary file
            os.remove(temp_path)

            return redirect("accounts:superuser_backup_restore")

        except Exception as e:
            messages.error(request, f"Error restoring backup: {str(e)}")

    return redirect("accounts:superuser_backup_restore")


@superuser_required
def backup_list(request):
    """Return HTML fragment of backup list"""
    import os
    import json
    from django.conf import settings
    from django.http import HttpResponse

    try:
        backup_dir = os.path.join(settings.BASE_DIR, "backups")
        backups = []

        if os.path.exists(backup_dir):
            for file in os.listdir(backup_dir):
                if file.endswith(".meta"):
                    metadata_path = os.path.join(backup_dir, file)
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        backups.append(metadata)

        backups.sort(key=lambda x: x["created_at"], reverse=True)

        html = ""
        if backups:
            for backup in backups:
                html += f"""
                <tr>
                    <td>{backup["name"]}</td>
                    <td>{backup["description"] or "N/A"}</td>
                    <td>{backup["created_at"]}</td>
                    <td>{backup["size"] / 1024:.2f} KB</td>
                    <td>SQL</td>
                    <td>
                        <a href="/accounts/superuser/download-backup/{backup["filename"]}/" 
                           class="btn btn-sm btn-primary me-1">
                            <i class="fas fa-download"></i>
                        </a>
                        <button class="btn btn-sm btn-danger delete-backup" 
                                data-backup-name="{backup["name"]}"
                                data-url="/accounts/superuser/delete-backup/{backup["filename"]}/">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
                """
        else:
            html = """
            <tr>
                <td colspan="6" class="text-center text-muted">
                    <i class="fas fa-inbox fa-3x mb-3"></i>
                    <p>No backup files found. Create your first backup above.</p>
                </td>
            </tr>
            """

        return HttpResponse(html)

    except Exception as e:
        return HttpResponse(
            f"<tr><td colspan='6'>Error loading backups: {str(e)}</td></tr>"
        )


@superuser_required
def delete_backup(request, backup_name):
    """Delete a backup file"""
    import os
    from django.conf import settings

    try:
        backup_dir = os.path.join(settings.BASE_DIR, "backups")
        backup_path = os.path.join(backup_dir, backup_name)
        metadata_path = os.path.join(backup_dir, f"{backup_name}.meta")

        if os.path.exists(backup_path):
            os.remove(backup_path)
        if os.path.exists(metadata_path):
            os.remove(metadata_path)

        messages.success(request, f"Backup '{backup_name}' deleted successfully.")

    except Exception as e:
        messages.error(request, f"Error deleting backup: {str(e)}")

    return redirect("accounts:superuser_backup_restore")


@superuser_required
def download_backup(request, backup_name):
    """Download a backup file"""
    import os
    from django.conf import settings
    from django.http import HttpResponse, Http404

    try:
        backup_dir = os.path.join(settings.BASE_DIR, "backups")
        backup_path = os.path.join(backup_dir, backup_name)

        if not os.path.exists(backup_path):
            raise Http404("Backup file not found")

        with open(backup_path, "rb") as f:
            response = HttpResponse(f.read(), content_type="application/octet-stream")
            response["Content-Disposition"] = f'attachment; filename="{backup_name}"'
            return response

    except Exception as e:
        messages.error(request, f"Error downloading backup: {str(e)}")
        return redirect("accounts:superuser_backup_restore")


@superuser_required
def superuser_system_diagnostics(request):
    """System diagnostics panel"""
    import platform
    import os
    from django.conf import settings

    # Basic system information (always available)
    diagnostics = {
        "system": platform.system(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "django_version": __import__("django").get_version(),
    }

    # Try to get advanced metrics with psutil
    try:
        import psutil

        # Get correct disk path for Windows
        disk_path = "/" if os.name != "nt" else "C:"

        diagnostics.update(
            {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "cpu_count": psutil.cpu_count(),
                "memory": psutil.virtual_memory(),
                "disk": psutil.disk_usage(disk_path),
                "psutil_available": True,
            }
        )
    except ImportError:
        diagnostics.update(
            {
                "psutil_available": False,
                "psutil_error": "psutil module not installed. Install it with: pip install psutil",
            }
        )
    except Exception as e:
        diagnostics.update(
            {
                "psutil_available": False,
                "psutil_error": f"Error getting system metrics: {str(e)}",
            }
        )

    # Get database information
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_count = len(cursor.fetchall())
            diagnostics["database_tables"] = table_count
            diagnostics["database_engine"] = settings.DATABASES["default"]["ENGINE"]
    except Exception as e:
        diagnostics["database_error"] = str(e)

    return render(
        request,
        "accounts/superuser/system_diagnostics.html",
        {
            "diagnostics": diagnostics,
            "page_title": "System Diagnostics",
            "active_nav": "system_diagnostics",
        },
    )


@superuser_required
def superuser_mass_email(request):
    """Send mass emails to users"""
    from django.core.mail import send_mail
    from django.conf import settings

    if request.method == "POST":
        subject = request.POST.get("subject")
        message = request.POST.get("message")
        user_ids = request.POST.getlist("user_ids")

        if subject and message and user_ids:
            users = User.objects.filter(id__in=user_ids)
            email_count = 0
            failed_count = 0

            for user in users:
                if user.email:
                    try:
                        send_mail(
                            subject=subject,
                            message=message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[user.email],
                            fail_silently=False,
                        )
                        email_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send email to {user.email}: {str(e)}")
                        failed_count += 1

            if email_count > 0:
                messages.success(
                    request,
                    f"Email successfully sent to {email_count} user{'s' if email_count != 1 else ''}.",
                )
            if failed_count > 0:
                messages.warning(
                    request,
                    f"Failed to send email to {failed_count} user{'s' if failed_count != 1 else ''}. Check logs for details.",
                )
        else:
            messages.error(
                request,
                "Please provide subject, message, and select at least one user.",
            )

    users = User.objects.order_by("username")
    return render(
        request,
        "accounts/superuser/mass_email.html",
        {
            "users": users,
            "page_title": "Mass Email Users",
            "active_nav": "mass_email",
        },
    )


@superuser_required
def superuser_api_management(request):
    """API management panel"""
    return render(
        request,
        "accounts/superuser/api_management.html",
        {
            "page_title": "API Management",
            "active_nav": "api_management",
        },
    )


@superuser_required
def superuser_logs_viewer(request):
    """System logs viewer"""
    import logging
    import os
    from django.conf import settings

    # Get log files
    log_files = []
    log_dir = os.path.join(settings.BASE_DIR, "logs")

    # Check both Django handlers and logs directory
    for handler in logging.root.handlers:
        if hasattr(handler, "baseFilename"):
            log_files.append(handler.baseFilename)

    # Also scan logs directory for additional log files
    if os.path.exists(log_dir):
        for filename in os.listdir(log_dir):
            if filename.endswith(".log") or filename.endswith(".txt"):
                log_files.append(os.path.join(log_dir, filename))

    return render(
        request,
        "accounts/superuser/logs_viewer.html",
        {
            "log_files": log_files,
            "page_title": "System Logs Viewer",
            "active_nav": "logs_viewer",
        },
    )


@superuser_required
def superuser_read_log_file(request):
    """Read a specific log file (AJAX endpoint)"""
    import os
    from django.conf import settings
    from django.http import JsonResponse
    from django.views.decorators.csrf import csrf_exempt

    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        file_path = request.POST.get("file_path")

        # Security check - ensure file is in allowed directory
        log_dir = os.path.join(settings.BASE_DIR, "logs")
        if not os.path.exists(log_dir):
            log_dir = os.path.join(settings.BASE_DIR)  # Fallback to base dir

        # Validate the file path to prevent directory traversal
        if not file_path:
            return JsonResponse({"error": "No file path provided"}, status=400)

        # Ensure file path is within allowed directories
        is_allowed = (
            file_path.startswith(log_dir)
            or file_path.startswith(settings.BASE_DIR)
            and (
                file_path.endswith(".log")
                or file_path.endswith(".txt")
                or "logs" in file_path
            )
        )

        if not is_allowed:
            return JsonResponse({"error": "Access denied"}, status=403)

        try:
            # Read last N lines of log file for performance
            max_lines = 1000  # Limit for performance
            lines = []

            with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                # Read file in reverse to get last lines efficiently
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)

                for line in file:
                    if len(lines) >= max_lines:
                        break
                    lines.append(line.strip())

            # Parse log lines
            parsed_logs = []
            for i, line in enumerate(lines):
                if not line.strip():
                    continue

                # Try to extract timestamp, level, and message
                parsed = parse_log_line(line)
                if parsed:
                    parsed["line_number"] = i + 1
                    parsed_logs.append(parsed)

            return JsonResponse(
                {
                    "success": True,
                    "logs": parsed_logs,
                    "total_lines": len(lines),
                    "file_path": file_path,
                }
            )

        except Exception as e:
            logger.error(f"Error reading log file {file_path}: {str(e)}")
            return JsonResponse(
                {"error": f"Failed to read log file: {str(e)}"}, status=500
            )

    return JsonResponse({"error": "Invalid request"}, status=400)


def parse_log_line(line):
    """Parse a log line to extract timestamp, level, and message"""
    import re
    from datetime import datetime

    # Common log formats
    patterns = [
        # Django default format: 2025-10-29 14:30:15,123 INFO django.request: Message
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[\,\d]*)\s+(\w+)\s+(.+?):?\s*(.*)",
        # Python logging: 2025-10-29 14:30:15 - INFO - Message
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*-\s*(\w+)\s*-\s*(.*)",
        # Apache/Nginx style: [29/Oct/2025:14:30:15 +0000] INFO Message
        r"\[([^\]]+)\]\s+(\w+)\s+(.*)",
        # Simple format: INFO 2025-10-29 Message
        r"(\w+)\s+(\d{4}-\d{2}-\d{2}[^\s]*)\s+(.*)",
    ]

    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            groups = match.groups()

            if len(groups) == 3:  # timestamp, level, message
                try:
                    return {
                        "timestamp": groups[0],
                        "level": groups[1].upper(),
                        "message": groups[2],
                        "raw": line,
                    }
                except:
                    pass
            elif len(groups) == 2:  # level, rest
                try:
                    return {
                        "timestamp": groups[1] if groups[1].count("-") >= 2 else "",
                        "level": groups[0].upper(),
                        "message": groups[0] if groups[0].count("-") < 2 else groups[1],
                        "raw": line,
                    }
                except:
                    pass

    # If no pattern matches, treat as info level
    return {"timestamp": "", "level": "INFO", "message": line, "raw": line}


# ============================================================================
# COMPREHENSIVE RBAC DASHBOARD - ADMIN TOTAL CONTROL
# ============================================================================


@login_required
@user_passes_test(
    lambda u: u.is_superuser or u.is_staff or user_has_permission(u, "roles.view")
)
def rbac_dashboard(request):
    """
    Comprehensive RBAC Dashboard for Admin to have total control over:
    - Roles and permissions
    - User-role assignments
    - Permission assignments
    - Role hierarchy
    - Audit trails
    """
    from django.db.models import Count, Q
    from datetime import timedelta

    # Get statistics
    total_roles = Role.objects.count()
    total_users = User.objects.count()
    total_permissions = Permission.objects.count()

    # Users without roles (security concern)
    users_without_roles = User.objects.filter(roles__isnull=True).count()

    # Users with multiple roles
    users_with_multiple_roles = (
        User.objects.annotate(role_count=Count("roles"))
        .filter(role_count__gt=1)
        .count()
    )

    # Role statistics with user counts
    roles_with_stats = Role.objects.annotate(
        user_count=Count("customuser_role", distinct=True),
        permission_count=Count("permissions", distinct=True),
        child_count=Count("children", distinct=True),
    ).order_by("-user_count", "name")

    # Top roles by user count
    top_roles = roles_with_stats[:10]

    # Recently created roles
    recent_roles = Role.objects.order_by("-id")[:5]

    # Users with their roles (for quick assignment view)
    users_with_roles = (
        User.objects.prefetch_related("roles")
        .annotate(role_count=Count("roles"))
        .order_by("-role_count", "username")[:20]
    )

    # Recent RBAC audit logs
    recent_audit_logs = (
        AuditLog.objects.filter(
            Q(action__icontains="role")
            | Q(action__icontains="permission")
            | Q(action__icontains="privilege")
        )
        .select_related("user", "target_user")
        .order_by("-timestamp")[:10]
    )

    # Role hierarchy tree for visualization
    root_roles = Role.objects.filter(parent__isnull=True).prefetch_related("children")

    # Permissions by category (app label)
    permissions_by_app = (
        Permission.objects.select_related("content_type")
        .values("content_type__app_label")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # Calculate role inheritance depth
    def get_role_depth(role, depth=0):
        """Calculate the depth of a role in the hierarchy"""
        if not role.parent:
            return depth
        return get_role_depth(role.parent, depth + 1)

    max_hierarchy_depth = 0
    for role in Role.objects.all():
        depth = get_role_depth(role)
        max_hierarchy_depth = max(max_hierarchy_depth, depth)

    # Check for potential issues
    issues = []

    # Users without any roles
    if users_without_roles > 0:
        issues.append(
            {
                "type": "warning",
                "message": f"{users_without_roles} user(s) have no roles assigned",
                "action_url": reverse("accounts:user_dashboard"),
                "action_text": "Assign Roles",
            }
        )

    # Check for circular references in role hierarchy
    circular_refs = []
    for role in Role.objects.all():
        if role.check_circular_reference(role.parent):
            circular_refs.append(role.name)

    if circular_refs:
        issues.append(
            {
                "type": "danger",
                "message": f"Circular reference detected in roles: {', '.join(circular_refs)}",
                "action_url": reverse("accounts:role_management"),
                "action_text": "Fix Hierarchy",
            }
        )

    # Roles with no permissions
    roles_without_permissions = Role.objects.filter(permissions__isnull=True).count()
    if roles_without_permissions > 0:
        issues.append(
            {
                "type": "info",
                "message": f"{roles_without_permissions} role(s) have no permissions assigned",
                "action_url": reverse("accounts:role_management"),
                "action_text": "Review Roles",
            }
        )

    context = {
        "total_roles": total_roles,
        "total_users": total_users,
        "total_permissions": total_permissions,
        "users_without_roles": users_without_roles,
        "users_with_multiple_roles": users_with_multiple_roles,
        "roles_without_permissions": roles_without_permissions,
        "max_hierarchy_depth": max_hierarchy_depth,
        "top_roles": top_roles,
        "recent_roles": recent_roles,
        "users_with_roles": users_with_roles,
        "recent_audit_logs": recent_audit_logs,
        "root_roles": root_roles,
        "permissions_by_app": permissions_by_app,
        "issues": issues,
        "page_title": "RBAC Dashboard - Admin Control Center",
        "active_nav": "rbac_dashboard",
    }
    return render(request, "accounts/rbac_dashboard.html", context)


@login_required
@permission_required("users.edit")
def ajax_assign_role(request):
    """
    AJAX endpoint for quick role assignment/unassignment from RBAC dashboard
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST method required"})

    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        role_id = data.get("role_id")
        action = data.get("action")  # 'assign' or 'remove'

        if not all([user_id, role_id, action]):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Missing required parameters: user_id, role_id, action",
                }
            )

        user = get_object_or_404(User, id=user_id)
        role = get_object_or_404(Role, id=role_id)

        if action == "assign":
            user.roles.add(role)
            message = f'Role "{role.name}" assigned to {user.username}'
        elif action == "remove":
            user.roles.remove(role)
            message = f'Role "{role.name}" removed from {user.username}'
        else:
            return JsonResponse({"success": False, "error": "Invalid action"})

        # Log the action
        AuditLog.objects.create(
            user=request.user,
            target_user=user,
            action="role_assignment",
            details={
                "action": action,
                "role_name": role.name,
                "role_id": role.id,
                "performed_via": "rbac_dashboard_ajax",
            },
            ip_address=request.META.get("REMOTE_ADDR"),
            timestamp=timezone.now(),
        )

        return JsonResponse(
            {
                "success": True,
                "message": message,
                "user_roles": list(user.roles.values_list("name", flat=True)),
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@permission_required("roles.edit")
def ajax_update_role_permissions(request):
    """
    AJAX endpoint for quick permission updates on roles
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST method required"})

    try:
        data = json.loads(request.body)
        role_id = data.get("role_id")
        permission_ids = data.get("permission_ids", [])

        if not role_id:
            return JsonResponse({"success": False, "error": "role_id required"})

        role = get_object_or_404(Role, id=role_id)

        # Get current permissions for logging
        old_permissions = set(role.permissions.values_list("id", flat=True))
        new_permissions = set(permission_ids)

        # Update permissions
        role.permissions.set(permission_ids)

        # Calculate changes
        added = new_permissions - old_permissions
        removed = old_permissions - new_permissions

        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action="role_permissions_update",
            details={
                "role_name": role.name,
                "role_id": role.id,
                "permissions_added_count": len(added),
                "permissions_removed_count": len(removed),
                "total_permissions": len(new_permissions),
                "performed_via": "rbac_dashboard_ajax",
            },
            ip_address=request.META.get("REMOTE_ADDR"),
            timestamp=timezone.now(),
        )

        return JsonResponse(
            {
                "success": True,
                "message": f'Permissions updated for role "{role.name}"',
                "added_count": len(added),
                "removed_count": len(removed),
                "total_permissions": len(new_permissions),
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@permission_required("users.view")
def rbac_user_matrix(request):
    """
    View showing a matrix of users and their roles for bulk assignment
    """
    users = (
        User.objects.prefetch_related("roles")
        .annotate(role_count=Count("roles"))
        .order_by("username")
    )

    roles = Role.objects.all().order_by("name")

    # Create user-role matrix
    user_role_matrix = []
    for user in users:
        user_roles = set(user.roles.values_list("id", flat=True))
        user_role_matrix.append({"user": user, "roles": user_roles})

    context = {
        "user_role_matrix": user_role_matrix,
        "roles": roles,
        "page_title": "User-Role Assignment Matrix",
        "active_nav": "rbac_user_matrix",
    }
    return render(request, "accounts/rbac_user_matrix.html", context)


@login_required
@permission_required("roles.view")
def rbac_audit_trail(request):
    """
    Comprehensive audit trail for all RBAC-related activities
    """
    # Filter by action type
    action_filter = request.GET.get("action_type", "")

    # Base query - RBAC related actions
    rbac_actions = [
        "role_assignment",
        "role_permissions_update",
        "privilege_change",
        "create",
        "update",
        "delete",
        "user_bulk_action",
        "bulk_delete",
        "bulk_update",
    ]

    logs = (
        AuditLog.objects.filter(
            Q(action__in=rbac_actions)
            | Q(action__icontains="role")
            | Q(action__icontains="permission")
        )
        .select_related("user", "target_user")
        .order_by("-timestamp")
    )

    # Apply filters
    if action_filter:
        logs = logs.filter(action__icontains=action_filter)

    # Date range filter
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)

    # User filter
    user_filter = request.GET.get("user_id")
    if user_filter:
        logs = logs.filter(user_id=user_filter)

    # Pagination
    paginator = Paginator(logs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get all users for filter dropdown
    all_users = User.objects.filter(is_active=True).order_by("username")

    # Get statistics
    total_logs = logs.count()
    today_logs = logs.filter(timestamp__date=timezone.now().date()).count()

    # Group by action type for chart
    action_counts = (
        logs.values("action").annotate(count=Count("id")).order_by("-count")[:10]
    )

    context = {
        "page_obj": page_obj,
        "all_users": all_users,
        "action_filter": action_filter,
        "date_from": date_from,
        "date_to": date_to,
        "user_filter": user_filter,
        "total_logs": total_logs,
        "today_logs": today_logs,
        "action_counts": action_counts,
        "page_title": "RBAC Audit Trail",
        "active_nav": "rbac_audit_trail",
    }
    return render(request, "accounts/rbac_audit_trail.html", context)
