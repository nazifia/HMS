from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from .models import HMSPermission, RolePermissionAssignment, UserPermissionAssignment, SidebarMenuItem, FeatureFlag
from accounts.models import Role, CustomUser
from .forms import HMSPermissionForm, RolePermissionAssignmentForm, UserPermissionAssignmentForm


def home_view(request):
    """
    Home page view - redirects authenticated users to dashboard or shows login
    """
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    else:
        return redirect('accounts:login')


@login_required
def notifications_list(request):
    """
    List user notifications
    """
    notifications = request.user.notifications.all().order_by('-created_at')
    
    context = {
        'notifications': notifications,
    }
    
    return render(request, 'core/notifications_list.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """
    Mark notification as read
    """
    notification = get_object_or_404(
        request.user.notifications,
        id=notification_id
    )
    notification.mark_as_read()
    
    return redirect('core:notifications_list')


@login_required
def create_prescription_view(request, patient_id, module_name):
    """
    Create prescription for patient from any module
    """
    # This is a placeholder - implementation would depend on the specific module
    messages.info(request, "Prescription creation functionality would be implemented here.")
    return redirect('dashboard:dashboard')


@login_required
def patient_prescriptions_view(request, patient_id):
    """
    View patient prescriptions
    """
    # This is a placeholder - implementation would depend on existing prescription system
    messages.info(request, "Patient prescriptions functionality would be implemented here.")
    return redirect('dashboard:dashboard')


def medication_autocomplete_view(request):
    """
    Autocomplete for medications
    """
    # This is a placeholder - implementation would depend on existing medication system
    return JsonResponse({'results': []})


def search_patients(request):
    """
    Search patients - placeholder for existing functionality
    """
    # This would integrate with existing patient search
    messages.info(request, "Patient search functionality would be integrated here.")
    return redirect('dashboard:dashboard')


def patient_search_ajax(request):
    """
    AJAX patient search - placeholder for existing functionality
    """
    # This would integrate with existing patient search
    return JsonResponse({'results': []})


def test_url_helpers(request):
    """
    Test URL helpers functionality
    """
    messages.info(request, "URL helpers test functionality.")
    return redirect('dashboard:dashboard')


def test_performance(request):
    """
    Test performance functionality
    """
    messages.info(request, "Performance test functionality.")
    return redirect('dashboard:dashboard')


@login_required
@permission_required('core.view_hmspermission', 'core.manage_permissions')
def permission_management_dashboard(request):
    """
    HMS Custom Permission Management Dashboard
    """
    context = {
        'total_permissions': HMSPermission.objects.count(),
        'active_permissions': HMSPermission.objects.filter(is_active=True).count(),
        'total_roles': Role.objects.count(),
        'total_role_assignments': RolePermissionAssignment.objects.count(),
        'total_user_assignments': UserPermissionAssignment.objects.count(),
        'sidebar_items': SidebarMenuItem.objects.filter(is_active=True).count(),
        'feature_flags': FeatureFlag.objects.count(),
        'enabled_features': FeatureFlag.objects.filter(is_enabled=True).count(),
    }
    
    # Permission distribution by category
    context['permissions_by_category'] = HMSPermission.objects.values(
        'category'
    ).annotate(
        count=models.Count('id')
    ).order_by('category')
    
    return render(request, 'core/permission_management_dashboard.html', context)


@login_required
@permission_required('core.view_hmspermission')
def hms_permission_list(request):
    """
    List all HMS Custom Permissions
    """
    permissions = HMSPermission.objects.all().order_by('category', 'display_name')
    
    # Filter by category if specified
    category_filter = request.GET.get('category')
    if category_filter:
        permissions = permissions.filter(category=category_filter)
    
    # Filter by active status
    active_filter = request.GET.get('active')
    if active_filter == 'true':
        permissions = permissions.filter(is_active=True)
    elif active_filter == 'false':
        permissions = permissions.filter(is_active=False)
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        permissions = permissions.filter(
            models.Q(name__icontains=search_query) |
            models.Q(display_name__icontains=search_query) |
            models.Q(codename__icontains=search_query)
        )
    
    paginator = Paginator(permissions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': HMSPermission.PERMISSION_CATEGORIES,
        'current_category': category_filter,
        'current_active': active_filter,
        'search_query': search_query,
    }
    
    return render(request, 'core/hms_permission_list.html', context)


@login_required
@permission_required('core.add_hmspermission')
def hms_permission_create(request):
    """
    Create new HMS Custom Permission
    """
    if request.method == 'POST':
        form = HMSPermissionForm(request.POST)
        if form.is_valid():
            permission = form.save()
            messages.success(request, f'Permission "{permission.display_name}" created successfully.')
            return redirect('core:hms_permission_list')
    else:
        form = HMSPermissionForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    
    return render(request, 'core/hms_permission_form.html', context)


@login_required
@permission_required('core.change_hmspermission')
def hms_permission_edit(request, pk):
    """
    Edit existing HMS Custom Permission
    """
    permission = get_object_or_404(HMSPermission, pk=pk)
    
    if request.method == 'POST':
        form = HMSPermissionForm(request.POST, instance=permission)
        if form.is_valid():
            permission = form.save()
            messages.success(request, f'Permission "{permission.display_name}" updated successfully.')
            return redirect('core:hms_permission_list')
    else:
        form = HMSPermissionForm(instance=permission)
    
    context = {
        'form': form,
        'permission': permission,
        'action': 'Edit',
    }
    
    return render(request, 'core/hms_permission_form.html', context)


@login_required
@permission_required('core.delete_hmspermission')
def hms_permission_delete(request, pk):
    """
    Delete HMS Custom Permission
    """
    permission = get_object_or_404(HMSPermission, pk=pk)
    
    if request.method == 'POST':
        permission_name = permission.display_name
        permission.delete()
        messages.success(request, f'Permission "{permission_name}" deleted successfully.')
        return redirect('core:hms_permission_list')
    
    context = {
        'permission': permission,
    }
    
    return render(request, 'core/hms_permission_confirm_delete.html', context)


@login_required
@permission_required('core.view_rolepermissionassignment')
def role_permission_assignments(request):
    """
    Manage role-to-permission assignments
    """
    assignments = RolePermissionAssignment.objects.select_related(
        'role', 'permission', 'granted_by'
    ).order_by('-granted_at')
    
    # Filter by role
    role_filter = request.GET.get('role')
    if role_filter:
        assignments = assignments.filter(role_id=role_filter)
    
    # Filter by permission
    permission_filter = request.GET.get('permission')
    if permission_filter:
        assignments = assignments.filter(permission_id=permission_filter)
    
    paginator = Paginator(assignments, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'roles': Role.objects.all().order_by('name'),
        'permissions': HMSPermission.objects.filter(is_active=True).order_by('display_name'),
        'current_role': role_filter,
        'current_permission': permission_filter,
    }
    
    return render(request, 'core/role_permission_assignments.html', context)


@login_required
@permission_required('core.add_rolepermissionassignment')
def assign_role_permission(request):
    """
    Assign permission to role
    """
    if request.method == 'POST':
        form = RolePermissionAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.granted_by = request.user
            assignment.save()
            
            messages.success(request, 
                f'Permission "{assignment.permission.display_name}" assigned to role "{assignment.role.name}" successfully.')
            return redirect('core:role_permission_assignments')
    else:
        form = RolePermissionAssignmentForm()
    
    context = {
        'form': form,
        'action': 'Assign',
    }
    
    return render(request, 'core/role_permission_assignment_form.html', context)


@login_required
@permission_required('core.delete_rolepermissionassignment')
def remove_role_permission(request, pk):
    """
    Remove permission from role
    """
    assignment = get_object_or_404(RolePermissionAssignment, pk=pk)
    
    if request.method == 'POST':
        permission_name = assignment.permission.display_name
        role_name = assignment.role.name
        assignment.delete()
        messages.success(request, 
            f'Permission "{permission_name}" removed from role "{role_name}" successfully.')
        return redirect('core:role_permission_assignments')
    
    context = {
        'assignment': assignment,
    }
    
    return render(request, 'core/role_permission_assignment_confirm_delete.html', context)


@login_required
@permission_required('core.view_userpermissionassignment')
def user_permission_assignments(request):
    """
    Manage user-to-permission assignments
    """
    assignments = UserPermissionAssignment.objects.select_related(
        'user', 'permission', 'granted_by'
    ).order_by('-granted_at')
    
    # Filter by user
    user_filter = request.GET.get('user')
    if user_filter:
        assignments = assignments.filter(user_id=user_filter)
    
    # Filter by permission
    permission_filter = request.GET.get('permission')
    if permission_filter:
        assignments = assignments.filter(permission_id=permission_filter)
    
    paginator = Paginator(assignments, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'users': CustomUser.objects.all().order_by('username'),
        'permissions': HMSPermission.objects.filter(is_active=True).order_by('display_name'),
        'current_user': user_filter,
        'current_permission': permission_filter,
    }
    
    return render(request, 'core/user_permission_assignments.html', context)


@login_required
@permission_required('core.add_userpermissionassignment')
def assign_user_permission(request):
    """
    Assign permission directly to user
    """
    if request.method == 'POST':
        form = UserPermissionAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.granted_by = request.user
            assignment.save()
            
            messages.success(request, 
                f'Permission "{assignment.permission.display_name}" assigned to user "{assignment.user.username}" successfully.')
            return redirect('core:user_permission_assignments')
    else:
        form = UserPermissionAssignmentForm()
    
    context = {
        'form': form,
        'action': 'Assign',
    }
    
    return render(request, 'core/user_permission_assignment_form.html', context)


@login_required
@permission_required('core.delete_userpermissionassignment')
def remove_user_permission(request, pk):
    """
    Remove permission from user
    """
    assignment = get_object_or_404(UserPermissionAssignment, pk=pk)
    
    if request.method == 'POST':
        permission_name = assignment.permission.display_name
        user_name = assignment.user.username
        assignment.delete()
        messages.success(request, 
            f'Permission "{permission_name}" removed from user "{user_name}" successfully.')
        return redirect('core:user_permission_assignments')
    
    context = {
        'assignment': assignment,
    }
    
    return render(request, 'core/user_permission_assignment_confirm_delete.html', context)


@login_required
@permission_required('core.view_sidebarmenuitem')
def sidebar_menu_management(request):
    """
    Manage sidebar menu items
    """
    menu_items = SidebarMenuItem.objects.all().order_by('category', 'order', 'title')
    
    context = {
        'menu_items': menu_items,
    }
    
    return render(request, 'core/sidebar_menu_management.html', context)


@login_required
@permission_required('core.view_featureflag')
def feature_flag_management(request):
    """
    Manage feature flags
    """
    feature_flags = FeatureFlag.objects.all().order_by('feature_type', 'display_name')
    
    context = {
        'feature_flags': feature_flags,
    }
    
    return render(request, 'core/feature_flag_management.html', context)


# AJAX views for dynamic permission checking
@login_required
def check_permission(request):
    """
    AJAX endpoint to check if user has specific permission
    """
    if request.method == 'GET':
        permission_name = request.GET.get('permission')
        if permission_name:
            from core.permissions import RolePermissionChecker
            checker = RolePermissionChecker(request.user)
            has_permission = checker.has_permission(permission_name)
            return JsonResponse({'has_permission': has_permission})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def get_user_permissions(request):
    """
    AJAX endpoint to get all user permissions
    """
    from core.permissions import RolePermissionChecker
    checker = RolePermissionChecker(request.user)
    user_permissions = list(checker.get_user_permissions())
    
    return JsonResponse({
        'permissions': user_permissions,
        'is_superuser': request.user.is_superuser,
    })


@login_required
@permission_required('core.change_hmspermission')
def bulk_permission_update(request):
    """
    Bulk update permissions for roles or users
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        permission_ids = request.POST.getlist('permission_ids')
        target_type = request.POST.get('target_type')
        target_ids = request.POST.getlist('target_ids')
        
        if action == 'assign' and permission_ids and target_type and target_ids:
            success_count = 0
            
            with transaction.atomic():
                for permission_id in permission_ids:
                    try:
                        permission = HMSPermission.objects.get(id=permission_id)
                        
                        for target_id in target_ids:
                            if target_type == 'role':
                                role = Role.objects.get(id=target_id)
                                RolePermissionAssignment.objects.get_or_create(
                                    role=role,
                                    permission=permission,
                                    defaults={'granted_by': request.user}
                                )
                            elif target_type == 'user':
                                user = CustomUser.objects.get(id=target_id)
                                UserPermissionAssignment.objects.get_or_create(
                                    user=user,
                                    permission=permission,
                                    defaults={'granted_by': request.user}
                                )
                        
                        success_count += 1
                    except (HMSPermission.DoesNotExist, Role.DoesNotExist, CustomUser.DoesNotExist):
                        continue
            
            messages.success(request, f'Successfully processed {success_count} permissions.')
            return redirect('core:permission_management_dashboard')
    
    context = {
        'roles': Role.objects.all().order_by('name'),
        'users': CustomUser.objects.all().order_by('username'),
        'permissions': HMSPermission.objects.filter(is_active=True).order_by('display_name'),
    }
    
    return render(request, 'core/bulk_permission_update.html', context)
