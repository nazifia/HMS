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

# Roles that work at a service point and must select one after login.
SERVICE_POINT_ROLES = (
    'receptionist',
    'health_record_officer',
    'accountant',
    'cashier_accountant',
)


def require_service_point(request):
    """
    For views that record a service point (registration, routing): if the user
    is desk staff with assigned points but hasn't signed in at one, return a
    redirect to the selector (preserving the current URL as next); else None.
    """
    if request.session.get('selected_service_point_id') or request.user.is_superuser:
        return None
    role = getattr(getattr(request.user, 'profile', None), 'role', None)
    if role not in SERVICE_POINT_ROLES:
        return None
    if not request.user.service_points.filter(is_active=True).exists():
        return None
    from urllib.parse import quote
    from django.urls import reverse
    messages.info(request, 'Select your service point to continue.')
    return redirect(f"{reverse('core:select_service_point')}?next={quote(request.get_full_path())}")


def service_point_required(view_func):
    """Decorator: desk staff must sign in at a service point before this view."""
    from functools import wraps

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        desk_redirect = require_service_point(request)
        if desk_redirect:
            return desk_redirect
        return view_func(request, *args, **kwargs)

    return wrapper


def get_selected_service_point(request):
    """Return the ServicePoint stored in the session, or None."""
    point_id = request.session.get('selected_service_point_id')
    if not point_id:
        return None
    try:
        return ServicePoint.objects.get(id=point_id, is_active=True)
    except ServicePoint.DoesNotExist:
        request.session.pop('selected_service_point_id', None)
        request.session.pop('selected_service_point_name', None)
        return None


def set_session_service_point(request, point):
    request.session['selected_service_point_id'] = point.id
    request.session['selected_service_point_name'] = point.name


@login_required
def select_service_point(request):
    """
    Post-login desk selection for reception/records/billing staff.

    GET: show assigned points (auto-select when exactly one).
    POST: store the chosen point in the session.
    """
    if request.user.is_superuser:
        points = ServicePoint.objects.filter(is_active=True)
    else:
        points = request.user.service_points.filter(is_active=True)
    points = points.select_related('department')

    next_url = request.GET.get('next') or request.POST.get('next') or ''

    if not points.exists():
        messages.warning(
            request,
            'You are not assigned to any service point. '
            'Contact an administrator to be assigned to one.',
        )
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        point = points.filter(id=request.POST.get('service_point_id')).first()
        if point is None:
            messages.error(request, 'Invalid service point selected.')
        else:
            set_session_service_point(request, point)
            messages.success(request, f"You are now working at '{point.name}'.")
            from django.utils.http import url_has_allowed_host_and_scheme
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect('dashboard:dashboard')

    # Auto-select when the user has exactly one point and none chosen yet.
    if points.count() == 1 and not request.session.get('selected_service_point_id'):
        point = points.first()
        set_session_service_point(request, point)
        messages.success(request, f"Automatically signed in at '{point.name}'.")
        return redirect(next_url or 'dashboard:dashboard')

    return render(request, 'core/select_service_point.html', {
        'service_points': points,
        'current_selection': get_selected_service_point(request),
        'next': next_url,
        'page_title': 'Select Service Point',
    })


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
