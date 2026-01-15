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
from consultations.models import Referral


def calculate_referral_estimated_cost(referral):
    """
    Calculate the estimated cost for a referral based on destination and type.
    
    Args:
        referral (Referral): The referral object to calculate cost for
        
    Returns:
        float: Estimated cost for the referral
    """
    # Base referral cost (same as used in bulk authorization)
    base_cost = 10000.00
    
    # Check if the referral has specific cost factors based on destination
    if referral.referred_to_department:
        # Department-specific pricing (can be expanded with actual pricing data)
        department_name = referral.referred_to_department.name.lower()
        
        # Specialty-specific pricing adjustments
        if department_name in ['surgery', 'theatre', 'operating']:
            # Surgical referrals typically have higher costs
            return 25000.00
        elif department_name in ['radiology', 'imaging', 'x-ray']:
            # Imaging referrals
            return 15000.00
        elif department_name in ['laboratory', 'lab', 'pathology']:
            # Lab referrals
            return 12000.00
        elif department_name in ['physiotherapy', 'rehabilitation']:
            # Physiotherapy referrals
            return 8000.00
        elif department_name in ['ophthalmic', 'ophthalmology', 'eye']:
            # Ophthalmic referrals
            return 18000.00
        elif department_name in ['dental', 'oral']:
            # Dental referrals
            return 10000.00
        elif department_name in ['neurology', 'neurosurgery']:
            # Neurology referrals
            return 20000.00
        elif department_name in ['oncology', 'cancer']:
            # Oncology referrals
            return 30000.00
        elif department_name in ['cardiology', 'heart']:
            # Cardiology referrals
            return 22000.00
        elif department_name in ['icu', 'intensive', 'critical']:
            # ICU referrals
            return 35000.00
        elif department_name in ['nhia', 'national health insurance']:
            # NHIA referrals (shouldn't normally require auth, but if they do)
            return 5000.00
    
    # Check for specialty-specific referrals
    if referral.referred_to_specialty:
        specialty = referral.referred_to_specialty.lower()
        if any(word in specialty for word in ['surgery', 'surgical', 'operative']):
            return 25000.00
        elif any(word in specialty for word in ['cardiology', 'heart']):
            return 22000.00
        elif any(word in specialty for word in ['neurology', 'neurosurgery', 'brain']):
            return 20000.00
        elif any(word in specialty for word in ['oncology', 'cancer', 'tumor']):
            return 30000.00
    
    # Default base cost for general referrals
    return base_cost


def calculate_test_request_estimated_cost(test_request):
    """
    Calculate the estimated cost for a test request based on the sum of all test prices.
    
    Args:
        test_request (TestRequest): The test request object to calculate cost for
        
    Returns:
        float: Estimated cost for the test request
    """
    # Sum up the prices of all tests in the request
    total_cost = 0.00
    
    if test_request.tests.exists():
        for test in test_request.tests.all():
            total_cost += float(test.price)
    
    return total_cost if total_cost > 0 else 5000.00  # Default minimum cost if no tests found


def calculate_prescription_authorization_amount(prescription):
    """
    Calculate the 10% patient portion for NHIA prescription authorization.
    This is the amount NHIA patients actually need to pay (10% of total cost).
    
    Args:
        prescription (Prescription): The prescription object to calculate amount for
        
    Returns:
        float: 10% of the total prescription cost for NHIA patients
    """
    # Import the prescription model dynamically
    from pharmacy.models import Prescription
    
    if not isinstance(prescription, Prescription):
        return 0.00
    
    # Use the prescription's built-in method to get the patient payable amount (10% for NHIA)
    try:
        patient_amount = prescription.get_patient_payable_amount()
        # Convert to float for compatibility
        return float(patient_amount) if patient_amount else 0.00
    except Exception:
        # Fallback calculation if method fails
        total_prescribed_price = 0.00
        for item in prescription.items.all():
            total_prescribed_price += float(item.medication.price * item.quantity)
        
        # NHIA patients pay 10%, others pay 100%
        if prescription.patient.patient_type == 'nhia':
            return total_prescribed_price * 0.10
        else:
            return total_prescribed_price


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
        'record': obj,  # Template expects 'record'
        'model_type': model_type,
        'model_info': model_info,
        'module_name': model_info["display_name"],  # Template expects 'module_name'
        'page_title': f'Request Authorization - {model_info["display_name"]}',
    }
    return render(request, 'core/request_authorization_form.html', context)


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
    
    # Calculate estimated cost for referrals
    if model_type == 'referral' and isinstance(obj, Referral):
        estimated_cost = calculate_referral_estimated_cost(obj)
        context['estimated_cost'] = estimated_cost
        # Set default amount if not provided in form data
        if 'form_data' not in context or not context['form_data'].get('amount'):
            context['default_amount'] = estimated_cost
    
    # Calculate estimated cost for test requests
    elif model_type == 'test_request' and hasattr(obj, 'tests'):
        # Import TestRequest model dynamically to avoid circular imports
        from laboratory.models import TestRequest
        if isinstance(obj, TestRequest):
            estimated_cost = calculate_test_request_estimated_cost(obj)
            context['estimated_cost'] = estimated_cost
            # Set default amount if not provided in form data
            if 'form_data' not in context or not context['form_data'].get('amount'):
                context['default_amount'] = estimated_cost
    
    # Calculate patient portion for prescriptions
    elif model_type == 'prescription':
        try:
            from pharmacy.models import Prescription
            if isinstance(obj, Prescription):
                # Get the 10% patient portion for NHIA patients
                patient_amount = calculate_prescription_authorization_amount(obj)
                
                # Also calculate total for reference
                total_prescribed_price = obj.get_total_prescribed_price()
                
                context['patient_amount'] = patient_amount
                context['total_prescribed_price'] = total_prescribed_price
                context['nhia_portion'] = total_prescribed_price - patient_amount
                
                # Set default amount to patient portion (10% for NHIA) if not provided in form data
                if 'form_data' not in context or not context['form_data'].get('amount'):
                    context['default_amount'] = patient_amount
        except Exception as e:
            # Log error but don't break the view
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating prescription amount: {e}")
    
    return render(request, 'core/generate_authorization.html', context)


@login_required
def universal_authorization_dashboard(request):
    """
    Universal dashboard showing all pending authorization requests across all modules
    Supports search by patient name or patient ID
    """
    # Get search query from request
    search_query = request.GET.get('search', '').strip()

    # Get all pending authorizations
    pending_items = get_all_pending_authorizations()

    # Filter pending items by search query if provided
    if search_query:
        filtered_pending_items = {}
        for model_type, data in pending_items.items():
            filtered_items = [
                item for item in data['items']
                if search_query.lower() in item.patient.get_full_name().lower() or
                   search_query.lower() in str(item.patient.patient_id).lower()
            ]
            if filtered_items:
                filtered_pending_items[model_type] = {
                    'display_name': data['display_name'],
                    'items': filtered_items,
                    'count': len(filtered_items)
                }
        pending_items = filtered_pending_items

    # Calculate total count
    total_count = sum(item['count'] for item in pending_items.values())

    # Get recent authorization codes with search filter
    recent_codes_query = AuthorizationCode.objects.select_related('patient', 'generated_by')

    if search_query:
        recent_codes_query = recent_codes_query.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(patient__patient_id__icontains=search_query)
        )

    recent_codes = recent_codes_query.order_by('-generated_at')[:20]

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
        'search_query': search_query,
        'page_title': 'Universal Authorization Dashboard',
        'active_nav': 'authorization',
        'today': today,
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

