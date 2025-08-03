from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import CustomUserProfile, Department, Role, AuditLog
from .forms import (
    CustomLoginForm, UserProfileForm, StaffCreationForm, DepartmentForm,
    UserRegistrationForm, RoleForm, UserRoleAssignmentForm, BulkUserActionForm,
    PermissionFilterForm, AdvancedUserSearchForm
)
from core.models import AuditLog, InternalNotification
from django.utils import timezone
from django.db import models
from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.urls import reverse
User = get_user_model()




# Helper function to check if user is admin
def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.roles.filter(name='admin').exists()
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
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.urls import reverse
from .forms import CustomLoginForm

def custom_login_view(request):
    """
    Custom login view for application users (using phone numbers).
    Admin users should use /admin/ directly.
    """
    # Redirect if already logged in
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        form = CustomLoginForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']  # This will be phone number
            password = form.cleaned_data['password']
            
            # Authenticate user (will use PhoneNumberBackend)
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.get_full_name()}!')
                    
                    # Redirect to next page or dashboard
                    next_page = request.GET.get('next', 'dashboard:dashboard')
                    return redirect(next_page)
                else:
                    messages.error(request, 'Your account has been deactivated. Please contact support.')
            else:
                messages.error(request, 'Invalid phone number or password. Please try again.')
    else:
        form = CustomLoginForm()

    context = {
        'form': form,
        'title': 'Login',
        'page_title': 'HMS - Login',
    }
    return render(request, 'accounts/login.html', context)



def dashboard_view(request):
    return render(request, 'dashboard/dashboard.html')



@login_required
def profile(request):
    """View for user profile. Allows viewing own or others' profiles if authorized."""
    user_id_param = request.GET.get('user_id')
    target_user_for_view = None # Initialize

    if user_id_param:
        # Check if the logged-in user is authorized to view another profile
        if not (request.user.is_staff or request.user.is_superuser or str(request.user.id) == user_id_param):
            messages.error(request, "You are not authorized to view this profile.")
            # Redirect to logged-in user's own profile or dashboard
            return redirect(reverse('accounts:profile') if hasattr(request.user, 'id') else 'dashboard:dashboard')


        try:
            # Fetch the user whose profile is being viewed
            target_user_for_view = User.objects.select_related('profile').get(pk=user_id_param)
        except User.DoesNotExist:
            messages.error(request, "The requested user profile was not found.")
            return redirect('dashboard:dashboard') # Or a more appropriate redirect
    else:
        # Viewing own profile, ensure request.user is fully loaded with profile relation
        # Note: request.user is a SimpleLazyObject. Accessing its attributes resolves it.
        # We fetch it again with select_related to ensure profile is efficiently loaded.
        target_user_for_view = User.objects.select_related('profile').get(pk=request.user.pk)

    # At this point, target_user_for_view is a CustomUser instance.
    # Access its profile using the @property 'profile'
    user_profile_instance = target_user_for_view.profile 

    if user_profile_instance is None:
        # This case means the CustomUser exists, but their CustomUserProfile record does not.
        # This could be due to a signal failure or manual DB operation.
        # You might want to log this or even create a profile on-the-fly.
        messages.warning(request, f"Profile data for {target_user_for_view.username} is incomplete or missing.")
        # Optionally, create one if it makes sense for your application:
        # user_profile_instance, _ = CustomUserProfile.objects.get_or_create(user=target_user_for_view)

    context = {
        'viewed_user_profile': user_profile_instance,  # This is the CustomUserProfile instance (or None)
        'viewed_user_object': target_user_for_view     # This is the CustomUser instance
    }
    return render(request, 'accounts/profile.html', context)





