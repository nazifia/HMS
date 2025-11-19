"""
Script to fix the corrupted dental_record_detail view and implement edit_dental_record.
This applies surgical fixes to dental/views.py
"""
import re

# Read the file
with open(r'c:\Users\Dell\Desktop\MY_PRODUCTS\HMS\dental\views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Replace the corrupted dental_record_detail function (lines 244-273)
old_detail = '''@login_required
def dental_record_detail(request, record_id):
    """View to display details of a specific dental record"""
    record = get_object_or_404(DentalRecord.objects.select_related('patient', 'service', 'dentist', 'authorization_code'), id=record_id)

    # Get prescriptions for this patient
    prescriptions = Prescription.objects.filter(patient=record.patient).order_by('-prescription_date')[:5]

    # Get X-rays for this record
    xrays = DentalXRay.objects.filter(dental_record=record).order_by('-taken_at')

    # **NHIA AUTHORIZATION CHECK**
    """View to edit an existing dental record"""
    record = get_object_or_404(DentalRecord, id=record_id)
    
    if request.method == 'POST':
        form = DentalRecordForm(request.POST, instance=record)
        if form.is_valid():
            record = form.save()  # Capture the saved instance
            messages.success(request, 'Dental record updated successfully.')
            return redirect('dental:dental_record_detail', record_id=record.id)
    else:
        form = DentalRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Dental Record'
    }
    return render(request, 'dental/dental_record_form.html', context)'''

new_detail = '''@login_required
def dental_record_detail(request, record_id):
    """View to display details of a specific dental record"""
    record = get_object_or_404(DentalRecord.objects.select_related('patient', 'service', 'dentist', 'authorization_code'), id=record_id)

    # Get prescriptions for this patient
    prescriptions = Prescription.objects.filter(patient=record.patient).order_by('-prescription_date')[:5]

    # Get X-rays for this record
    xrays = DentalXRay.objects.filter(dental_record=record).order_by('-taken_at')

    # **NHIA AUTHORIZATION CHECK**
    is_nhia_patient = record.patient.patient_type == 'nhia'
    requires_authorization = is_nhia_patient and not record.authorization_code
    authorization_valid = is_nhia_patient and bool(record.authorization_code)
    
    # Authorization message for NHIA patients
    if is_nhia_patient:
        if authorizationvalid:
            authorization_message = f"Authorized with code: {record.authorization_code.code}"
        else:
            authorization_message = "Authorization required - Please request authorization from desk office"
    else:
        authorization_message = "Not applicable (Non-NHIA patient)"
    
    context = {
        'record': record,
        'prescriptions': prescriptions,
        'xrays': xrays,
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
    }
    return render(request, 'dental/dental_record_detail.html', context)'''

# Fix 2: Replace the empty edit_dental_record stub (lines 530-532  
old_edit = '''@login_required
def edit_dental_record(request, record_id):
    """View to edit an existing dental record"""'''

new_edit = '''@login_required
def edit_dental_record(request, record_id):
    """View to edit an existing dental record"""
    from django.urls import reverse
    record = get_object_or_404(DentalRecord, id=record_id)
    
    if request.method == 'POST':
        form = DentalRecordForm(request.POST, instance=record)
        if form.is_valid():
            record = form.save()  # Capture the saved instance
            messages.success(request, 'Dental record updated successfully.')
            
            # Check if patient is NHIA - redirect to authorization code request page
            if record.patient.patient_type == 'nhia':
                # Redirect to authorization code generation page with patient_id
                return redirect(f"{reverse('desk_office:generate_authorization_code')}?patient_id={record.patient.id}")
            else:
                # For non-NHIA patients, redirect back to detail page
                return redirect('dental:dental_record_detail', record_id=record.id)
    else:
        form = DentalRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Dental Record'
    }
    return render(request, 'dental/dental_record_form.html', context)'''

# Apply fixes
content = content.replace(old_detail, new_detail)
content = content.replace(old_edit, new_edit)

# Write back
with open(r'c:\Users\Dell\Desktop\MY_PRODUCTS\HMS\dental\views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully fixed dental/views.py")
