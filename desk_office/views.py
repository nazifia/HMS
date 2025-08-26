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
    if request.method == 'GET' and 'term' in request.GET:
        term = request.GET.get('term')
        if len(term) >= 2:
            patients = Patient.objects.filter(
                patient_type='nhia'
            ).filter(
                Q(first_name__icontains=term) |
                Q(last_name__icontains=term) |
                Q(patient_id__icontains=term)
            )[:10]
            
            results = []
            for patient in patients:
                results.append({
                    'id': patient.pk,
                    'text': f"{patient.get_full_name()} ({patient.patient_id})"
                })
            
            return JsonResponse({'results': results})
    
    return JsonResponse({'results': []})