"""
Script to implement auto-population of authorization amount from dental service price
"""

# Fix 1: Update dental edit view to pass service price
with open(r'c:\Users\Dell\Desktop\MY_PRODUCTS\HMS\dental\views.py', 'r', encoding='utf-8') as f:
    dental_content = f.read()

old_redirect = """            # Check if patient is NHIA - redirect to authorization code request page
            if record.patient.patient_type == 'nhia':
                # Redirect to authorization code generation page with patient_id
                return redirect(f"{reverse('desk_office:generate_authorization_code')}?patient_id={record.patient.id}")"""

new_redirect = """            # Check if patient is NHIA - redirect to authorization code request page
            if record.patient.patient_type == 'nhia':
                # Get service price for authorization amount
                service_price = record.get_service_price()
                # Redirect to authorization code generation page with patient_id and amount
                return redirect(f"{reverse('desk_office:generate_authorization_code')}?patient_id={record.patient.id}&amount={service_price}")"""

dental_content = dental_content.replace(old_redirect, new_redirect)

with open(r'c:\Users\Dell\Desktop\MY_PRODUCTS\HMS\dental\views.py', 'w', encoding='utf-8') as f:
    f.write(dental_content)

# Fix 2: Update desk_office view to capture amount parameter
with open(r'c:\Users\Dell\Desktop\MY_PRODUCTS\HMS\desk_office\views.py', 'r', encoding='utf-8') as f:
    desk_content = f.read()

old_patient_selection = """    # Handle patient selection
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

new_patient_selection = """    # Handle patient selection
    if request.method == 'GET' and 'patient_id' in request.GET:
        patient_identifier = request.GET.get('patient_id')
        service_amount = request.GET.get('amount', None)  # Get amount from URL if provided
        try:
            # Try to find by primary key first (integer ID)
            try:
                selected_patient = Patient.objects.get(id=int(patient_identifier), patient_type='nhia')
            except (ValueError, Patient.DoesNotExist):
                # If that fails, try finding by custom patient_id field (string)
                selected_patient = Patient.objects.get(patient_id=patient_identifier, patient_type='nhia')
            
            # Pass the amount to the form if provided
            if service_amount:
                authorization_form = AuthorizationCodeForm(patient=selected_patient, initial={'amount': service_amount})
            else:
                authorization_form = AuthorizationCodeForm(patient=selected_patient)
        except Patient.DoesNotExist:
            messages.error(request, 'Selected patient not found or is not an NHIA patient.')"""

desk_content = desk_content.replace(old_patient_selection, new_patient_selection)

with open(r'c:\Users\Dell\Desktop\MY_PRODUCTS\HMS\desk_office\views.py', 'w', encoding='utf-8') as f:
    f.write(desk_content)

# Fix 3: Update form to include amount field
with open(r'c:\Users\Dell\Desktop\MY_PRODUCTS\HMS\desk_office\forms.py', 'r', encoding='utf-8') as f:
    form_content = f.read()

old_meta = """    class Meta:
        model = AuthorizationCode
        fields = ['patient', 'service_type', 'service_description', 'department']"""

new_meta = """    class Meta:
        model = AuthorizationCode
        fields = ['patient', 'service_type', 'service_description', 'department', 'amount']"""

form_content = form_content.replace(old_meta, new_meta)

with open(r'c:\Users\Dell\Desktop\MY_PRODUCTS\HMS\desk_office\forms.py', 'w', encoding='utf-8') as f:
    f.write(form_content)

print("Successfully implemented auto-population of authorization amount!")
print("Changes made:")
print("1. dental/views.py - Added service price to redirect URL")
print("2. desk_office/views.py - Added amount parameter capture and form initialization")
print("3. desk_office/forms.py - Added amount field to form fields list")