@login_required
def edit_profile(request):
    user_id_to_edit = request.GET.get('user_id')
    target_user = None

    # Determine which user's profile to edit
    if user_id_to_edit:
        # Allow staff/superusers to edit others, or users to edit their own
        if not (request.user.is_staff or request.user.is_superuser or str(request.user.id) == user_id_to_edit):
            messages.error(request, "You are not authorized to edit this profile.")
            # Redirect to their own profile or a safe page
            return redirect(reverse('accounts:profile') + (f'?user_id={request.user.id}' if request.user.id else ''))
        
        try:
            # Fetch the CustomUser instance directly
            target_user = User.objects.get(pk=user_id_to_edit)
        except User.DoesNotExist:
            messages.error(request, "User to edit not found.")
            return redirect(reverse('dashboard:dashboard')) # Or a more appropriate page
    else:
        # If no user_id, edit the logged-in user's profile
        target_user = request.user

    # target_user is now the CustomUser instance whose profile is being edited.
    # The form's __init__ will handle accessing target_user.profile.

    if request.method == 'POST':
        # Check if username is empty in the POST data and set it to the current username
        post_data = request.POST.copy()  # Make a mutable copy of the POST data
        if not post_data.get('username') and target_user:
            post_data['username'] = target_user.username
            
        # Pass the modified POST data to the form
        form = UserProfileForm(post_data, request.FILES, instance=target_user, request_user=request.user)
        if form.is_valid():
            form.save() # The form's save method now handles saving both User and Profile
            messages.success(request, f"{target_user.username}'s profile has been updated successfully!")
            return redirect(reverse('accounts:profile') + f'?user_id={target_user.id}')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pass the CustomUser instance (target_user) to the form
        form = UserProfileForm(instance=target_user, request_user=request.user)

    context = {
        'form': form,
        'profile_user_object': target_user, # Pass the user object for template context
        'page_title': f'Edit Profile: {target_user.username}',
        # Add a flag for template to conditionally show admin fields
        'can_edit_admin_fields': request.user.is_staff or request.user.is_superuser 
    }
    return render(request, 'accounts/edit_profile.html', context)


@login_required
@user_passes_test(is_admin)
def staff_list(request):
    """View for listing all staff members (admin only)"""
    staff = CustomUserProfile.objects.all().order_by('role', 'user__phone_number')
    context = {
        'staff': staff
    }
    return render(request, 'accounts/staff_list.html', context)

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
        "role": user.get_profile.role,
        "department": user.get_profile.department,
        "employee_id": user.get_profile.employee_id,
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
@user_passes_test(is_admin)
def add_staff(request):
    """View for adding new staff member (admin only)"""
    if request.method == 'POST':
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_staff_onboarding_task_to_mcp(user)
            messages.success(request, f'Account created for {user.username}!')
            return redirect('accounts:staff_list')
    else:
        form = StaffCreationForm()

    context = {
        'form': form,
        'title': 'Add Staff Member'
    }
    return render(request, 'accounts/staff_form.html', context)

@login_required
@user_passes_test(is_admin)
def edit_staff(request, staff_id):
    """View for editing staff member (admin only)"""
    user_profile = get_object_or_404(CustomUserProfile, id=staff_id)
    user = user_profile.user

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, f'{user.username}\'s profile has been updated!')
            return redirect('accounts:staff_list')
    else:
        form = UserProfileForm(instance=user_profile)

    context = {
        'form': form,
        'title': f'Edit {user.username}',
        'staff_id': staff_id
    }
    return render(request, 'accounts/staff_form.html', context)

@login_required
@user_passes_test(is_admin)
def delete_staff(request, staff_id):
    """View for deleting staff member (admin only)"""
    user_profile = get_object_or_404(CustomUserProfile, id=staff_id)
    user = user_profile.user

    if request.method == 'POST':
        # Instead of deleting, we can deactivate the user
        user.is_active = False
        user.save()
        user_profile.is_active = False
        user_profile.save()
        messages.success(request, f'{user.username} has been deactivated!')
        return redirect('accounts:staff_list')

    context = {
        'user_profile': user_profile
    }
    return render(request, 'accounts/delete_staff.html', context)

@login_required
@user_passes_test(is_admin)
def department_list(request):
    """View for listing all departments (admin only)"""
    departments = Department.objects.all().order_by('name')
    context = {
        'departments': departments
    }
    return render(request, 'accounts/department_list.html', context)

@login_required
@user_passes_test(is_admin)
def add_department(request):
    """View for adding new department (admin only)"""
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department has been added successfully!')
            return redirect('accounts:department_list')
    else:
        form = DepartmentForm()

    context = {
        'form': form,
        'title': 'Add Department'
    }
    return render(request, 'accounts/department_form.html', context)

@login_required
@user_passes_test(is_admin)
def edit_department(request, department_id):
    """View for editing department (admin only)"""
    department = get_object_or_404(Department, id=department_id)

    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, f'Department {department.name} has been updated!')
            return redirect('accounts:department_list')
    else:
        form = DepartmentForm(instance=department)

    context = {
        'form': form,
        'title': f'Edit {department.name}',
        'department_id': department_id
    }
    return render(request, 'accounts/department_form.html', context)

