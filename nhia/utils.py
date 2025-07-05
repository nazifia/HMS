import datetime

def generate_nhia_reg_number():
    """Generate a unique NHIA registration number."""
    today = datetime.date.today()
    return f"NHIA-{today.strftime('%Y%m%d')}-{get_next_serial()}"

def get_next_serial():
    from nhia.models import NHIAPatient
    last_patient = NHIAPatient.objects.all().order_by('id').last()
    if not last_patient:
        return '0001'
    last_serial = int(last_patient.nhia_reg_number.split('-')[-1])
    new_serial = last_serial + 1
    return f'{new_serial:04d}'
