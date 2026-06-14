"""
Management views for reception/records Service Points.

Admins define service points (reception, records, triage, billing desks) and
assign staff to one or more of them. Patients are registered at a point and
routed from it to a physician.
"""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import CustomUser

from .models import ServicePoint


class ServicePointForm(forms.ModelForm):
    class Meta:
        model = ServicePoint
        fields = ['name', 'point_type', 'location', 'description', 'staff', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'point_type': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'staff': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 10}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['staff'].queryset = CustomUser.objects.filter(is_active=True).order_by('username')
        self.fields['staff'].required = False


def _can_manage(user):
    return user.is_superuser or (
        hasattr(user, 'profile') and user.profile and user.profile.role in ('admin', 'health_record_officer')
    )


@login_required
def service_point_list(request):
    points = ServicePoint.objects.prefetch_related('staff').all()
    return render(request, 'core/service_point_list.html', {
        'service_points': points,
        'can_manage': _can_manage(request.user),
        'page_title': 'Service Points',
    })


@login_required
def service_point_create(request):
    if not _can_manage(request.user):
        messages.error(request, 'You do not have permission to manage service points.')
        return redirect('core:service_point_list')

    if request.method == 'POST':
        form = ServicePointForm(request.POST)
        if form.is_valid():
            point = form.save()
            messages.success(request, f"Service point '{point.name}' created.")
            return redirect('core:service_point_list')
    else:
        form = ServicePointForm()
    return render(request, 'core/service_point_form.html', {
        'form': form,
        'page_title': 'Create Service Point',
    })


@login_required
def service_point_edit(request, pk):
    if not _can_manage(request.user):
        messages.error(request, 'You do not have permission to manage service points.')
        return redirect('core:service_point_list')

    point = get_object_or_404(ServicePoint, pk=pk)
    if request.method == 'POST':
        form = ServicePointForm(request.POST, instance=point)
        if form.is_valid():
            form.save()
            messages.success(request, f"Service point '{point.name}' updated.")
            return redirect('core:service_point_list')
    else:
        form = ServicePointForm(instance=point)
    return render(request, 'core/service_point_form.html', {
        'form': form,
        'service_point': point,
        'page_title': f'Edit {point.name}',
    })
