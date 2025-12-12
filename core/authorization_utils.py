"""
Universal Authorization Utilities
Provides centralized authorization request processing for all medical modules
"""
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.apps import apps
from nhia.models import AuthorizationCode
import string
import random


# Registry of all models that support authorization
AUTHORIZATION_SUPPORTED_MODELS = {
    'consultation': {
        'app': 'consultations',
        'model': 'Consultation',
        'display_name': 'Consultation',
        'service_type': 'general',
    },
    'referral': {
        'app': 'consultations',
        'model': 'Referral',
        'display_name': 'Referral',
        'service_type': 'general',
    },
    'prescription': {
        'app': 'pharmacy',
        'model': 'Prescription',
        'display_name': 'Prescription',
        'service_type': 'general',
    },
    'test_request': {
        'app': 'laboratory',
        'model': 'TestRequest',
        'display_name': 'Laboratory Test',
        'service_type': 'laboratory',
    },
    'radiology_order': {
        'app': 'radiology',
        'model': 'RadiologyOrder',
        'display_name': 'Radiology Order',
        'service_type': 'radiology',
    },
    'surgery': {
        'app': 'theatre',
        'model': 'Surgery',
        'display_name': 'Surgery',
        'service_type': 'theatre',
    },
    'dental_record': {
        'app': 'dental',
        'model': 'DentalRecord',
        'display_name': 'Dental Record',
        'service_type': 'dental',
    },
    'ophthalmic_record': {
        'app': 'ophthalmic',
        'model': 'OphthalmicRecord',
        'display_name': 'Ophthalmic Record',
        'service_type': 'opthalmic',
    },
    'ent_record': {
        'app': 'ent',
        'model': 'EntRecord',
        'display_name': 'ENT Record',
        'service_type': 'ent',
    },
    'oncology_record': {
        'app': 'oncology',
        'model': 'OncologyRecord',
        'display_name': 'Oncology Record',
        'service_type': 'oncology',
    },
    'scbu_record': {
        'app': 'scbu',
        'model': 'ScbuRecord',
        'display_name': 'SCBU Record',
        'service_type': 'inpatient',
    },
    'anc_record': {
        'app': 'anc',
        'model': 'AncRecord',
        'display_name': 'ANC Record',
        'service_type': 'general',
    },
    'labor_record': {
        'app': 'labor',
        'model': 'LaborRecord',
        'display_name': 'Labor Record',
        'service_type': 'inpatient',
    },
    'icu_record': {
        'app': 'icu',
        'model': 'IcuRecord',
        'display_name': 'ICU Record',
        'service_type': 'inpatient',
    },
    'family_planning_record': {
        'app': 'family_planning',
        'model': 'Family_planningRecord',
        'display_name': 'Family Planning Record',
        'service_type': 'general',
    },
    'gynae_emergency_record': {
        'app': 'gynae_emergency',
        'model': 'Gynae_emergencyRecord',
        'display_name': 'Gynae Emergency Record',
        'service_type': 'general',
    },
    'dental_record': {
        'app': 'dental',
        'model': 'DentalRecord',
        'display_name': 'Dental Record',
        'service_type': 'dental',
    },
    'ophthalmic_record': {
        'app': 'ophthalmic',
        'model': 'OphthalmicRecord',
        'display_name': 'Ophthalmic Record',
        'service_type': 'ophthalmic',
    },
    'ent_record': {
        'app': 'ent',
        'model': 'EntRecord',
        'display_name': 'ENT Record',
        'service_type': 'ent',
    },
}


def generate_authorization_code_string():
    """Generate a unique authorization code"""
    date_str = timezone.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"AUTH-{date_str}-{random_str}"


def get_model_info(model_type):
    """Get model information from registry"""
    return AUTHORIZATION_SUPPORTED_MODELS.get(model_type)


