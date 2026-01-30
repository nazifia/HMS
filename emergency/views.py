from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import EmergencyRecord, EmergencyClinicalNote
from .forms import EmergencyRecordForm, EmergencyRecordSearchForm, EmergencyClinicalNoteForm
from patients.models import Patient
from core.patient_search_utils import search_patients_by_query, format_patient_search_results
from core.medical_prescription_forms import MedicalModulePrescriptionForm, PrescriptionItemFormSet
from pharmacy.models import Prescription, PrescriptionItem
from core.decorators import department_access_required
from core.department_dashboard_utils import (
    get_user_department,
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
@department_access_required('Emergency Medicine')
def emergency_dashboard(request):
    """Dashboard for Emergency Medicine department with triage and patient flow metrics"""
    from django.db.models import Count, Avg, Q
    from datetime import timedelta

    user_department = get_user_department(request.user)

    if not user_department and not request.user.is_superuser:
        messages.error(request, "You must be assigned to a department.")
        return redirect('dashboard:dashboard')

    context = build_enhanced_dashboard_context(
        department=user_department,
        record_model=EmergencyRecord,
        record_queryset=EmergencyRecord.objects.all(),
        priority_field='triage_level',
        status_field='status',
        completed_status='discharged'
    )

    today = timezone.now().date()

    # Emergency-specific statistics
    total_visits = EmergencyRecord.objects.count()
    visits_today = EmergencyRecord.objects.filter(arrival_time__date=today).count()
    
    # Triage distribution
    triage_data = EmergencyRecord.objects.values('triage_level').annotate(count=Count('id')).order_by('-count')
    triage_labels = [item['triage_level'].replace('_', ' ').title() for item in triage_data]
    triage_counts = [item['count'] for item in triage_data]
    
    # Current status counts
    waiting_count = EmergencyRecord.objects.filter(status='waiting').count()
    in_progress_count = EmergencyRecord.objects.filter(status='in_progress').count()
    under_observation_count = EmergencyRecord.objects.filter(status='under_observation').count()
    admitted_count = EmergencyRecord.objects.filter(status='admitted').count()
    discharged_today = EmergencyRecord.objects.filter(status='discharged', discharge_time__date=today).count()
    
    # Critical patients (resuscitation and emergency triage levels)
    critical_count = EmergencyRecord.objects.filter(
        triage_level__in=['resuscitation', 'emergency'],
        status__in=['waiting', 'in_progress', 'under_observation']
    ).count()
    
    # Average vital signs
    avg_temp = EmergencyRecord.objects.aggregate(avg=Avg('temperature'))['avg']
    avg_temp = round(avg_temp, 1) if avg_temp else 0
    
    avg_pulse = EmergencyRecord.objects.aggregate(avg=Avg('pulse_rate'))['avg']
    avg_pulse = round(avg_pulse, 0) if avg_pulse else 0
    
    avg_o2sat = EmergencyRecord.objects.aggregate(avg=Avg('oxygen_saturation'))['avg']
    avg_o2sat = round(avg_o2sat, 1) if avg_o2sat else 0
    
    # Get recent records
    recent_records = EmergencyRecord.objects.select_related('patient', 'doctor').order_by('-arrival_time')[:10]
    
    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)
    
    context.update({
        'total_visits': total_visits,
        'visits_today': visits_today,
        'waiting_count': waiting_count,
        'in_progress_count': in_progress_count,
        'under_observation_count': under_observation_count,
        'admitted_count': admitted_count,
        'discharged_today': discharged_today,
        'critical_count': critical_count,
        'avg_temperature': avg_temp,
        'avg_pulse_rate': avg_pulse,
        'avg_oxygen_saturation': avg_o2sat,
        'triage_labels': json.dumps(triage_labels),
        'triage_counts': json.dumps(triage_counts),
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
    })

    return render(request, 'emergency/dashboard.html', context)


@login_required
def emergency_records_list(request):
    """View to list all emergency records with search and pagination"""
    records = EmergencyRecord.objects.select_related('patient', 'doctor').all()
    
    search_form = EmergencyRecordSearchForm(request.GET)
    search_query = None
    
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        triage_level = search_form.cleaned_data.get('triage_level')
        status = search_form.cleaned_data.get('status')
        
        if search_query:
            records = records.filter(
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query) |
                Q(patient__phone_number__icontains=search_query) |
                Q(chief_complaint__icontains=search_query) |
                Q(primary_diagnosis__icontains=search_query)
            )
            
        if date_from:
            records = records.filter(arrival_time__gte=date_from)
            
        if date_to:
            records = records.filter(arrival_time__lte=date_to)
            
        if triage_level:
            records = records.filter(triage_level=triage_level)
            
        if status:
            records = records.filter(status=status)
    
    # Get counts for stats
    total_records = records.count()
    critical_count = records.filter(triage_level__in=['resuscitation', 'emergency']).count()
    waiting_count = records.filter(status='waiting').count()
    
    # Pagination
    paginator = Paginator(records, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'search_query': search_query,
        'total_records': total_records,
        'critical_count': critical_count,
        'waiting_count': waiting_count,
    }
    return render(request, 'emergency/emergency_records_list.html', context)


@login_required
def create_emergency_record(request):
    """View to create a new emergency record"""
    if request.method == 'POST':
        form = EmergencyRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Emergency record created successfully.')
            return redirect('emergency:emergency_record_detail', record_id=record.id)
    else:
        form = EmergencyRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Emergency Record'
    }
    return render(request, 'emergency/emergency_record_form.html', context)


