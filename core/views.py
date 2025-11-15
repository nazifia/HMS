from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from accounts.models import Role, CustomUser


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



