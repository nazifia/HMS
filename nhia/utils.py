def generate_nhia_reg_number():
    """Generate a unique NHIA registration number."""
    return get_next_serial()

def get_next_serial():
    from nhia.models import NHIAPatient
    last_patient = NHIAPatient.objects.all().order_by('id').last()
    if not last_patient:
        return '4000000001'  # Start with 4 followed by 9 zeros and 1
    
    # Extract serial number from existing formats
    nhia_number = last_patient.nhia_reg_number
    
    # Handle all possible formats
    if nhia_number.startswith('4') and len(nhia_number) == 10 and nhia_number.isdigit():
        # New 10-digit format: 4XXXXXXXXX - use the full number
        last_serial = int(nhia_number)
    elif nhia_number.startswith('4') and len(nhia_number) == 5:
        # Previous 5-digit format: 4XXXX - convert to 10-digit format
        last_serial = int(f'4{nhia_number[1:]:0>9}')  # 4 + 9 digits
    elif '-' in nhia_number:
        # Old new format: NHIA-YYYYMMDD-0001
        last_serial = int(f'4{nhia_number.split("-")[-1]:0>9}')  # 4 + 9 digits
    else:
        # Old format: NHIA100000005 - extract the numeric part
        numeric_part = int(''.join(filter(str.isdigit, nhia_number)))
        last_serial = int(f'4{numeric_part:0>9}')  # 4 + 9 digits
    
    # Increment the serial number
    new_serial = last_serial + 1
    
    # Ensure it starts with 4 and is 10 digits
    if new_serial < 4000000000:
        new_serial = 4000000000
    
    return str(new_serial)
