from django.db import transaction
from .models import Patient
from nhia.models import NHIAPatient

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