def get_model_class(model_type):
    """Get the actual model class for a given model type"""
    model_info = get_model_info(model_type)
    if not model_info:
        return None
    
    try:
        return apps.get_model(model_info['app'], model_info['model'])
    except LookupError:
        return None


def get_object_for_authorization(model_type, object_id):
    """Get an object that needs authorization"""
    model_class = get_model_class(model_type)
    if not model_class:
        return None
    
    try:
        return model_class.objects.get(id=object_id)
    except model_class.DoesNotExist:
        return None


def check_if_requires_authorization(obj):
    """
    Check if an object requires authorization
    Returns (requires_auth: bool, reason: str)
    """
    # Check if object has patient attribute
    if not hasattr(obj, 'patient'):
        return False, "No patient associated"
    
    patient = obj.patient
    
    # Check if patient is NHIA
    if patient.patient_type != 'nhia':
        return False, "Patient is not NHIA"
    
    # Check if object already has authorization
    if hasattr(obj, 'authorization_code') and obj.authorization_code:
        # If it's a ForeignKey to AuthorizationCode
        if isinstance(obj.authorization_code, AuthorizationCode):
            if obj.authorization_code.is_valid():
                return False, "Already has valid authorization"
        # If it's a CharField with code string
        elif isinstance(obj.authorization_code, str) and obj.authorization_code.strip():
            return False, "Already has authorization code"
    
    # For consultations and referrals, check if NHIA patient in non-NHIA unit
    if hasattr(obj, 'is_nhia_patient') and hasattr(obj, 'check_authorization_requirement'):
        if obj.check_authorization_requirement():
            return True, "NHIA patient in non-NHIA unit"
    
    # For services linked to consultations requiring authorization
    if hasattr(obj, 'consultation') and obj.consultation:
        if hasattr(obj.consultation, 'requires_authorization') and obj.consultation.requires_authorization:
            return True, "Linked to consultation requiring authorization"
    
    # Default: NHIA patients may need authorization for specialty services
    return True, "NHIA patient accessing specialty service"


def get_authorization_status(obj):
    """
    Get the authorization status of an object
    Returns: 'not_required', 'required', 'pending', 'authorized', 'rejected', 'expired'
    """
    requires_auth, _ = check_if_requires_authorization(obj)
    
    if not requires_auth:
        return 'not_required'
    
    # Check if has authorization_status field and it's set to 'pending'
    if hasattr(obj, 'authorization_status'):
        if obj.authorization_status == 'pending':
            return 'pending'
        elif obj.authorization_status == 'authorized':
            return 'authorized'
        elif obj.authorization_status == 'rejected':
            return 'rejected'
        elif obj.authorization_status == 'expired':
            return 'expired'
    
    # Check if has authorization_code
    if hasattr(obj, 'authorization_code') and obj.authorization_code:
        if isinstance(obj.authorization_code, AuthorizationCode):
            if obj.authorization_code.is_valid():
                return 'authorized'
            elif obj.authorization_code.status == 'expired':
                return 'expired'
            elif obj.authorization_code.status == 'cancelled':
                return 'rejected'
        elif isinstance(obj.authorization_code, str) and obj.authorization_code.strip():
            return 'authorized'
    
    # Default to 'required' if authorization is needed but not yet obtained
    return 'required'


def create_authorization_request(obj, requested_by, notes=''):
    """
    Create an authorization request for an object
    This marks the object as pending authorization
    """
    # Check if object supports authorization status
    if hasattr(obj, 'authorization_status'):
        obj.authorization_status = 'pending'
    
    if hasattr(obj, 'requires_authorization'):
        obj.requires_authorization = True
    
    # Add note about who requested authorization
    request_note = f"\n[Authorization requested by {requested_by.get_full_name()} on {timezone.now().strftime('%Y-%m-%d %H:%M')}]"
    if notes:
        request_note += f"\nReason: {notes}"
    
    if hasattr(obj, 'notes'):
        if obj.notes:
            obj.notes += request_note
        else:
            obj.notes = request_note.strip()
    
    obj.save()
    return True


