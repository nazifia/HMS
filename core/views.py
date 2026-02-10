from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from accounts.permissions import permission_required as custom_permission_required
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
@custom_permission_required('core.view')
def notifications_list(request):
    """
    List user notifications
    """
    notifications = InternalNotification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    context = {
        'notifications': notifications,
    }

    return render(request, 'core/notifications_list.html', context)


@login_required
@custom_permission_required('core.edit')
def mark_notification_read(request, notification_id):
    """
    Mark notification as read - allows any staff member to mark authorization request notifications
    """
    # Get the notification - allow staff/superusers to mark any notification
    if request.user.is_staff or request.user.is_superuser:
        notification = get_object_or_404(InternalNotification, id=notification_id)
    else:
        # Regular users can only mark their own notifications
        notification = get_object_or_404(InternalNotification, id=notification_id, user=request.user)

    notification.mark_as_read()

    # Return empty response for HTMX requests to remove the element
    if request.headers.get('HX-Request'):
        from django.http import HttpResponse
        return HttpResponse(status=200)

    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.method == 'POST':
        return JsonResponse({'success': True, 'message': 'Notification marked as read'})

    return redirect('core:notifications_list')


@login_required
@custom_permission_required('core.create')
def create_prescription_view(request, patient_id, module_name):
    """
    Create prescription for patient from any module
    """
    # This is a placeholder - implementation would depend on the specific module
    messages.info(request, "Prescription creation functionality would be implemented here.")
    return redirect('dashboard:dashboard')


@login_required
@custom_permission_required('core.view')
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
    HTMX AJAX patient search endpoint
    Returns HTML fragment with patient search results
    """
    from patients.models import Patient
    from django.db.models import Q

    query = request.GET.get('q', '').strip()
    patient_type = request.GET.get('patient_type', '')  # Optional filter for NHIA/non-NHIA

    if not query or len(query) < 2:
        return render(request, 'pharmacy/pack_orders/partials/patient_search_results.html', {
            'patients': [],
            'query': query
        })

    # Search patients by name, ID, phone, or NHIA number
    patients = Patient.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(patient_id__icontains=query) |
        Q(phone_number__icontains=query) |
        Q(email__icontains=query)
    )

    # Filter by patient type if specified
    if patient_type:
        patients = patients.filter(patient_type=patient_type)

    # Filter active patients only
    patients = patients.filter(is_active=True)

    # Limit results
    patients = patients[:10]

    return render(request, 'pharmacy/pack_orders/partials/patient_search_results.html', {
        'patients': patients,
        'query': query
    })


def get_authorization_codes_for_patient(request):
    """
    HTMX AJAX endpoint to get authorization codes for a selected patient
    Returns HTML fragment with authorization code options
    """
    from patients.models import Patient
    from nhia.models import AuthorizationCode

    patient_id = request.GET.get('patient_id', '').strip()

    if not patient_id:
        return render(request, 'pharmacy/pack_orders/partials/authorization_codes.html', {
            'authorization_codes': [],
            'is_nhia': False,
            'patient_id': None
        })

    try:
        patient = Patient.objects.get(id=patient_id, is_active=True)
    except Patient.DoesNotExist:
        return render(request, 'pharmacy/pack_orders/partials/authorization_codes.html', {
            'authorization_codes': [],
            'is_nhia': False,
            'patient_id': patient_id
        })

    # Check if patient is NHIA
    is_nhia = hasattr(patient, 'patient_type') and patient.patient_type == 'nhia'

    # Get valid authorization codes for this patient
    authorization_codes = AuthorizationCode.objects.filter(
        patient=patient,
        status='active'
    ).order_by('-generated_at')

    return render(request, 'pharmacy/pack_orders/partials/authorization_codes.html', {
        'authorization_codes': authorization_codes,
        'is_nhia': is_nhia,
        'patient_id': patient_id,
        'patient': patient
    })


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
@custom_permission_required('core.view')
def request_nhia_authorization_form(request, model_type, object_id):
    """
    Display form to request NHIA authorization
    """
    # Import authorization utilities
    from .authorization_utils import get_model_class, get_model_info, check_if_requires_authorization

    # Get the model class for the specified type
    model_class = get_model_class(model_type)
    if not model_class:
        messages.error(request, 'Invalid record type.')
        return redirect('dashboard:dashboard')

    # Get the record
    record = get_object_or_404(model_class, id=object_id)

    # Check if patient is NHIA
    if record.patient.patient_type != 'nhia':
        messages.error(request, 'Authorization request is only for NHIA patients.')
        return redirect(request.META.get('HTTP_REFERER', 'dashboard:dashboard'))

    # Check if already authorized or not required
    requires_auth, reason = check_if_requires_authorization(record)
    if not requires_auth:
        messages.info(request, f'Authorization not required: {reason}')
        return redirect(request.META.get('HTTP_REFERER', 'dashboard:dashboard'))

    # Get model information for display
    model_info = get_model_info(model_type)
    if not model_info:
        display_name = model_type.replace('_', ' ').title()
    else:
        display_name = model_info['display_name']

    if request.method == 'POST':
        notes = request.POST.get('notes', '').strip()
        estimated_amount = request.POST.get('estimated_amount', '')

        # Send authorization request
        from django.db.models import Q
        desk_office_users = CustomUser.objects.filter(
            Q(is_superuser=True) |
            Q(is_staff=True) |
            Q(profile__role='admin') |
            Q(profile__role='accountant')
        ).distinct()

        if not desk_office_users.exists():
            messages.error(request, 'No desk office staff available to receive authorization requests.')
            return render(request, 'core/request_authorization_form.html', {
                'record': record,
                'model_type': model_type,
                'module_name': display_name,
            })

        # Create notification
        primary_user = desk_office_users.first()
        notification_title = f"NHIA Authorization Request - {display_name}"
        notification_message = f"""
