"""
Management views for reception/records Service Points.

Admins define service points (reception, records, triage, billing desks) and
assign staff to one or more of them. Patients are registered at a point and
routed from it to a physician.

Department heads may also manage points, but only within the department(s)
they head: they cannot create hospital-wide points or touch other
departments' points.
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import CustomUser, Department

from .models import ServicePoint


class ServicePointForm(forms.ModelForm):
    class Meta:
        model = ServicePoint
        fields = ['name', 'point_type', 'department', 'location', 'description', 'staff', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'point_type': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'staff': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 10}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, departments=None, **kwargs):
        """`departments` limits the department choices (dept heads); None = all."""
        super().__init__(*args, **kwargs)
        self.fields['staff'].queryset = CustomUser.tenant_objects.filter(is_active=True).order_by('username')
        self.fields['staff'].required = False
        if departments is None:
            self.fields['department'].queryset = Department.objects.order_by('name')
            self.fields['department'].required = False
            self.fields['department'].empty_label = 'Hospital-wide (no department)'
        else:
            self.fields['department'].queryset = departments.order_by('name')
            self.fields['department'].required = True
            self.fields['department'].empty_label = None


def _can_manage(user):
    """Global managers: may manage any point, including hospital-wide ones."""
    return user.is_superuser or (
        hasattr(user, 'profile') and user.profile and user.profile.role in ('admin', 'health_record_officer')
    )


def _headed_departments(user):
    return Department.objects.filter(head=user)


def _can_manage_point(user, point):
    if _can_manage(user):
        return True
    return point.department_id is not None and point.department.head_id == user.id


@login_required
def service_point_list(request):
    points = ServicePoint.objects.select_related('department').prefetch_related('staff').all()
    headed_ids = set(_headed_departments(request.user).values_list('id', flat=True))
    return render(request, 'core/service_point_list.html', {
        'service_points': points,
        'can_manage': _can_manage(request.user),
        'headed_department_ids': headed_ids,
        'page_title': 'Service Points',
    })


@login_required
def service_point_create(request):
    is_global = _can_manage(request.user)
    headed = _headed_departments(request.user)
    if not is_global and not headed.exists():
        messages.error(request, 'You do not have permission to manage service points.')
        return redirect('core:service_point_list')

    departments = None if is_global else headed
    if request.method == 'POST':
        form = ServicePointForm(request.POST, departments=departments)
        if form.is_valid():
            point = form.save()
            messages.success(request, f"Service point '{point.name}' created.")
            return redirect('core:service_point_list')
    else:
        form = ServicePointForm(departments=departments)
    return render(request, 'core/service_point_form.html', {
        'form': form,
        'page_title': 'Create Service Point',
    })


@login_required
def service_point_edit(request, pk):
    point = get_object_or_404(ServicePoint.objects.select_related('department'), pk=pk)
    if not _can_manage_point(request.user, point):
        messages.error(request, 'You do not have permission to manage this service point.')
        return redirect('core:service_point_list')

    departments = None if _can_manage(request.user) else _headed_departments(request.user)
    if request.method == 'POST':
        form = ServicePointForm(request.POST, instance=point, departments=departments)
        if form.is_valid():
            form.save()
            messages.success(request, f"Service point '{point.name}' updated.")
            return redirect('core:service_point_list')
    else:
        form = ServicePointForm(instance=point, departments=departments)
    return render(request, 'core/service_point_form.html', {
        'form': form,
        'service_point': point,
        'page_title': f'Edit {point.name}',
    })