@login_required
@user_passes_test(is_admin)
def delete_department(request, department_id):
    """View for deleting department (admin only)"""
    department = get_object_or_404(Department, id=department_id)

    if request.method == 'POST':
        department.delete()
        messages.success(request, f'Department {department.name} has been deleted!')
        return redirect('accounts:department_list')

    context = {
        'department': department
    }
    return render(request, 'accounts/delete_department.html', context)

@login_required
def api_users(request):
    """API view for getting user information"""
    role = request.GET.get('role', None)

    users_query = User.objects.filter(is_active=True)

    if role:
        users_query = users_query.filter(profile__role=role)

    users = users_query.select_related('profile').prefetch_related('roles')

    results = []
    for user in users:
        user_roles = list(user.roles.values_list('name', flat=True))
        results.append({
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name(),
            'roles': user_roles,
            'department': user.profile.department if user.profile else None
        })

    return JsonResponse(results, safe=False)

def register(request):
    """User registration view using phone number as authentication."""
    from .forms import UserRegistrationForm
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Optionally create CustomUserProfile and set phone_number here
            profile = user.get_profile
            profile.phone_number = form.cleaned_data['phone_number']
            profile.save()
            # Assign selected module (role) to user
            selected_role = form.cleaned_data['module']
            user.roles.set([selected_role])  # Remove any other roles, only assign selected
            # Assign permissions from the selected role
            user.user_permissions.set(selected_role.permissions.all())
            user.save()
            messages.success(request, 'Your account has been created. You can now log in.')
            return redirect('accounts:login')
        else:
            print('Registration form errors:', form.errors.as_json())  # Debug print
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form, 'title': 'Register'})


@login_required
@user_passes_test(is_admin)
def create_role(request):
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Role created successfully.')
            return redirect('accounts:role_management')
    else:
        form = RoleForm()
    context = {
        'form': form,
        'page_title': 'Create Role'
    }
    return render(request, 'accounts/role_form.html', context)

@login_required
@user_passes_test(is_admin)
def edit_role(request, role_id):
    role = get_object_or_404(Role, id=role_id)
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, 'Role updated successfully.')
            return redirect('accounts:role_management')
    else:
        form = RoleForm(instance=role)
    context = {
        'form': form,
        'page_title': f'Edit Role: {role.name}'
    }
    return render(request, 'accounts/role_form.html', context)

@login_required
def role_demo(request):
    return render(request, 'accounts/role_demo.html', {'page_title': 'Role Demo'})

@login_required
@user_passes_test(is_admin)
def audit_logs(request):
    logs = AuditLog.objects.all().order_by('-timestamp')
    form = AuditLogFilterForm(request.GET)
    if form.is_valid():
        user = form.cleaned_data.get('user')
        action = form.cleaned_data.get('action')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

        if user:
            logs = logs.filter(user=user)
        if action:
            logs = logs.filter(action=action)
        if start_date:
            logs = logs.filter(timestamp__gte=start_date)
        if end_date:
            logs = logs.filter(timestamp__lte=end_date)

    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'logs': page_obj,
        'form': form,
        'page_title': 'Audit Logs'
    }
    return render(request, 'accounts/audit_logs.html', context)

@login_required
@user_passes_test(is_admin)
def permission_management(request):
    permissions = Permission.objects.all()
    form = PermissionFilterForm(request.GET)
    if form.is_valid():
        content_type = form.cleaned_data.get('content_type')
        if content_type:
            permissions = permissions.filter(content_type=content_type)

    context = {
        'permissions': permissions,
        'form': form,
        'page_title': 'Permission Management'
    }
    return render(request, 'accounts/permission_management.html', context)

@login_required
@user_passes_test(is_admin)
def bulk_user_actions(request):
    if request.method == 'POST':
        form = BulkUserActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            users = form.cleaned_data['users']
            if action == 'activate':
                users.update(is_active=True)
            elif action == 'deactivate':
                users.update(is_active=False)
            elif action == 'assign_role':
                role = form.cleaned_data['role']
                for user in users:
                    user.roles.set([role])
            messages.success(request, f'Bulk action "{action}" applied to {users.count()} users.')
            return redirect('accounts:user_dashboard')
    return redirect('accounts:user_dashboard')

