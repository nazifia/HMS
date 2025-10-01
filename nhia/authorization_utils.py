"""
Utility functions for NHIA authorization checking and management.

This module provides helper functions to determine when NHIA patients
require desk office authorization for services.
"""

from django.utils import timezone


def is_nhia_patient(patient):
    """
    Check if a patient is an NHIA patient.

    Args:
        patient: Patient model instance

    Returns:
        bool: True if patient has active NHIA info, False otherwise
    """
    # Use the Patient model's is_nhia_patient() method for consistency
    return patient.is_nhia_patient()


def is_nhia_department(department):
    """
    Check if a department is an NHIA department.
    
    Args:
        department: Department model instance
        
    Returns:
        bool: True if department is NHIA, False otherwise
    """
    if not department:
        return False
    return department.name.upper() == 'NHIA'


def is_nhia_consulting_room(consulting_room):
    """
    Check if a consulting room belongs to NHIA department.
    
    Args:
        consulting_room: ConsultingRoom model instance
        
    Returns:
        bool: True if room is in NHIA department, False otherwise
    """
    if not consulting_room or not consulting_room.department:
        return False
    return is_nhia_department(consulting_room.department)


def requires_consultation_authorization(patient, consulting_room):
    """
    Determine if a consultation requires authorization.
    
    NHIA patients seen in non-NHIA consulting rooms require authorization.
    
    Args:
        patient: Patient model instance
        consulting_room: ConsultingRoom model instance
        
    Returns:
        bool: True if authorization is required, False otherwise
    """
    if not is_nhia_patient(patient):
        return False
    
    if is_nhia_consulting_room(consulting_room):
        return False
    
    return True


def requires_referral_authorization(patient, from_consultation, to_doctor):
    """
    Determine if a referral requires authorization.
    
    NHIA patients referred from NHIA units to non-NHIA units require authorization.
    
    Args:
        patient: Patient model instance
        from_consultation: Consultation model instance (source of referral)
        to_doctor: CustomUser model instance (doctor being referred to)
        
    Returns:
        bool: True if authorization is required, False otherwise
    """
    if not is_nhia_patient(patient):
        return False
    
    # Check if referral is from NHIA consultation
    if not from_consultation or not from_consultation.consulting_room:
        return False
    
    if not is_nhia_consulting_room(from_consultation.consulting_room):
        return False
    
    # Check if referred-to doctor is in NHIA department
    if not to_doctor or not hasattr(to_doctor, 'profile'):
        return True  # Assume authorization required if we can't determine
    
    profile = to_doctor.profile
    if not profile or not profile.department:
        return True  # Assume authorization required if we can't determine
    
    if is_nhia_department(profile.department):
        return False
    
    return True


def requires_prescription_authorization(patient, consultation=None):
    """
    Determine if a prescription requires authorization.
    
    NHIA patients with prescriptions from non-NHIA consultations require authorization.
    
    Args:
        patient: Patient model instance
        consultation: Consultation model instance (optional)
        
    Returns:
        bool: True if authorization is required, False otherwise
    """
    if not is_nhia_patient(patient):
        return False
    
    if consultation and consultation.requires_authorization:
        return True
    
    return False


def requires_lab_test_authorization(patient, consultation=None):
    """
    Determine if a lab test request requires authorization.
    
    NHIA patients with lab tests from non-NHIA consultations require authorization.
    
    Args:
        patient: Patient model instance
        consultation: Consultation model instance (optional)
        
    Returns:
        bool: True if authorization is required, False otherwise
    """
    if not is_nhia_patient(patient):
        return False
    
    if consultation and consultation.requires_authorization:
        return True
    
    return False


def requires_radiology_authorization(patient, consultation=None):
    """
    Determine if a radiology order requires authorization.
    
    NHIA patients with radiology orders from non-NHIA consultations require authorization.
    
    Args:
        patient: Patient model instance
        consultation: Consultation model instance (optional)
        
    Returns:
        bool: True if authorization is required, False otherwise
    """
    if not is_nhia_patient(patient):
        return False
    
    if consultation and consultation.requires_authorization:
        return True
    
    return False


def validate_authorization_code(authorization_code, service_type=None):
    """
    Validate an authorization code.
    
    Args:
        authorization_code: AuthorizationCode model instance
        service_type: Optional service type to validate against
        
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    if not authorization_code:
        return False, "No authorization code provided"
    
    if not authorization_code.is_valid():
        return False, f"Authorization code is {authorization_code.status}"
    
    if service_type and authorization_code.service_type not in [service_type, 'general']:
        return False, f"Authorization code is for {authorization_code.get_service_type_display()}, not {service_type}"
    
    if authorization_code.expiry_date < timezone.now().date():
        return False, "Authorization code has expired"
    
    return True, "Authorization code is valid"


def get_authorization_status_display(requires_auth, has_code, code_valid=None):
    """
    Get a user-friendly display of authorization status.
    
    Args:
        requires_auth: bool - whether authorization is required
        has_code: bool - whether an authorization code is present
        code_valid: bool or None - whether the code is valid (if present)
        
    Returns:
        dict: Display information with status, message, css_class, icon
    """
    if not requires_auth:
        return {
            'status': 'not_required',
            'message': 'Authorization not required',
            'css_class': 'secondary',
            'icon': 'info-circle'
        }
    
    if not has_code:
        return {
            'status': 'required',
            'message': 'Desk office authorization required',
            'css_class': 'warning',
            'icon': 'exclamation-triangle'
        }
    
    if code_valid is False:
        return {
            'status': 'invalid',
            'message': 'Authorization code is invalid or expired',
            'css_class': 'danger',
            'icon': 'times-circle'
        }
    
    if code_valid is True:
        return {
            'status': 'authorized',
            'message': 'Authorized',
            'css_class': 'success',
            'icon': 'check-circle'
        }
    
    return {
        'status': 'pending',
        'message': 'Authorization pending verification',
        'css_class': 'info',
        'icon': 'clock'
    }