def generate_authorization_for_object(obj, generated_by, amount=0.00, expiry_days=30, notes='', manual_code=None):
    """
    Generate an authorization code for an object
    Supports both auto-generated and manually input codes

    Args:
        obj: The object to authorize
        generated_by: User generating the code
        amount: Amount covered by authorization
        expiry_days: Number of days until expiry
        notes: Additional notes
        manual_code: Optional manual code (if None, auto-generates)

    Returns:
        (auth_code, error) tuple
    """
    model_type = None
    for key, info in AUTHORIZATION_SUPPORTED_MODELS.items():
        if obj.__class__.__name__ == info['model']:
            model_type = key
            break

    if not model_type:
        return None, "Unsupported model type"

    model_info = AUTHORIZATION_SUPPORTED_MODELS[model_type]

    # Use manual code or generate unique code
    if manual_code:
        # Validate manual code
        manual_code = manual_code.strip().upper()
        if not manual_code:
            return None, "Manual code cannot be empty"

        # Check if code already exists
        if AuthorizationCode.objects.filter(code=manual_code).exists():
            return None, f"Authorization code '{manual_code}' already exists"

        code_str = manual_code
        code_source = "Manual"
    else:
        # Auto-generate unique code
        while True:
            code_str = generate_authorization_code_string()
            if not AuthorizationCode.objects.filter(code=code_str).exists():
                break
        code_source = "System"

    # Calculate expiry date
    expiry_date = timezone.now().date() + timezone.timedelta(days=expiry_days)

    # Create authorization code
    notes_with_source = f"{code_source}-generated for {model_info['display_name']} #{obj.id}. {notes}"

    auth_code = AuthorizationCode.objects.create(
        code=code_str,
        patient=obj.patient,
        service_type=model_info['service_type'],
        amount=amount,
        expiry_date=expiry_date,
        status='active',
        notes=notes_with_source,
        generated_by=generated_by
    )

    # Link authorization code to object
    if hasattr(obj, 'authorization_code'):
        # Check if it's a ForeignKey or CharField
        field = obj._meta.get_field('authorization_code')
        if field.get_internal_type() == 'ForeignKey':
            obj.authorization_code = auth_code
        else:
            obj.authorization_code = auth_code.code

    if hasattr(obj, 'authorization_status'):
        obj.authorization_status = 'authorized'

    if hasattr(obj, 'requires_authorization'):
        obj.requires_authorization = True

    obj.save()

    return auth_code, None


def get_all_pending_authorizations():
    """
    Get all objects across all modules that are pending authorization
    Returns a dictionary grouped by model type
    """
    pending_items = {}
    
    for model_type, model_info in AUTHORIZATION_SUPPORTED_MODELS.items():
        model_class = get_model_class(model_type)
        if not model_class:
            continue
        
        # Try to get pending items
        queryset = model_class.objects.all()
        
        # Filter by authorization status if field exists
        if hasattr(model_class, 'authorization_status'):
            queryset = queryset.filter(
                requires_authorization=True,
                authorization_status__in=['required', 'pending']
            )
        else:
            # For models without authorization_status, check if they're NHIA patients without codes
            # Only filter by isnull=True since authorization_code might be a ForeignKey
            queryset = queryset.filter(
                patient__patient_type='nhia',
                authorization_code__isnull=True
            )
        
        # Get related fields for efficient querying
        if hasattr(model_class, 'patient'):
            queryset = queryset.select_related('patient')
        if hasattr(model_class, 'doctor'):
            queryset = queryset.select_related('doctor')
        
        items = list(queryset[:50])  # Limit to 50 items per model type
        
        if items:
            pending_items[model_type] = {
                'display_name': model_info['display_name'],
                'items': items,
                'count': len(items)
            }
    
    return pending_items

