from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from accounts.models import Role, CustomUser
from patients.models import Patient
from .models import InternalNotification


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
@require_POST
def request_nhia_authorization(request):
    """
    Send NHIA authorization request notification to desk office staff
    """
    try:
        patient_id = request.POST.get('patient_id')
        module_name = request.POST.get('module_name', 'Medical')
        record_id = request.POST.get('record_id')

        # Validate patient
        try:
            patient = Patient.objects.get(id=patient_id, patient_type='nhia')
        except Patient.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid patient or patient is not registered under NHIA.'
            }, status=400)

        # Get all admin users and superusers (desk office staff)
        desk_office_users = CustomUser.objects.filter(
            Q(is_superuser=True) |
            Q(is_staff=True) |
            Q(profile__role='admin') |
            Q(profile__role='accountant')
        ).distinct()

        if not desk_office_users.exists():
            return JsonResponse({
                'success': False,
                'message': 'No desk office staff available to receive authorization requests.'
            }, status=400)

        # Create notifications for all desk office staff
        notification_title = f"NHIA Authorization Request - {module_name}"
        notification_message = f"""
Authorization request for NHIA patient: {patient.get_full_name()} (ID: {patient.patient_id})

Module: {module_name}
Record ID: {record_id}
Requested by: {request.user.get_full_name() or request.user.username}

Please generate an authorization code for this patient to proceed with treatment and billing.
        """.strip()

        notifications_created = 0
        for user in desk_office_users:
            InternalNotification.objects.create(
                user=user,
                sender=request.user,
                title=notification_title,
                message=notification_message,
                notification_type='warning'
            )
            notifications_created += 1

        return JsonResponse({
            'success': True,
            'message': f'Authorization request sent to {notifications_created} desk office staff member(s). They will process your request shortly.'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error sending authorization request: {str(e)}'
        }, status=500)


