"""
Universal Authorization Request Views
Handles authorization requests from any module
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from django.db.models import Q
from .authorization_utils import (
    get_object_for_authorization,
    get_model_info,
    check_if_requires_authorization,
    get_authorization_status,
    create_authorization_request,
    generate_authorization_for_object,
    get_all_pending_authorizations,
    AUTHORIZATION_SUPPORTED_MODELS
)
from nhia.models import AuthorizationCode


@login_required
def request_authorization(request, model_type, object_id):
    """
    Universal view to request authorization for any object
    """
    # Get the object
    obj = get_object_for_authorization(model_type, object_id)
    if not obj:
        messages.error(request, 'Invalid request. Object not found.')
        return redirect('dashboard:dashboard')
    
    model_info = get_model_info(model_type)
    if not model_info:
        messages.error(request, 'Invalid model type.')
        return redirect('dashboard:dashboard')
    
    # Check if patient is NHIA
    if obj.patient.patient_type != 'nhia':
        messages.error(request, 'Authorization is only required for NHIA patients.')
        return redirect(request.META.get('HTTP_REFERER', 'dashboard:dashboard'))
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        estimated_amount = request.POST.get('estimated_amount', '')
        
        # Create authorization request
        success = create_authorization_request(obj, request.user, notes)
        
        if success:
            messages.success(
                request,
                f'Authorization request submitted successfully for {model_info["display_name"]} #{obj.id}. '
                'Desk office will process this request shortly.'
            )
        else:
            messages.error(request, 'Failed to create authorization request.')
        
        return redirect(request.META.get('HTTP_REFERER', 'dashboard:dashboard'))
    
    # GET request - show confirmation page
    context = {
        'object': obj,
        'model_type': model_type,
        'model_info': model_info,
        'page_title': f'Request Authorization - {model_info["display_name"]}',
    }
    return render(request, 'core/request_authorization.html', context)


@login_required
def generate_authorization(request, model_type, object_id):
    """
    Universal view to generate authorization code for any object
    Typically used by desk office staff
    Supports both auto-generated and manually input codes
    """
    # Get the object
    obj = get_object_for_authorization(model_type, object_id)
    if not obj:
        messages.error(request, 'Invalid request. Object not found.')
        return redirect('desk_office:authorization_dashboard')

    model_info = get_model_info(model_type)
    if not model_info:
        messages.error(request, 'Invalid model type.')
        return redirect('desk_office:authorization_dashboard')

    # Check if patient is NHIA
    if obj.patient.patient_type != 'nhia':
        messages.error(request, 'Authorization is only required for NHIA patients.')
        return redirect(request.META.get('HTTP_REFERER', 'desk_office:authorization_dashboard'))

    if request.method == 'POST':
        amount = request.POST.get('amount', '0.00')
        expiry_days = int(request.POST.get('expiry_days', '30'))
        notes = request.POST.get('notes', '')
        code_type = request.POST.get('code_type', 'auto')  # 'auto' or 'manual'
        manual_code = request.POST.get('manual_code', '').strip().upper()

        try:
            amount = float(amount)
        except ValueError:
            amount = 0.00

        # Handle manual code input
        if code_type == 'manual':
            if not manual_code:
                messages.error(request, 'Please enter a manual authorization code.')
                context = {
                    'object': obj,
                    'model_type': model_type,
                    'model_info': model_info,
                    'page_title': f'Generate Authorization - {model_info["display_name"]}',
                    'form_data': request.POST,
                }
                return render(request, 'core/generate_authorization.html', context)

            # Check if manual code already exists
            if AuthorizationCode.objects.filter(code=manual_code).exists():
                messages.error(
                    request,
                    f'Authorization code "{manual_code}" already exists. Please use a different code.'
                )
                context = {
                    'object': obj,
                    'model_type': model_type,
                    'model_info': model_info,
                    'page_title': f'Generate Authorization - {model_info["display_name"]}',
                    'form_data': request.POST,
                }
                return render(request, 'core/generate_authorization.html', context)

            # Create authorization code with manual code
            from core.authorization_utils import generate_authorization_for_object
            auth_code, error = generate_authorization_for_object(
                obj, request.user, amount, expiry_days, notes, manual_code=manual_code
            )

            if auth_code:
                messages.success(
                    request,
                    f'Manual authorization code "{auth_code.code}" created successfully for '
                    f'{model_info["display_name"]} #{obj.id}.'
                )
                return redirect('desk_office:authorization_dashboard')
            else:
                messages.error(request, f'Failed to create authorization code: {error}')
        else:
            # Auto-generate authorization code
            auth_code, error = generate_authorization_for_object(
                obj, request.user, amount, expiry_days, notes
            )

            if auth_code:
                messages.success(
                    request,
                    f'Authorization code {auth_code.code} generated successfully for '
                    f'{model_info["display_name"]} #{obj.id}.'
                )
                return redirect('desk_office:authorization_dashboard')
            else:
                messages.error(request, f'Failed to generate authorization code: {error}')

    # GET request - show form
    context = {
        'object': obj,
        'model_type': model_type,
        'model_info': model_info,
        'page_title': f'Generate Authorization - {model_info["display_name"]}',
    }
    return render(request, 'core/generate_authorization.html', context)


@login_required
def universal_authorization_dashboard(request):
    """
    Universal dashboard showing all pending authorization requests across all modules
    """
    # Get all pending authorizations
    pending_items = get_all_pending_authorizations()
    
    # Calculate total count
    total_count = sum(item['count'] for item in pending_items.values())
    
    # Get recent authorization codes
    recent_codes = AuthorizationCode.objects.select_related('patient', 'generated_by').order_by('-generated_at')[:20]
    
    # Get statistics
    today = timezone.now().date()
    stats = {
        'total_pending': total_count,
        'today_generated': AuthorizationCode.objects.filter(generated_at__date=today).count(),
        'active_codes': AuthorizationCode.objects.filter(status='active').count(),
        'expired_codes': AuthorizationCode.objects.filter(status='expired').count(),
    }
    
    context = {
        'pending_items': pending_items,
        'recent_codes': recent_codes,
        'stats': stats,
        'page_title': 'Universal Authorization Dashboard',
        'active_nav': 'authorization',
    }
    
    return render(request, 'core/universal_authorization_dashboard.html', context)


@login_required
def check_authorization_status_ajax(request):
    """
    AJAX endpoint to check authorization status of an object
    """
    model_type = request.GET.get('model_type')
    object_id = request.GET.get('object_id')
    
    if not model_type or not object_id:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    obj = get_object_for_authorization(model_type, object_id)
    if not obj:
        return JsonResponse({'error': 'Object not found'}, status=404)
    
    requires_auth, reason = check_if_requires_authorization(obj)
    status = get_authorization_status(obj)
    
    data = {
        'requires_authorization': requires_auth,
        'reason': reason,
        'status': status,
        'patient_type': obj.patient.patient_type if hasattr(obj, 'patient') else None,
    }
    
    # Add authorization code details if available
    if hasattr(obj, 'authorization_code') and obj.authorization_code:
        if isinstance(obj.authorization_code, AuthorizationCode):
            data['authorization_code'] = {
                'code': obj.authorization_code.code,
                'amount': str(obj.authorization_code.amount),
                'expiry_date': obj.authorization_code.expiry_date.strftime('%Y-%m-%d'),
                'status': obj.authorization_code.status,
                'is_valid': obj.authorization_code.is_valid(),
            }
        else:
            data['authorization_code'] = {
                'code': str(obj.authorization_code),
            }
    
    return JsonResponse(data)


@login_required
def bulk_generate_authorization(request):
    """
    Generate authorization codes for multiple objects at once
    """
    if request.method != 'POST':
        return HttpResponseBadRequest('POST request required')
    
    items = request.POST.getlist('items[]')  # Format: "model_type:object_id"
    amount = request.POST.get('amount', '0.00')
    expiry_days = int(request.POST.get('expiry_days', '30'))
    notes = request.POST.get('notes', '')
    
    try:
        amount = float(amount)
    except ValueError:
        amount = 0.00
    
    generated_count = 0
    failed_count = 0
    
    for item in items:
        try:
            model_type, object_id = item.split(':')
            obj = get_object_for_authorization(model_type, int(object_id))
            
            if obj and obj.patient.patient_type == 'nhia':
                auth_code, error = generate_authorization_for_object(
                    obj, request.user, amount, expiry_days, notes
                )
                if auth_code:
                    generated_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1
        except (ValueError, AttributeError):
            failed_count += 1
    
    messages.success(
        request,
        f'Successfully generated {generated_count} authorization codes. '
        f'{failed_count} items failed.'
    )
    
    return redirect('core:universal_authorization_dashboard')


@login_required
def authorization_history(request, model_type, object_id):
    """
    View authorization history for a specific object
    """
    obj = get_object_for_authorization(model_type, object_id)
    if not obj:
        messages.error(request, 'Object not found.')
        return redirect('dashboard:dashboard')
    
    model_info = get_model_info(model_type)
    
    # Get all authorization codes for this patient related to this service type
    auth_codes = AuthorizationCode.objects.filter(
        patient=obj.patient,
        service_type=model_info['service_type']
    ).order_by('-generated_at')
    
    context = {
        'object': obj,
        'model_type': model_type,
        'model_info': model_info,
        'auth_codes': auth_codes,
        'page_title': f'Authorization History - {model_info["display_name"]}',
    }
    
    return render(request, 'core/authorization_history.html', context)

