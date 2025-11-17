from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import AncRecord
from .forms import AncRecordForm, AncRecordSearchForm
from patients.models import Patient
from core.patient_search_utils import search_patients_by_query, format_patient_search_results
from core.medical_prescription_forms import MedicalModulePrescriptionForm, PrescriptionItemFormSet
from core.prescription_utils import create_prescription_from_module, add_medication_to_prescription
from pharmacy.models import Prescription, PrescriptionItem
from core.decorators import department_access_required
from core.department_dashboard_utils import (
    get_user_department,
    build_department_dashboard_context,
    build_enhanced_dashboard_context,
    categorize_referrals,
    get_daily_trend_data,
    get_status_distribution,
    calculate_completion_rate,
    get_active_staff
)
from django.utils import timezone
import json


@login_required
@department_access_required('ANC')
def anc_dashboard(request):
    """Enhanced Dashboard for ANC department with charts and maternal health metrics"""
    from django.db.models import Count, Avg, Q
    from datetime import timedelta

    user_department = get_user_department(request.user)

    if not user_department:
        messages.error(request, "You must be assigned to a department.")
        return redirect('dashboard:dashboard')

    # Build enhanced context with charts and trends
    context = build_enhanced_dashboard_context(
        department=user_department,
        record_model=AncRecord,
        record_queryset=AncRecord.objects.all(),
        priority_field=None,
        status_field='status',
        completed_status='completed'
    )

    # ANC-specific statistics
    today = timezone.now().date()

    # Appointments today
    appointments_today = AncRecord.objects.filter(
        visit_date__date=today
    ).count()

    # Get recent records with patient info
    recent_records = AncRecord.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]

    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)

    # Add to context
    context.update({
        'appointments_today': appointments_today,
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
    })

    return render(request, 'anc/dashboard.html', context)


@login_required
def anc_records_list(request):
    """View to list all anc records with search and pagination"""
    records = AncRecord.objects.select_related('patient', 'doctor').all()
    
    search_form = AncRecordSearchForm(request.GET)
    search_query = None
    
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        
        if search_query:
            records = records.filter(
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query) |
                Q(patient__phone_number__icontains=search_query) |
                Q(diagnosis__icontains=search_query)
            )
            
        if date_from:
            records = records.filter(visit_date__gte=date_from)
            
        if date_to:
            records = records.filter(visit_date__lte=date_to)
    
    # Get counts for stats
    total_records = records.count()
    follow_up_count = records.filter(follow_up_required=True).count()
    
    # Pagination
    paginator = Paginator(records, 10)  # Show 10 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'search_query': search_query,
        'total_records': total_records,
        'follow_up_count': follow_up_count,
    }
    return render(request, 'anc/anc_records_list.html', context)

@login_required
def create_anc_record(request):
    """View to create a new anc record"""
    if request.method == 'POST':
        form = AncRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'ANC record created successfully.')
            return redirect('anc:anc_record_detail', record_id=record.id)
    else:
        form = AncRecordForm()
    
    # Get all active patients for the dropdown
    all_patients = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'form': form,
        'title': 'Create ANC Record',
        'all_patients': all_patients,
    }
    return render(request, 'anc/anc_record_form.html', context)

@login_required
def anc_record_detail(request, record_id):
    """View to display details of a specific anc record"""
    record = get_object_or_404(
        AncRecord.objects.select_related('patient', 'doctor'),
        id=record_id
    )

    # Get prescriptions for this patient
    prescriptions = Prescription.objects.filter(patient=record.patient).order_by('-prescription_date')[:5]

    # NHIA AUTHORIZATION CHECK
    is_nhia_patient = record.patient.patient_type == 'nhia'
    requires_authorization = is_nhia_patient and not record.authorization_code
    authorization_valid = is_nhia_patient and bool(record.authorization_code)
    authorization_message = None

    if is_nhia_patient:
        if record.authorization_code:
            authorization_message = f"Authorized - Code: {record.authorization_code}"
        else:
            authorization_message = "NHIA Authorization Required"
            messages.warning(
                request,
                f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                f"Please contact the desk office to obtain authorization for ANC services."
            )

    context = {
        'record': record,
        'prescriptions': prescriptions,
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
    }
    return render(request, 'anc/anc_record_detail.html', context)

@login_required
def edit_anc_record(request, record_id):
    """View to edit an existing anc record"""
    record = get_object_or_404(AncRecord, id=record_id)
    
    if request.method == 'POST':
        form = AncRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'ANC record updated successfully.')
            return redirect('anc:anc_record_detail', record_id=record.id)
    else:
        form = AncRecordForm(instance=record)
    
    # Get all active patients for the dropdown
    all_patients = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit ANC Record',
        'all_patients': all_patients,
    }
    return render(request, 'anc/anc_record_form.html', context)

@login_required
def delete_anc_record(request, record_id):
    """View to delete a anc record"""
    record = get_object_or_404(AncRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'ANC record deleted successfully.')
        return redirect('anc:anc_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'anc/anc_record_confirm_delete.html', context)

@login_required
def search_anc_patients(request):
    """AJAX view for searching patients in ANC module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)

@login_required
def create_prescription_for_anc(request, record_id):
    """Create a prescription for an ANC patient"""
    record = get_object_or_404(AncRecord, id=record_id)
    
    if request.method == 'POST':
        prescription_form = MedicalModulePrescriptionForm(request.POST)
        formset = PrescriptionItemFormSet(request.POST)
        
        if prescription_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Create the prescription
                    diagnosis = prescription_form.cleaned_data['diagnosis']
                    notes = prescription_form.cleaned_data['notes']
                    prescription_type = prescription_form.cleaned_data['prescription_type']
                    
                    prescription = Prescription.objects.create(
                        patient=record.patient,
                        doctor=request.user,
                        diagnosis=diagnosis,
                        notes=notes,
                        prescription_type=prescription_type
                    )
                    
                    # Add prescription items
                    for form in formset.cleaned_data:
                        if form and not form.get('DELETE', False):
                            medication = form['medication']
                            dosage = form['dosage']
                            frequency = form['frequency']
                            duration = form['duration']
                            quantity = form['quantity']
                            instructions = form.get('instructions', '')
                            
                            PrescriptionItem.objects.create(
                                prescription=prescription,
                                medication=medication,
                                dosage=dosage,
                                frequency=frequency,
                                duration=duration,
                                quantity=quantity,
                                instructions=instructions
                            )
                    
                    messages.success(request, 'Prescription created successfully!')
                    return redirect('anc:anc_record_detail', record_id=record.id)
                    
            except Exception as e:
                messages.error(request, f'Error creating prescription: {str(e)}')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        prescription_form = MedicalModulePrescriptionForm()
        formset = PrescriptionItemFormSet()
    
    context = {
        'record': record,
        'prescription_form': prescription_form,
        'formset': formset,
        'title': 'Create Prescription'
    }
    return render(request, 'anc/create_prescription.html', context)