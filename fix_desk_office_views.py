"""
Fix the generate_authorization_code view to handle both primary key and custom patient_id lookups
"""
import re

with open(r'c:\Users\Dell\Desktop\MY_PRODUCTS\HMS\desk_office\views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the patient selection block

old_code = """    # Handle patient selection
    if request.method == 'GET' and 'patient_id' in request.GET:
        try:
            selected_patient = Patient.objects.get(id=request.GET.get('patient_id'), patient_type='nhia')
            authorization_form = AuthorizationCodeForm(patient=selected_patient)
        except Patient.DoesNotExist:
            messages.error(request, 'Selected patient not found or is not an NHIA patient.')"""

new_code = """    # Handle patient selection
    if request.method == 'GET' and 'patient_id' in request.GET:
        patient_identifier = request.GET.get('patient_id')
        try:
            # Try to find by primary key first (integer ID)
            try:
                selected_patient = Patient.objects.get(id=int(patient_identifier), patient_type='nhia')
            except (ValueError, Patient.DoesNotExist):
                # If that fails, try finding by custom patient_id field (string)
                selected_patient = Patient.objects.get(patient_id=patient_identifier, patient_type='nhia')
            
            authorization_form = AuthorizationCodeForm(patient=selected_patient)
        except Patient.DoesNotExist:
            messages.error(request, 'Selected patient not found or is not an NHIA patient.')"""

content = content.replace(old_code, new_code)

with open(r'c:\Users\Dell\Desktop\MY_PRODUCTS\HMS\desk_office\views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully fixed desk_office/views.py")
