"""
Views for UI Permission Management
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.core.paginator import Paginator

from core.models import UIPermission, PermissionGroup
from core.ui_permission_forms import (
    UIPermissionForm, PermissionGroupForm,
    BulkUIPermissionAssignForm, UIPermissionFilterForm,
    RoleUIPermissionForm
)
from accounts.models import Role
from accounts.permissions import permission_required, role_required


@login_required
@role_required(['admin'], raise_exception=True)
def ui_permission_dashboard(request):
    """Dashboard for UI permission management"""

    # Get statistics
    total_ui_permissions = UIPermission.objects.count()
    active_permissions = UIPermission.objects.filter(is_active=True).count()
    inactive_permissions = total_ui_permissions - active_permissions

    # Get permissions by module
    permissions_by_module = UIPermission.objects.values('module').annotate(
        count=Count('id')
    ).order_by('module')

    # Get permissions by type
    permissions_by_type = UIPermission.objects.values('element_type').annotate(
        count=Count('id')
    ).order_by('element_type')

    # Get recent UI permissions
    recent_permissions = UIPermission.objects.order_by('-created_at')[:10]

    context = {
        'total_ui_permissions': total_ui_permissions,
        'active_permissions': active_permissions,
        'inactive_permissions': inactive_permissions,
        'permissions_by_module': permissions_by_module,
        'permissions_by_type': permissions_by_type,
        'recent_permissions': recent_permissions,
    }

    return render(request, 'core/ui_permission_dashboard.html', context)


@login_required
@role_required(['admin'], raise_exception=True)
def ui_permission_list(request):
    """List all UI permissions with filtering"""

    # Get filter form
    filter_form = UIPermissionFilterForm(request.GET)

    # Start with all permissions
    ui_permissions = UIPermission.objects.all().prefetch_related(
        'required_permissions', 'required_roles'
    )

    # Apply filters
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('module'):
            ui_permissions = ui_permissions.filter(
                module=filter_form.cleaned_data['module']
            )

        if filter_form.cleaned_data.get('element_type'):
            ui_permissions = ui_permissions.filter(
                element_type=filter_form.cleaned_data['element_type']
            )

        if filter_form.cleaned_data.get('is_active'):
            is_active = filter_form.cleaned_data['is_active'] == 'true'
            ui_permissions = ui_permissions.filter(is_active=is_active)

        if filter_form.cleaned_data.get('search'):
            search = filter_form.cleaned_data['search']
            ui_permissions = ui_permissions.filter(
                Q(element_id__icontains=search) |
                Q(element_label__icontains=search) |
                Q(description__icontains=search)
            )

    # Order by module and display order
    ui_permissions = ui_permissions.order_by('module', 'display_order', 'element_label')

    # Pagination
    paginator = Paginator(ui_permissions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
    }

    return render(request, 'core/ui_permission_list.html', context)


@login_required
@role_required(['admin'], raise_exception=True)
def ui_permission_create(request):
    """Create a new UI permission"""

    if request.method == 'POST':
        form = UIPermissionForm(request.POST)
        if form.is_valid():
            ui_permission = form.save(commit=False)
            ui_permission.created_by = request.user
            ui_permission.save()
            form.save_m2m()  # Save many-to-many relationships

            messages.success(
                request,
                f'UI Permission "{ui_permission.element_label}" created successfully!'
            )
            return redirect('core:ui_permission_detail', pk=ui_permission.pk)
    else:
        form = UIPermissionForm()

    context = {
        'form': form,
        'action': 'Create',
    }

    return render(request, 'core/ui_permission_form.html', context)


@login_required
@role_required(['admin'], raise_exception=True)
def ui_permission_edit(request, pk):
    """Edit an existing UI permission"""

    ui_permission = get_object_or_404(UIPermission, pk=pk)

    if request.method == 'POST':
        form = UIPermissionForm(request.POST, instance=ui_permission)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'UI Permission "{ui_permission.element_label}" updated successfully!'
            )
            return redirect('core:ui_permission_detail', pk=ui_permission.pk)
    else:
        form = UIPermissionForm(instance=ui_permission)

    context = {
        'form': form,
        'ui_permission': ui_permission,
        'action': 'Edit',
    }

    return render(request, 'core/ui_permission_form.html', context)


@login_required
@role_required(['admin'], raise_exception=True)
def ui_permission_detail(request, pk):
    """View details of a UI permission"""

    ui_permission = get_object_or_404(
        UIPermission.objects.prefetch_related(
            'required_permissions', 'required_roles'
        ),
        pk=pk
    )

    # Get roles that have this permission
    roles_with_access = ui_permission.required_roles.all()

    context = {
        'ui_permission': ui_permission,
        'roles_with_access': roles_with_access,
    }

    return render(request, 'core/ui_permission_detail.html', context)


@login_required
@role_required(['admin'], raise_exception=True)
def ui_permission_delete(request, pk):
    """Delete a UI permission"""

    ui_permission = get_object_or_404(UIPermission, pk=pk)

    # Prevent deletion of system permissions
    if ui_permission.is_system:
        messages.error(
            request,
            'Cannot delete system UI permissions. You can deactivate it instead.'
        )
        return redirect('core:ui_permission_detail', pk=pk)

    if request.method == 'POST':
        element_label = ui_permission.element_label
        ui_permission.delete()
        messages.success(
            request,
            f'UI Permission "{element_label}" deleted successfully!'
        )
        return redirect('core:ui_permission_list')

    context = {
        'ui_permission': ui_permission,
    }

    return render(request, 'core/ui_permission_delete.html', context)


@login_required
@role_required(['admin'], raise_exception=True)
def ui_permission_toggle_active(request, pk):
    """Toggle active status of a UI permission"""

    ui_permission = get_object_or_404(UIPermission, pk=pk)
    ui_permission.is_active = not ui_permission.is_active
    ui_permission.save()

    status = 'activated' if ui_permission.is_active else 'deactivated'
    messages.success(
        request,
        f'UI Permission "{ui_permission.element_label}" {status} successfully!'
    )

    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_active': ui_permission.is_active,
            'message': f'Permission {status}',
        })

    return redirect('core:ui_permission_detail', pk=pk)


@login_required
@role_required(['admin'], raise_exception=True)
def role_ui_permissions(request, role_id):
    """Manage UI permissions for a specific role"""

    role = get_object_or_404(Role, pk=role_id)

    if request.method == 'POST':
        form = RoleUIPermissionForm(request.POST, role=role)
        if form.is_valid():
            # Clear existing UI permissions for this role
            role.ui_elements.clear()

            # Add selected UI permissions
            for field_name, ui_perms in form.cleaned_data.items():
                if field_name.startswith('module_') and ui_perms:
                    role.ui_elements.add(*ui_perms)

            messages.success(
                request,
                f'UI permissions for role "{role.name}" updated successfully!'
            )
            return redirect('accounts:role_detail', pk=role_id)
    else:
        form = RoleUIPermissionForm(role=role)

    # Get current permissions grouped by module
    current_permissions = role.ui_elements.all().order_by('module', 'display_order')

    context = {
        'role': role,
        'form': form,
        'current_permissions': current_permissions,
    }

    return render(request, 'core/role_ui_permissions.html', context)


@login_required
@role_required(['admin'], raise_exception=True)
def permission_group_list(request):
    """List all permission groups"""

    groups = PermissionGroup.objects.annotate(
        permission_count=Count('ui_permissions')
    ).order_by('module', 'name')

    context = {
        'groups': groups,
    }

    return render(request, 'core/permission_group_list.html', context)


@login_required
@role_required(['admin'], raise_exception=True)
def permission_group_create(request):
    """Create a new permission group"""

    if request.method == 'POST':
        form = PermissionGroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            messages.success(
                request,
                f'Permission Group "{group.name}" created successfully!'
            )
            return redirect('core:permission_group_list')
    else:
        form = PermissionGroupForm()

    context = {
        'form': form,
        'action': 'Create',
    }

    return render(request, 'core/permission_group_form.html', context)


@login_required
@role_required(['admin'], raise_exception=True)
def bulk_assign_permissions(request):
    """Bulk assign UI permissions to roles"""

    if request.method == 'POST':
        form = BulkUIPermissionAssignForm(request.POST)
        if form.is_valid():
            roles = form.cleaned_data['roles']
            ui_permissions = form.cleaned_data['ui_permissions']
            action = form.cleaned_data['action']

            for role in roles:
                if action == 'add':
                    role.ui_elements.add(*ui_permissions)
                elif action == 'remove':
                    role.ui_elements.remove(*ui_permissions)
                elif action == 'replace':
                    role.ui_elements.set(ui_permissions)

            messages.success(
                request,
                f'Bulk permission assignment completed for {roles.count()} roles!'
            )
            return redirect('core:ui_permission_dashboard')
    else:
        form = BulkUIPermissionAssignForm()

    context = {
        'form': form,
    }

    return render(request, 'core/bulk_assign_permissions.html', context)