@login_required
def emergency_record_detail(request, record_id):
    """View to display details of a specific emergency record"""
    record = get_object_or_404(
        EmergencyRecord.objects.select_related('patient', 'doctor'),
        id=record_id
    )

    # NHIA Authorization Check
    is_nhia_patient = record.patient.patient_type == 'nhia'
    requires_authorization = is_nhia_patient and not record.authorization_code
    authorization_valid = is_nhia_patient and bool(record.authorization_code)
    authorization_message = None
    authorization_request_pending = False

    if is_nhia_patient:
        if record.authorization_code:
            authorization_message = f"Authorized - Code: {record.authorization_code}"
        else:
            authorization_message = "NHIA Authorization Required"
            
            from core.models import InternalNotification
            authorization_request_pending = InternalNotification.objects.filter(
                message__contains=f"Record ID: {record.id}",
                is_read=False
            ).filter(
                message__contains="Emergency"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing."
                )

    context = {
        'record': record,
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'emergency/emergency_record_detail.html', context)


@login_required
def edit_emergency_record(request, record_id):
    """View to edit an existing emergency record"""
    record = get_object_or_404(EmergencyRecord, id=record_id)

    if request.method == 'POST':
        form = EmergencyRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Emergency record updated successfully.')
            return redirect('emergency:emergency_record_detail', record_id=record.id)
    else:
        form = EmergencyRecordForm(instance=record)

    # NHIA Authorization Check
    is_nhia_patient = record.patient.patient_type == 'nhia'
    requires_authorization = is_nhia_patient and not record.authorization_code
    authorization_valid = is_nhia_patient and bool(record.authorization_code)
    authorization_message = None
    authorization_request_pending = False

    if is_nhia_patient:
        if record.authorization_code:
            authorization_message = f"Authorized - Code: {record.authorization_code}"
        else:
            authorization_message = "NHIA Authorization Required"
            
            from core.models import InternalNotification
            authorization_request_pending = InternalNotification.objects.filter(
                message__contains=f"Record ID: {record.id}",
                is_read=False
            ).filter(
                message__contains="Emergency"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing."
                )

    context = {
        'form': form,
        'record': record,
        'title': 'Edit Emergency Record',
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'emergency/emergency_record_form.html', context)


@login_required
def delete_emergency_record(request, record_id):
    """View to delete an emergency record"""
    record = get_object_or_404(EmergencyRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Emergency record deleted successfully.')
        return redirect('emergency:emergency_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'emergency/emergency_record_confirm_delete.html', context)


@login_required
def search_emergency_patients(request):
    """AJAX view for searching patients in Emergency module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)


@login_required
def create_prescription_for_emergency(request, record_id):
    """Create a prescription for an Emergency patient"""
    record = get_object_or_404(EmergencyRecord, id=record_id)
    
    if request.method == 'POST':
        prescription_form = MedicalModulePrescriptionForm(request.POST)
        formset = PrescriptionItemFormSet(request.POST)
        
        if prescription_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
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
                    return redirect('emergency:emergency_record_detail', record_id=record.id)
                    
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
    return render(request, 'emergency/create_prescription.html', context)


# Clinical Notes Views

@login_required
def add_clinical_note(request, record_id):
    """Add a clinical note (SOAP format) to an emergency record"""
    record = get_object_or_404(EmergencyRecord, id=record_id)

    if request.method == 'POST':
        form = EmergencyClinicalNoteForm(request.POST)
        if form.is_valid():
            clinical_note = form.save(commit=False)
            clinical_note.emergency_record = record
            clinical_note.created_by = request.user
            clinical_note.save()
            messages.success(request, 'Clinical note added successfully.')
            return redirect('emergency:emergency_record_detail', record_id=record.pk)
    else:
        form = EmergencyClinicalNoteForm()

    context = {
        'form': form,
        'record': record,
        'title': 'Add Clinical Note'
    }
    return render(request, 'emergency/clinical_note_form.html', context)


@login_required
def edit_clinical_note(request, note_id):
    """Edit an existing clinical note"""
    note = get_object_or_404(EmergencyClinicalNote, id=note_id)
    record = note.emergency_record

    if request.method == 'POST':
        form = EmergencyClinicalNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clinical note updated successfully.')
            return redirect('emergency:emergency_record_detail', record_id=record.pk)
    else:
        form = EmergencyClinicalNoteForm(instance=note)

    context = {
        'form': form,
        'note': note,
        'record': record,
        'title': 'Edit Clinical Note'
    }
    return render(request, 'emergency/clinical_note_form.html', context)


@login_required
def delete_clinical_note(request, note_id):
    """Delete a clinical note"""
    note = get_object_or_404(EmergencyClinicalNote, id=note_id)
    record_id = note.emergency_record.pk

    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Clinical note deleted successfully.')
        return redirect('emergency:emergency_record_detail', record_id=record_id)

    context = {
        'note': note
    }
    return render(request, 'emergency/clinical_note_confirm_delete.html', context)


@login_required
def view_clinical_note(request, note_id):
    """View a specific clinical note"""
    note = get_object_or_404(EmergencyClinicalNote, id=note_id)

    context = {
        'note': note,
        'record': note.emergency_record
    }
    return render(request, 'emergency/clinical_note_detail.html', context)