@login_required
@user_passes_test(is_admin)
def user_privileges(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserRoleAssignmentForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Roles for {user.username} updated successfully.')
            return redirect('accounts:user_dashboard')
    else:
        form = UserRoleAssignmentForm(instance=user)
    context = {
        'form': form,
        'user': user,
        'page_title': f'Manage Roles for {user.username}'
    }
    return render(request, 'accounts/user_privileges.html', context)

@login_required
@user_passes_test(is_admin)
def delete_role(request, role_id):
    role = get_object_or_404(Role, id=role_id)
    if request.method == 'POST':
        role.delete()
        messages.success(request, 'Role deleted successfully.')
        return redirect('accounts:role_management')
    context = {
        'role': role,
        'page_title': f'Delete Role: {role.name}'
    }
    return render(request, 'accounts/role_confirm_delete.html', context)


@login_required
@user_passes_test(is_admin)
def role_management(request):
    roles = Role.objects.all().prefetch_related('permissions')
    form = RoleForm()
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Role created successfully.')
            return redirect('accounts:role_management')

    context = {
        'roles': roles,
        'form': form,
        'page_title': 'Role Management'
    }
    return render(request, 'accounts/role_management.html', context)


@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def user_dashboard(request):
    """Admin user management dashboard: filter, search, bulk actions, CSV export."""
    users = User.objects.all().select_related('profile')
    # Filters
    search = request.GET.get('search', '')
    role = request.GET.get('role', '')
    is_active = request.GET.get('is_active', '')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    if role:
        users = users.filter(profile__role=role)
    if is_active == 'true':
        users = users.filter(is_active=True)
    elif is_active == 'false':
        users = users.filter(is_active=False)

    # Bulk actions
    if request.method == 'POST' and 'bulk_action' in request.POST:
        action = request.POST.get('bulk_action')
        selected_ids = request.POST.getlist('selected_users')
        if selected_ids:
            qs = User.objects.filter(id__in=selected_ids)
            if action == 'activate':
                qs.update(is_active=True)
            elif action == 'deactivate':
                qs.update(is_active=False)
            # Role assignment (if provided)
            new_role = request.POST.get('assign_role')
            if action == 'assign_role' and new_role:
                for user in qs:
                    user.get_profile.role = new_role
                    user.get_profile.save()
            from django.contrib import messages
            messages.success(request, f"Bulk action '{action}' applied to {qs.count()} user(s).")
            # Audit log for user actions (view, bulk action)
            AuditLog.objects.create(
                user=request.user,
                action='user_bulk_action',
                details=f"Bulk action '{action}' applied to users: {selected_ids}",
                timestamp=timezone.now()
            )
            # Optional: send notification to superusers
            # Get all superusers to notify them about bulk actions
            superusers = CustomUser.objects.filter(is_superuser=True)
            for superuser in superusers:
                InternalNotification.objects.create(
                    user=superuser,
                    message=f"Bulk user action '{action}' performed by {request.user.username}."
                )
            return redirect('accounts:user_dashboard')

    # CSV export
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="user_dashboard.csv"'
        import csv
        writer = csv.writer(response)
        writer.writerow(['Username', 'Full Name', 'Email', 'Role', 'Status'])
        for user in users:
            writer.writerow([
                user.username,
                user.get_full_name(),
                user.email,
                getattr(user.get_profile, 'role', ''),
                'Active' if user.is_active else 'Inactive',
            ])
        return response

    # Pagination
    paginator = Paginator(users.order_by('username'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'users': page_obj,
        'search': search,
        'role': role,
        'is_active': is_active,
        'roles': CustomUserProfile.ROLE_CHOICES,
        'page_title': 'User Management Dashboard',
    }
    return render(request, 'accounts/user_dashboard.html', context)


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
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator # Ensure Paginator is imported
from django.utils import timezone
from .models import CustomUserProfile, Department, Role, AuditLog
from .forms import CustomLoginForm, UserProfileForm, StaffCreationForm, DepartmentForm, UserRegistrationForm
from django.contrib.auth import get_user_model
from django.urls import reverse


User = get_user_model()

# Helper function (ensure it's defined or imported)
def is_admin_or_staff(user):
    return user.is_authenticated and (
        user.is_superuser or user.is_staff
    )

@login_required # Added @login_required as it's a dashboard
@user_passes_test(is_admin_or_staff)
def user_dashboard(request):
    users_query = User.objects.all().prefetch_related('roles', 'profile')
    
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    is_active_filter = request.GET.get('is_active', '') # Renamed to avoid clash with user.is_active
    
    if search_query:
        users_query = users_query.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    if role_filter:
        users_query = users_query.filter(profile__role=role_filter)
    
    if is_active_filter == 'true':
        users_query = users_query.filter(is_active=True)
    elif is_active_filter == 'false':
        users_query = users_query.filter(is_active=False)

    # Bulk actions
    if request.method == 'POST' and 'bulk_action' in request.POST:
        action = request.POST.get('bulk_action')
        selected_ids = request.POST.getlist('selected_users')
        if selected_ids:
            qs = User.objects.filter(id__in=selected_ids)
            if action == 'activate':
                qs.update(is_active=True)
            elif action == 'deactivate':
                qs.update(is_active=False)
            elif action == 'assign_role':
                new_role_name = request.POST.get('assign_role')
                if new_role_name:
                    try:
                        role_obj = Role.objects.get(name=new_role_name)
                        for user_obj in qs:
                            user_obj.roles.set([role_obj]) # Use set() to assign a single role, clear others
                                                          # Or .add() if multiple roles are allowed and you want to add this one
                    except Role.DoesNotExist:
                        messages.error(request, f"Specified role '{new_role_name}' doesn't exist")
            
            messages.success(request, f"Bulk action '{action}' applied to {qs.count()} user(s).")
            AuditLog.objects.create(
                user=request.user,
                action='user_bulk_action',
                target_user=None,
                details={"action": action, "applied_to_user_ids": selected_ids, "count": qs.count()},
                ip_address=request.META.get('REMOTE_ADDR'),
                timestamp=timezone.now()
            )
            return redirect('accounts:user_dashboard') # Ensure this URL name is correct

    # CSV export
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="user_dashboard.csv"'
        import csv
        writer = csv.writer(response)
        writer.writerow(['Username', 'Full Name', 'Email', 'Phone', 'Roles', 'Status'])
        # Use the filtered users_query for export
        for user_obj in users_query.order_by('username'): 
            writer.writerow([
                user_obj.username,
                user_obj.get_full_name(),
                user_obj.email,
                user_obj.phone_number,
                ', '.join([role.name for role in user_obj.roles.all()]),
                'Active' if user_obj.is_active else 'Inactive',
            ])
        return response

    # Pagination
    paginator = Paginator(users_query.order_by('username'), 25) # Apply ordering before pagination
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Prepare elided page range for pagination template
    # Adjust on_each_side and on_ends as per your preference
    elided_page_range = page_obj.paginator.get_elided_page_range(
        number=page_obj.number, 
        on_each_side=2,  # e.g., 2 pages on each side of the current page
        on_ends=1        # e.g., 1 page at the beginning and end
    )

    all_roles = Role.objects.all().order_by('name')
    role_counts_data = Role.objects.annotate(count=Count('customuser_role')).values('name', 'count')
    active_count = User.objects.filter(is_active=True).count() # Consider filtering this by current query too if makes sense
    inactive_count = User.objects.filter(is_active=False).count() # Same as above

    if request.method == 'GET': # Log only on initial load/filter, not POST actions
        # Convert is_active_filter to a boolean or None for better logging
        logged_is_active_filter = None
        if is_active_filter == 'true':
            logged_is_active_filter = True
        elif is_active_filter == 'false':
            logged_is_active_filter = False

        AuditLog.objects.create(
            user=request.user,
            action='user_dashboard_view',
            details={"filters": {"search": search_query, "role": role_filter, "is_active": logged_is_active_filter}},
            ip_address=request.META.get('REMOTE_ADDR'),
            timestamp=timezone.now()
        )

    context = {
        'page_obj': page_obj,
        'elided_page_range': elided_page_range, # Add this to context
        'search': search_query,
        'role': role_filter, # This context variable name 'role' is used in template for selected role in filter
        'is_active': is_active_filter,
        'roles': all_roles, # This context variable 'roles' is used for iterating Role objects in dropdowns
        'page_title': 'User Management',
        'active_nav': 'user_dashboard',
        'role_counts': list(role_counts_data),
        'active_count': active_count,
        'inactive_count': inactive_count,
    }
    return render(request, 'accounts/user_dashboard.html', context)


# ============================================================================
# PRIVILEGE MANAGEMENT VIEWS
# ============================================================================

@login_required
@user_passes_test(is_admin)
def role_management(request):
    """View for managing roles and permissions"""
    roles = Role.objects.all().prefetch_related('permissions', 'children').order_by('name')

    context = {
        'roles': roles,
        'page_title': 'Role Management',
        'active_nav': 'role_management',
    }
    return render(request, 'accounts/role_management.html', context)


@login_required
@user_passes_test(is_admin)
def create_role(request):
    """View for creating a new role"""
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save()

            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action='create',
                details={
                    'role_name': role.name,
                    'permissions': list(role.permissions.values_list('name', flat=True))
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                timestamp=timezone.now()
            )

            messages.success(request, f'Role "{role.name}" created successfully.')
            return redirect('accounts:role_management')
    else:
        form = RoleForm()

    context = {
        'form': form,
        'page_title': 'Create Role',
        'active_nav': 'role_management',
    }
    return render(request, 'accounts/create_role.html', context)


@login_required
@user_passes_test(is_admin)
def edit_role(request, role_id):
    """View for editing an existing role"""
    role = get_object_or_404(Role, id=role_id)

    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            old_permissions = list(role.permissions.values_list('name', flat=True))
            role = form.save()
            new_permissions = list(role.permissions.values_list('name', flat=True))

            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action='update',
                details={
                    'role_name': role.name,
                    'old_permissions': old_permissions,
                    'new_permissions': new_permissions
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                timestamp=timezone.now()
            )

            messages.success(request, f'Role "{role.name}" updated successfully.')
            return redirect('accounts:role_management')
    else:
        form = RoleForm(instance=role)

    context = {
        'form': form,
        'role': role,
        'page_title': f'Edit Role: {role.name}',
        'active_nav': 'role_management',
    }
    return render(request, 'accounts/edit_role.html', context)


@login_required
@user_passes_test(is_admin)
def delete_role(request, role_id):
    """View for deleting a role"""
    role = get_object_or_404(Role, id=role_id)

    if request.method == 'POST':
        role_name = role.name
        users_with_role = role.customuser_roles.count()

        if users_with_role > 0:
            messages.error(request, f'Cannot delete role "{role_name}" because it is assigned to {users_with_role} user(s).')
        else:
            # Log the action before deletion
            AuditLog.objects.create(
                user=request.user,
                action='delete',
                details={
                    'role_name': role_name,
                    'permissions': list(role.permissions.values_list('name', flat=True))
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                timestamp=timezone.now()
            )

            role.delete()
            messages.success(request, f'Role "{role_name}" deleted successfully.')

        return redirect('accounts:role_management')

    context = {
        'role': role,
        'users_with_role': role.customuser_roles.count(),
        'page_title': f'Delete Role: {role.name}',
        'active_nav': 'role_management',
    }
    return render(request, 'accounts/delete_role.html', context)


@login_required
@user_passes_test(is_admin)
def user_privileges(request, user_id):
    """View for managing user privileges (role assignments)"""
    target_user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = UserRoleAssignmentForm(request.POST, instance=target_user)
        if form.is_valid():
            old_roles = list(target_user.roles.values_list('name', flat=True))
            form.save()
            new_roles = list(target_user.roles.values_list('name', flat=True))

            # Log the action
            AuditLog.objects.create(
                user=request.user,
                target_user=target_user,
                action='privilege_change',
                details={
                    'old_roles': old_roles,
                    'new_roles': new_roles
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                timestamp=timezone.now()
            )

            messages.success(request, f'Privileges updated for user "{target_user.get_full_name()}".')
            return redirect('accounts:user_dashboard')
    else:
        form = UserRoleAssignmentForm(instance=target_user)

    context = {
        'form': form,
        'target_user': target_user,
        'page_title': f'Manage Privileges: {target_user.get_full_name()}',
        'active_nav': 'user_dashboard',
    }
    return render(request, 'accounts/user_privileges.html', context)


@login_required
@user_passes_test(is_admin)
def bulk_user_actions(request):
    """View for performing bulk actions on users"""
    if request.method == 'POST':
        form = BulkUserActionForm(request.POST)
        selected_users = request.POST.getlist('selected_users')

        if form.is_valid() and selected_users:
            action = form.cleaned_data['action']
            role = form.cleaned_data.get('role')

            users = User.objects.filter(id__in=selected_users)
            affected_count = users.count()

            if action == 'activate':
                users.update(is_active=True)
                messages.success(request, f'Activated {affected_count} user(s).')

            elif action == 'deactivate':
                users.update(is_active=False)
                messages.success(request, f'Deactivated {affected_count} user(s).')

            elif action == 'assign_role' and role:
                for user in users:
                    user.roles.add(role)
                messages.success(request, f'Assigned role "{role.name}" to {affected_count} user(s).')

            elif action == 'remove_role' and role:
                for user in users:
                    user.roles.remove(role)
                messages.success(request, f'Removed role "{role.name}" from {affected_count} user(s).')

            elif action == 'delete':
                # Don't allow deletion of superusers or current user
                safe_users = users.exclude(is_superuser=True).exclude(id=request.user.id)
                deleted_count = safe_users.count()
                safe_users.delete()
                messages.success(request, f'Deleted {deleted_count} user(s).')

            # Log the bulk action
            AuditLog.objects.create(
                user=request.user,
                action='user_bulk_action',
                details={
                    'action': action,
                    'affected_users': affected_count,
                    'role': role.name if role else None
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                timestamp=timezone.now()
            )

        else:
            messages.error(request, 'Please select users and provide valid action details.')

    return redirect('accounts:user_dashboard')


@login_required
@user_passes_test(is_admin)
def permission_management(request):
    """View for managing permissions"""
    from django.contrib.auth.models import Permission

    form = PermissionFilterForm(request.GET)
    permissions = Permission.objects.select_related('content_type').order_by(
        'content_type__app_label', 'content_type__model', 'codename'
    )

    if form.is_valid():
        content_type = form.cleaned_data.get('content_type')
        search = form.cleaned_data.get('search')

        if content_type:
            permissions = permissions.filter(content_type=content_type)

        if search:
            permissions = permissions.filter(
                Q(name__icontains=search) |
                Q(codename__icontains=search) |
                Q(content_type__model__icontains=search)
            )

    # Group permissions by content type
    grouped_permissions = {}
    for permission in permissions:
        app_model = f"{permission.content_type.app_label}.{permission.content_type.model}"
        if app_model not in grouped_permissions:
            grouped_permissions[app_model] = []
        grouped_permissions[app_model].append(permission)

    context = {
        'form': form,
        'grouped_permissions': grouped_permissions,
        'page_title': 'Permission Management',
        'active_nav': 'permission_management',
    }
    return render(request, 'accounts/permission_management.html', context)


@login_required
@user_passes_test(is_admin)
def audit_logs(request):
    """View for displaying audit logs"""
    logs = AuditLog.objects.select_related('user', 'target_user').order_by('-timestamp')

    # Filter by action type
    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action=action_filter)

    # Filter by user
    user_filter = request.GET.get('user')
    if user_filter:
        logs = logs.filter(user_id=user_filter)

    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)

    # Pagination
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Debugging: Print details of each log entry
    for log_entry in page_obj:
        print(f"Audit Log ID: {log_entry.id}, Details: {log_entry.details}")

    context = {
        'page_obj': page_obj,
        'action_choices': AuditLog.ACTION_CHOICES,
        'users': User.objects.filter(is_active=True).order_by('username'),
        'page_title': 'Audit Logs',
        'active_nav': 'audit_logs',
    }
    return render(request, 'accounts/audit_logs.html', context)


@login_required
@user_passes_test(is_admin)
def role_demo(request):
    """Demo view showing the role system in action"""
    # Get all roles with user counts
    roles = Role.objects.annotate(
        user_count=Count('customuser_roles')
    ).prefetch_related('permissions', 'customuser_roles__profile')

    # Get users by role
    users_by_role = {}
    for role in roles:
        users_by_role[role.name] = role.customuser_roles.select_related('profile').all()

    # Get role statistics
    total_roles = roles.count()
    total_users = User.objects.count()
    users_with_roles = User.objects.filter(roles__isnull=False).distinct().count()
    users_without_roles = total_users - users_with_roles

    # Get permission statistics
    total_permissions = Permission.objects.count()
    permissions_in_use = Permission.objects.filter(role__isnull=False).distinct().count()

    context = {
        'roles': roles,
        'users_by_role': users_by_role,
        'total_roles': total_roles,
        'total_users': total_users,
        'users_with_roles': users_with_roles,
        'users_without_roles': users_without_roles,
        'total_permissions': total_permissions,
        'permissions_in_use': permissions_in_use,
        'page_title': 'HMS Role System Demo',
        'active_nav': 'role_demo',
    }
    return render(request, 'accounts/role_demo.html', context)