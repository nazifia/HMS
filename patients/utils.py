from django.db import transaction, connection
from .models import Patient, Vitals
from nhia.models import NHIAPatient
import logging

logger = logging.getLogger(__name__)

def merge_patients(primary_patient, secondary_patient, is_nhia_patient=False, nhia_reg_number=None):
    """
    Merges two patient records, with an option to convert the primary patient to an NHIA patient.

    Args:
        primary_patient (Patient): The main patient record to merge into.
        secondary_patient (Patient): The patient record to merge from and then deactivate.
        is_nhia_patient (bool): If True, the primary patient will be converted to an NHIA patient.
        nhia_reg_number (str, optional): The NHIA registration number, required if is_nhia_patient is True.

    Returns:
        Patient: The updated primary patient record.
    """
    if not isinstance(primary_patient, Patient) or not isinstance(secondary_patient, Patient):
        raise TypeError("Both primary and secondary patients must be Patient instances.")

    if primary_patient == secondary_patient:
        raise ValueError("Cannot merge a patient with themselves.")

    with transaction.atomic():
        # Consolidate and update primary patient's information
        primary_patient.first_name = primary_patient.first_name or secondary_patient.first_name
        primary_patient.last_name = primary_patient.last_name or secondary_patient.last_name
        primary_patient.email = primary_patient.email or secondary_patient.email

        # Handle phone number consolidation
        if secondary_patient.phone_number and not primary_patient.phone_number:
            # If primary patient doesn't have a phone number, assign the secondary's
            if not Patient.objects.filter(phone_number=secondary_patient.phone_number).exists():
                primary_patient.phone_number = secondary_patient.phone_number
            else:
                primary_patient.notes = f"{primary_patient.notes or ''}\nSecondary phone {secondary_patient.phone_number} is already in use."

        elif secondary_patient.phone_number and primary_patient.phone_number != secondary_patient.phone_number:
            # If both have phone numbers and they are different, add secondary's to notes
            primary_patient.notes = f"{primary_patient.notes or ''}\nMerged patient's phone: {secondary_patient.phone_number}"

        primary_patient.address = primary_patient.address or secondary_patient.address
        
        # Re-associate related models from the secondary patient to the primary patient
        secondary_patient.medical_histories.update(patient=primary_patient)
        secondary_patient.vitals.update(patient=primary_patient)
        secondary_patient.documents.update(patient=primary_patient)
        secondary_patient.notes_set.update(patient=primary_patient)

        # Handle NHIA status conversion
        if is_nhia_patient:
            if not nhia_reg_number:
                raise ValueError("NHIA registration number is required for NHIA patients.")
            
            NHIAPatient.objects.update_or_create(
                patient=primary_patient,
                defaults={'nhia_reg_number': nhia_reg_number, 'is_active': True}
            )
            primary_patient.insurance_provider = 'NHIA'
            primary_patient.insurance_policy_number = nhia_reg_number
            primary_patient.patient_type = 'nhia'

        # Deactivate the secondary patient
        secondary_patient.is_active = False
        secondary_patient.save()
        
        primary_patient.save()

    return primary_patient


def get_safe_vitals_for_patient(patient, limit=None):
    """
    Safely get vitals for a patient, handling InvalidOperation errors

    Args:
        patient: Patient instance
        limit: Optional limit on number of vitals to return

    Returns:
        List of valid Vitals objects
    """
    try:
        # Try normal query first
        queryset = Vitals.objects.filter(patient=patient).order_by('-date_time')
        if limit:
            queryset = queryset[:limit]
        return list(queryset)
    except Exception as e:
        logger.warning(f"Database error when querying vitals for patient {patient.id}: {e}")

        # Fallback: get IDs first, then filter individually
        try:
            with connection.cursor() as cursor:
                sql = "SELECT id FROM patients_vitals WHERE patient_id = %s ORDER BY date_time DESC"
                params = [patient.id]
                if limit:
                    sql += f" LIMIT {limit}"
                cursor.execute(sql, params)
                vital_ids = [row[0] for row in cursor.fetchall()]

            # Get each vital individually, skipping invalid ones
            valid_vitals = []
            for vital_id in vital_ids:
                try:
                    vital = Vitals.objects.get(id=vital_id)
                    # Test decimal field access
                    _ = vital.temperature
                    _ = vital.height
                    _ = vital.weight
                    _ = vital.bmi
                    valid_vitals.append(vital)
                except Exception:
                    logger.warning(f"Skipping vital record {vital_id} due to invalid decimal data")
                    continue

            return valid_vitals
        except Exception as inner_e:
            logger.error(f"Failed to retrieve vitals for patient {patient.id}: {inner_e}")
            return []


def get_latest_safe_vitals_for_patient(patient):
    """
    Safely get the latest vitals for a patient

    Args:
        patient: Patient instance

    Returns:
        Latest Vitals object or None
    """
    vitals = get_safe_vitals_for_patient(patient, limit=1)
    return vitals[0] if vitals else None
