from django.core.cache import cache
from patients.models import Patient

def all_patients(request):
    patients = cache.get('ctx_all_patients')
    if patients is None:
        patients = list(
            Patient.objects.filter(is_active=True)
            .only('id', 'first_name', 'last_name', 'patient_id', 'phone_number', 'gender', 'date_of_birth')
            .order_by('first_name', 'last_name')
        )
        cache.set('ctx_all_patients', patients, 300)
    return {'all_patients': patients}


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
        ctx_cache_key = f'patient_ctx_{patient_id}'
        patient_context = cache.get(ctx_cache_key)
        if patient_context is None:
            try:
                patient = (
                    Patient.objects
                    .select_related('wallet', 'nhia_info')
                    .get(id=patient_id, is_active=True)
                )
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

                if hasattr(patient, 'wallet'):
                    patient_context['wallet_balance'] = patient.wallet.balance
                    patient_context['wallet_is_active'] = patient.wallet.is_active
                else:
                    patient_context['wallet_balance'] = None
                    patient_context['wallet_is_active'] = False

                if hasattr(patient, 'nhia_info'):
                    patient_context['nhia_reg_number'] = patient.nhia_info.nhia_reg_number
                    patient_context['nhia_is_active'] = patient.nhia_info.is_active
                else:
                    patient_context['nhia_reg_number'] = None
                    patient_context['nhia_is_active'] = False

                cache.set(ctx_cache_key, patient_context, 120)

            except Patient.DoesNotExist:
                request.session.pop('current_patient_id', None)

    return {
        'current_patient': patient_context,
        'has_current_patient': patient_context is not None,
    }
