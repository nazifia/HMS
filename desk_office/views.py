from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .forms import AuthorizationCodeForm, PatientSearchForm
from .models import AuthorizationCode
from patients.models import Patient

def generate_authorization_code(request):
    patient_search_form = PatientSearchForm()
    authorization_form = None
    selected_patient = None
    
    # Handle patient search
    if request.method == 'POST' and 'search_patients' in request.POST:
        patient_search_form = PatientSearchForm(request.POST)
        if patient_search_form.is_valid():
            search_query = patient_search_form.cleaned_data.get('search')
            if search_query:
                # Search for NHIA patients by name or patient ID
                patients = Patient.objects.filter(
                    patient_type='nhia'
                ).filter(
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query) |
                    Q(patient_id__icontains=search_query)
                )
                context = {
                    'patient_search_form': patient_search_form,
                    'patients': patients,
                    'search_query': search_query
                }
                return render(request, 'desk_office/generate_authorization_code.html', context)
    
    # Handle patient selection
    if request.method == 'GET' and 'patient_id' in request.GET:
        try:
            selected_patient = Patient.objects.get(id=request.GET.get('patient_id'), patient_type='nhia')
            authorization_form = AuthorizationCodeForm(patient=selected_patient)
        except Patient.DoesNotExist:
            messages.error(request, 'Selected patient not found or is not an NHIA patient.')
    
    # Handle authorization code generation
    if request.method == 'POST' and 'generate_code' in request.POST:
        try:
            patient_id = request.POST.get('patient_id')
            selected_patient = Patient.objects.get(id=patient_id, patient_type='nhia')
            authorization_form = AuthorizationCodeForm(request.POST, patient=selected_patient)
            if authorization_form.is_valid():
                authorization_code = authorization_form.save()
                messages.success(request, f'Authorization code {authorization_code.code} generated successfully.')
                return redirect('desk_office:generate_authorization_code')
            else:
                # Form is not valid, we'll display errors
                pass
        except Patient.DoesNotExist:
            messages.error(request, 'Selected patient not found or is not an NHIA patient.')
            authorization_form = AuthorizationCodeForm()
    
    context = {
        'patient_search_form': patient_search_form,
        'authorization_form': authorization_form,
        'selected_patient': selected_patient
    }
    return render(request, 'desk_office/generate_authorization_code.html', context)

def verify_authorization_code(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            authorization_code = AuthorizationCode.objects.get(code=code)
            # You can add more logic here to check the status of the code
            messages.success(request, f'Authorization code {authorization_code.code} is valid.')
            return render(request, 'desk_office/verify_authorization_code.html', {'authorization_code': authorization_code})
        except AuthorizationCode.DoesNotExist:
            messages.error(request, 'Invalid authorization code.')
            return redirect('desk_office:verify_authorization_code')
    return render(request, 'desk_office/verify_authorization_code.html')

def search_nhia_patients_ajax(request):
    """AJAX endpoint for searching NHIA patients"""
    if request.method == 'GET' and 'q' in request.GET:
        term = request.GET.get('q')
        patient_type = request.GET.get('patient_type', 'nhia')
        quick = request.GET.get('quick', 'false')
        
        if len(term) >= 2:
            patients = Patient.objects.filter(
                patient_type=patient_type
            ).filter(
                Q(first_name__icontains=term) |
                Q(last_name__icontains=term) |
                Q(patient_id__icontains=term) |
                Q(nhia_info__nhia_reg_number__icontains=term) |
                Q(phone_number__icontains=term)
            ).select_related('nhia_info')[:10]
            
            results = []
            for patient in patients:
                patient_data = {
                    'id': patient.pk,
                    'text': f"{patient.get_full_name()} ({patient.patient_id})",
                    'full_name': patient.get_full_name(),
                    'patient_id': patient.patient_id,
                    'age': patient.age,
                    'gender': patient.get_gender_display(),
                    'patient_type': patient.get_patient_type_display
                }
                
                if patient.nhia_info:
                    patient_data['nhia_number'] = patient.nhia_info.nhia_reg_number
                
                if quick == 'true':
                    # For quick code generation modal
                    results.append({
                        'id': patient.pk,
                        'text': f"{patient.get_full_name()} ({patient.patient_id})",
                        'full_name': patient.get_full_name(),
                        'patient_id': patient.patient_id
                    })
                else:
                    # For regular patient search
                    nhia_info = f'<br><small class="text-info">NHIA: {patient.nhia_info.nhia_reg_number}</small>' if patient.nhia_info else ''
                    html = f"""
                    <div class="patient-result-item card mb-2 p-3" onclick="window.location.href='/desk-office/authorization-dashboard/?patient_id={patient.pk}'">
                        <div class="row">
                            <div class="col-md-8">
                                <strong>{patient.get_full_name()}</strong>
                                <br>
                                <small class="text-muted">
                                    ID: {patient.patient_id} | 
                                    Phone: {patient.phone_number} |
                                    Age: {patient.age}
                                </small>
                                {nhia_info}
                            </div>
                            <div class="col-md-4 text-end">
                                <span class="badge bg-primary">{patient.get_patient_type_display}</span>
                                <span class="badge bg-secondary">{patient.get_gender_display}</span>
                            </div>
                        </div>
                    </div>
                    """
                    results.append({
                        'id': patient.pk,
                        'html': html
                    })
            
            return JsonResponse({'results': results})
    
    return JsonResponse({'results': []})


def cancel_authorization_code(request, code_id):
    """Cancel an authorization code"""
    if request.method == 'POST':
        try:
            auth_code = AuthorizationCode.objects.get(code=code_id)
            if auth_code.status == 'active':
                auth_code.status = 'cancelled'
                auth_code.save()
                messages.success(request, f'Authorization code {auth_code.code} has been cancelled.')
            else:
                messages.warning(request, 'Only active authorization codes can be cancelled.')
        except AuthorizationCode.DoesNotExist:
            messages.error(request, 'Authorization code not found.')
    
    return redirect(request.META.get('HTTP_REFERER', 'desk_office:authorization_code_list'))


def authorization_code_detail(request, code_id):
    """AJAX endpoint for authorization code details"""
    try:
        auth_code = AuthorizationCode.objects.get(code=code_id)
        
        nhia_info = f'<p><strong>NHIA Number:</strong> {auth_code.patient.nhia_info.nhia_reg_number}</p>' if auth_code.patient.nhia_info else ''
        
        html = f"""
        <div class="row">
            <div class="col-md-6">
                <h6>Code Information</h6>
                <p><strong>Code:</strong> {auth_code.code}</p>
                <p><strong>Status:</strong> <span class="badge bg-info">{auth_code.get_status_display()}</span></p>
                <p><strong>Generated:</strong> {auth_code.generated_at.strftime('%b %d, %Y %H:%M')}</p>
                <p><strong>Expires:</strong> {auth_code.expiry_date.strftime('%b %d, %Y') if auth_code.expiry_date else 'Never'}</p>
                <p><strong>Amount:</strong> ₦{auth_code.amount:.2f}</p>
            </div>
            <div class="col-md-6">
                <h6>Patient Information</h6>
                <p><strong>Name:</strong> {auth_code.patient.get_full_name()}</p>
                <p><strong>Patient ID:</strong> {auth_code.patient.patient_id}</p>
                <p><strong>Patient Type:</strong> {auth_code.patient.get_patient_type_display()}</p>
                {nhia_info}
            </div>
        </div>
        """
        return JsonResponse({'html': html})
    except AuthorizationCode.DoesNotExist:
        return JsonResponse({'error': 'Authorization code not found'})