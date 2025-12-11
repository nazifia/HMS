from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from patients.models import Patient
from core.patient_search_forms import PatientSearchForm
from patients.forms import NHIAIndependentPatientForm
from .models import NHIAPatient
import random
from datetime import datetime
from django.utils import timezone


def generate_nhia_reg_number():
    """Generate a unique NHIA registration number."""
    today = timezone.now().date()
    
    def get_next_serial():
        # Get the last patient to determine the next serial number
        last_patient = NHIAPatient.objects.all().order_by('id').last()
        if last_patient:
            # Extract the last serial part and increment
            try:
                last_serial = int(last_patient.nhia_reg_number.split('-')[-1])
                return last_serial + 1
            except (ValueError, IndexError):
                # If there's an issue with parsing, start from 1
                return 1
        else:
            # If no patients exist, start from 1
            return 1
    
    return f"NHIA-{today.strftime('%Y%m%d')}-{get_next_serial():04d}"


@login_required
def nhia_patient_list(request):
    nhia_patients = NHIAPatient.objects.select_related('patient').all().order_by('-date_registered')
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        nhia_patients = nhia_patients.filter(
            Q(nhia_reg_number__icontains=search_query) |
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(patient__patient_id__icontains=search_query)
        )
    
    paginator = Paginator(nhia_patients, 10)  # Show 10 NHIA patients per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'title': 'NHIA Patients'
    }
    
    return render(request, 'nhia/nhia_patient_list.html', context)


@login_required
def register_patient_for_nhia(request):
    # Start with all patients
    patients = Patient.objects.all().order_by('-registration_date')
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(patient_id__icontains=search_query)
        )
    
    # Filter out patients who already have an NHIA record
    patients = patients.exclude(nhia_info__isnull=False)
    
    paginator = Paginator(patients, 10)  # Show 10 patients per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'title': 'Select Patient for NHIA Registration'
    }
    
    return render(request, 'nhia/register_patient_for_nhia.html', context)


@login_required
def register_independent_nhia_patient(request):
    if request.method == 'POST':
        form = NHIAIndependentPatientForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the patient
            patient = form.save()
            patient.patient_type = 'nhia'  # Ensure type
            
            # Create or update NHIAPatient record
            if not hasattr(patient, 'nhia_info'):
                nhia_patient = NHIAPatient.objects.create(
                    patient=patient,
                    nhia_reg_number=generate_nhia_reg_number(),
                    is_active=form.cleaned_data.get('is_nhia_active', True)
                )
            else:
                # This shouldn't happen for a new independent patient, but just in case
                patient.nhia_info.nhia_reg_number = generate_nhia_reg_number()
                patient.nhia_info.is_active = form.cleaned_data.get('is_nhia_active', True)
                patient.nhia_info.save()
            
            messages.success(request, f'Independent NHIA Patient {patient.get_full_name()} registered successfully.')
            return redirect('nhia:nhia_patient_list')
    else:
        form = NHIAIndependentPatientForm()
    
    context = {
        'form': form,
        'title': 'Register Independent NHIA Patient'
    }
    
    return render(request, 'nhia/register_independent_nhia_patient.html', context)


# Our new views for authorization codes
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from patients.models import Patient
from .models import NHIAPatient, AuthorizationCode
from .forms import AuthorizationCodeForm
import random
import string
from datetime import datetime, timedelta
from django.utils import timezone


def generate_authorization_code():
    """Generate a unique authorization code"""
    # Generate a code with format: AUTH-YYYYMMDD-XXXXXX (where X is alphanumeric)
    date_str = timezone.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"AUTH-{date_str}-{random_str}"


@login_required
def nhia_dashboard(request):
    """Dashboard for NHIA operations"""
    # Get statistics
    total_nhia_patients = NHIAPatient.objects.count()
    active_authorization_codes = AuthorizationCode.objects.filter(status='active').count()
    used_authorization_codes = AuthorizationCode.objects.filter(status='used').count()
    
    # Get recent authorization codes
    recent_codes = AuthorizationCode.objects.all().order_by('-generated_at')[:10]
    
    context = {
        'total_nhia_patients': total_nhia_patients,
        'active_authorization_codes': active_authorization_codes,
        'used_authorization_codes': used_authorization_codes,
        'recent_codes': recent_codes,
    }
    return render(request, 'nhia/dashboard.html', context)


@login_required
def authorization_code_list(request):
    """List all authorization codes with search and filter functionality"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    service_type_filter = request.GET.get('service_type', '')
    
    codes = AuthorizationCode.objects.all().order_by('-generated_at')
    
    # Apply filters
    if search_query:
        codes = codes.filter(
            Q(code__icontains=search_query) |
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(patient__patient_id__icontains=search_query)
        )
    
    if status_filter:
        codes = codes.filter(status=status_filter)
    
    if service_type_filter:
        codes = codes.filter(service_type=service_type_filter)
    
    # Pagination
    paginator = Paginator(codes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'service_type_filter': service_type_filter,
    }
    return render(request, 'nhia/authorization_code_list.html', context)


@login_required
def generate_authorization_code_view(request):
    """Generate a new authorization code"""
    if request.method == 'POST':
        form = AuthorizationCodeForm(request.POST)
        if form.is_valid():
            authorization_code = form.save(commit=False)
            # Generate unique code
            while True:
                code = generate_authorization_code()
                if not AuthorizationCode.objects.filter(code=code).exists():
                    authorization_code.code = code
                    break
            authorization_code.generated_by = request.user
            authorization_code.save()
            messages.success(request, f'Authorization code {authorization_code.code} generated successfully.')
            return redirect('nhia:authorization_code_detail', code_id=authorization_code.id)
    else:
        # Pre-fill patient if provided in GET parameters
        patient_id = request.GET.get('patient_id')
        initial_data = {}
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id)
                initial_data['patient'] = patient
            except Patient.DoesNotExist:
                pass
        form = AuthorizationCodeForm(initial=initial_data)
    
    context = {
        'form': form,
    }
    return render(request, 'nhia/generate_authorization_code.html', context)


@login_required
def authorization_code_detail(request, code_id):
    """View details of an authorization code"""
    code = get_object_or_404(AuthorizationCode, id=code_id)
    context = {
        'code': code,
    }
    return render(request, 'nhia/authorization_code_detail.html', context)


@login_required
def cancel_authorization_code(request, code_id):
    """Cancel an authorization code"""
    code = get_object_or_404(AuthorizationCode, id=code_id)
    if code.status == 'active':
        code.status = 'cancelled'
        code.save()
        messages.success(request, f'Authorization code {code.code} has been cancelled.')
    else:
        messages.error(request, f'Authorization code {code.code} cannot be cancelled as it is not active.')
    return redirect('nhia:authorization_code_detail', code_id=code_id)