from patients.models import Patient

def all_patients(request):
    """
    Adds all registered patients to the context as 'all_patients'.
    """
    return {
        'all_patients': Patient.objects.all()
    }


def current_patient_context(request):
    """
    Provides current patient context across all pages.
    Returns patient information if a patient is currently selected/viewed.
    """
    patient_context = None

    # Check if there's a patient ID in the session - with safety check
    if not hasattr(request, 'session'):
        return {
            'current_patient': patient_context,
            'has_current_patient': patient_context is not None,
        }
    
    patient_id = request.session.get('current_patient_id')

    if patient_id:
        try:
            patient = Patient.objects.get(id=patient_id, is_active=True)
            patient_context = {
                'id': patient.id,
                'patient_id': patient.patient_id,
                'full_name': patient.get_full_name(),
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'phone_number': patient.phone_number,
                'email': patient.email,
                'date_of_birth': patient.date_of_birth,
                'age': patient.get_age(),
                'gender': patient.get_gender_display(),
                'patient_type': patient.get_patient_type_display(),
                'address': patient.address,
                'city': patient.city,
                'state': patient.state,
                'photo_url': patient.get_profile_image_url(),
                'has_photo': patient.has_profile_image(),
                'is_active': patient.is_active,
                'registration_date': patient.registration_date,
            }

            # Add wallet information if available
            if hasattr(patient, 'wallet'):
                patient_context['wallet_balance'] = patient.wallet.balance
                patient_context['wallet_is_active'] = patient.wallet.is_active
            else:
                patient_context['wallet_balance'] = None
                patient_context['wallet_is_active'] = False

            # Add NHIA information if available
            if hasattr(patient, 'nhia_info'):
                patient_context['nhia_reg_number'] = patient.nhia_info.nhia_reg_number
                patient_context['nhia_is_active'] = patient.nhia_info.is_active
            else:
                patient_context['nhia_reg_number'] = None
                patient_context['nhia_is_active'] = False

        except Patient.DoesNotExist:
            # Patient not found or inactive, clear the session
            request.session.pop('current_patient_id', None)

    return {
        'current_patient': patient_context,
        'has_current_patient': patient_context is not None,
    }
