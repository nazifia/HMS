from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages

from patients.models import Patient
from core.patient_search_forms import PatientSearchForm
from patients.forms import RetainershipIndependentPatientForm # Import RetainershipIndependentPatientForm
from .models import RetainershipPatient

@login_required
def retainership_patient_list(request):
    retainership_patients = RetainershipPatient.objects.select_related('patient').all().order_by('-date_registered')

    search_query = request.GET.get('search', '')
    if search_query:
        retainership_patients = retainership_patients.filter(
            Q(retainership_reg_number__icontains=search_query) |
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(patient__patient_id__icontains=search_query)
        )

    paginator = Paginator(retainership_patients, 10)  # Show 10 Retainership patients per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'title': 'Retainership Patients'
    }
    return render(request, 'retainership/retainership_patient_list.html', context)

from .forms import RetainershipPatientForm

@login_required
def select_patient_for_retainership(request):
    search_form = PatientSearchForm(request.GET)
    patients = Patient.objects.all().order_by('first_name')

    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        if search_query:
            patients = patients.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(patient_id__icontains=search_query) |
                Q(phone_number__icontains=search_query)
            )

    # Filter out patients who already have an Retainership record
    patients = patients.exclude(retainership_info__isnull=False)

    paginator = Paginator(patients, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'search_form': search_form,
        'page_obj': page_obj,
        'title': 'Select Patient for Retainership Registration'
    }
    return render(request, 'retainership/select_patient_for_retainership.html', context)

@login_required
def register_patient_for_retainership(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == 'POST':
        form = RetainershipPatientForm(request.POST, instance=patient.retainership_info)
        if form.is_valid():
            retainership_patient = form.save(commit=False)
            retainership_patient.patient = patient
            retainership_patient.save()
            messages.success(request, f'Patient {patient.get_full_name()} registered for retainership successfully.')
            return redirect('retainership:retainership_patient_list')
    else:
        form = RetainershipPatientForm(instance=patient.retainership_info)

    context = {
        'form': form,
        'patient': patient,
        'title': f'Register {patient.get_full_name()} for Retainership'
    }
    return render(request, 'retainership/register_patient_for_retainership.html', context)

@login_required
def register_independent_retainership_patient(request):
    if request.method == 'POST':
        form = RetainershipIndependentPatientForm(request.POST, request.FILES)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Independent Retainership Patient {patient.get_full_name()} registered successfully.')
            return redirect('patients:detail', patient_id=patient.id)
    else:
        form = RetainershipIndependentPatientForm()

    context = {
        'form': form,
        'title': 'Register Independent Retainership Patient'
    }
    return render(request, 'retainership/register_independent_retainership_patient.html', context)