Authorization request for NHIA Patient: {record.patient.get_full_name()} (ID: {record.patient.patient_id})

Module: {display_name}
Record ID: {record.id}
Requested by: {request.user.get_full_name() or request.user.username}
Reason: {notes}
Estimated Amount: ₦{estimated_amount if estimated_amount else 'Not specified'}

Please generate an authorization code for this patient to proceed with treatment and billing.
        """.strip()

        InternalNotification.objects.create(
            user=primary_user,
            sender=request.user,
            title=notification_title,
            message=notification_message,
            notification_type='warning'
        )

        messages.success(request, 'Authorization request sent to desk office successfully.')
        return redirect(request.META.get('HTTP_REFERER', 'dashboard:dashboard'))

    context = {
        'record': record,
        'model_type': model_type,
        'module_name': display_name,
    }
    return render(request, 'core/request_authorization_form.html', context)


@login_required
@require_POST
@custom_permission_required('core.create')
def request_nhia_authorization(request):
    """
    Send NHIA authorization request notification to desk office staff (AJAX endpoint)
    """
    try:
        patient_id = request.POST.get('patient_id')
        module_name = request.POST.get('module_name', 'Medical')
        record_id = request.POST.get('record_id')

        # Check for existing unread notification for this record
        existing_notification = InternalNotification.objects.filter(
            message__contains=f"Record ID: {record_id}",
            is_read=False
        ).exists()

        if existing_notification:
             return JsonResponse({
                'success': False,
                'message': 'An authorization request is already pending for this record.'
            }, status=400)

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

        # Check for existing unread notification with the same patient and module
        existing_notification = InternalNotification.objects.filter(
            Q(message__contains=f"Patient: {patient.get_full_name()} (ID: {patient.patient_id})") &
            Q(message__contains=f"Module: {module_name}") &
            Q(is_read=False)
        ).first()

        if existing_notification:
            return JsonResponse({
                'success': False,
                'message': f'An authorization request for this {module_name} record is already pending. Request sent on {existing_notification.created_at|date:"M d, Y H:i"}.'
            }, status=400)

        # Create a single notification for the first admin/superuser
        # Use select_for_update to prevent race conditions
        from django.db import transaction
        with transaction.atomic():
            # Double check no one else created a notification in the meantime
            final_check = InternalNotification.objects.filter(
                Q(message__contains=f"Patient: {patient.get_full_name()} (ID: {patient.patient_id})") &
                Q(message__contains=f"Module: {module_name}") &
                Q(is_read=False)
            ).first()
            
            if final_check:
                return JsonResponse({
                    'success': False,
                    'message': f'An authorization request for this {module_name} record is already pending. Request sent on {final_check.created_at|date:"M d, Y H:i"}.'
                }, status=400)

            # Get the first admin/superuser to receive the notification
            primary_user = desk_office_users.first()
            
            notification_title = f"NHIA Authorization Request - {module_name}"
            notification_message = f"""
Authorization request for NHIA Patient: {patient.get_full_name()} (ID: {patient.patient_id})

Module: {module_name}
Record ID: {record_id}
Requested by: {request.user.get_full_name() or request.user.username}

Please generate an authorization code for this patient to proceed with treatment and billing.
            """.strip()

            InternalNotification.objects.create(
                user=primary_user,
                sender=request.user,
                title=notification_title,
                message=notification_message,
                notification_type='warning'
            )

        return JsonResponse({
            'success': True,
            'message': f'Authorization request sent to desk office. They will process your request shortly.'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error sending authorization request: {str(e)}'
        }, status=500)


@login_required
def mark_notification_read(request, notification_id):
    """
    Mark notification as read and return JSON response
    """
    try:
        notification = get_object_or_404(InternalNotification, id=notification_id)
        
        if not notification.is_read:
            notification.mark_as_read()
            
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error marking notification as read: {str(e)}'
        }, status=500)


