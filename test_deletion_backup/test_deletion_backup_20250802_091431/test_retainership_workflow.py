import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from patients.forms import RetainershipIndependentPatientForm
from retainership.models import RetainershipPatient
from patients.models import Patient

def test_retainership_workflow():
    # 1. Create a new independent retainership patient
    form_data = {
        'first_name': 'John',
        'last_name': 'Doe',
        'date_of_birth': '1990-01-15',
        'gender': 'M',
        'phone_number': '+233241112223',
        'email': 'john.doe@example.com',
        'address': '123 Main St',
        'city': 'Accra',
        'state': 'Greater Accra',
        'country': 'Ghana',
        'is_retainership_active': True,
    }

    form = RetainershipIndependentPatientForm(data=form_data)
    if form.is_valid():
        patient = form.save()
        print(f"Successfully created patient: {patient.get_full_name()}")

        # 2. Verify the patient is created and is a retainership patient
        retainership_patient = RetainershipPatient.objects.get(patient=patient)
        print(f"Successfully created retainership patient: {retainership_patient}")

        # 3. Verify the registration number
        reg_number = str(retainership_patient.retainership_reg_number)
        if reg_number.startswith('3') and len(reg_number) == 10:
            print(f"Registration number {reg_number} is valid.")
        else:
            print(f"Registration number {reg_number} is invalid.")

    else:
        print("Form is not valid:", form.errors)

if __name__ == '__main__':
    test_retainership_workflow()
