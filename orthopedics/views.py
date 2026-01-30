from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import OrthopedicsRecord, OrthopedicsClinicalNote
from .forms import OrthopedicsRecordForm, OrthopedicsRecordSearchForm, OrthopedicsClinicalNoteForm
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
@department_access_required('Orthopedics')
def orthopedics_dashboard(request):
    """Dashboard for Orthopedics department with orthopedic care metrics"""
    from django.db.models import Count, Avg, Q
    from datetime import timedelta

    user_department = get_user_department(request.user)

    if not user_department and not request.user.is_superuser:
        messages.error(request, "You must be assigned to a department.")
        return redirect('dashboard:dashboard')

    context = build_enhanced_dashboard_context(
        department=user_department,
        record_model=OrthopedicsRecord,
        record_queryset=OrthopedicsRecord.objects.all(),
        priority_field=None,
        status_field=None,
        completed_status=None
    )

    today = timezone.now().date()

    # Orthopedics-specific statistics
    total_records = OrthopedicsRecord.objects.count()
    records_today = OrthopedicsRecord.objects.filter(visit_date__date=today).count()
    
    # Injury type distribution
    injury_data = OrthopedicsRecord.objects.exclude(injury_type__isnull=True).exclude(injury_type='').values('injury_type').annotate(count=Count('id')).order_by('-count')[:5]
    injury_labels = [item['injury_type'] for item in injury_data]
    injury_counts = [item['count'] for item in injury_data]
    
    # Body part distribution
    body_part_data = OrthopedicsRecord.objects.exclude(affected_body_part__isnull=True).exclude(affected_body_part='').values('affected_body_part').annotate(count=Count('id')).order_by('-count')[:5]
    body_part_labels = [item['affected_body_part'] for item in body_part_data]
    body_part_counts = [item['count'] for item in body_part_data]
    
    # Average pain score
    avg_pain = OrthopedicsRecord.objects.aggregate(avg=Avg('pain_score'))['avg']
    avg_pain = round(avg_pain, 1) if avg_pain else 0
    
    # Follow-ups due
    followups_due = OrthopedicsRecord.objects.filter(
        follow_up_required=True,
        follow_up_date__gte=today,
        follow_up_date__lte=today + timedelta(days=7)
    ).count()
    
    # Procedures count
    procedures_count = OrthopedicsRecord.objects.exclude(procedure_done__isnull=True).exclude(procedure_done='').count()
    
    # Recent records
    recent_records = OrthopedicsRecord.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]
    
    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)
    
    context.update({
        'total_records': total_records,
        'records_today': records_today,
        'avg_pain_score': avg_pain,
        'followups_due': followups_due,
        'procedures_count': procedures_count,
        'injury_labels': json.dumps(injury_labels),
        'injury_counts': json.dumps(injury_counts),
        'body_part_labels': json.dumps(body_part_labels),
        'body_part_counts': json.dumps(body_part_counts),
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
    })

    return render(request, 'orthopedics/dashboard.html', context)


@login_required
def orthopedics_records_list(request):
    """View to list all orthopedics records with search and pagination"""
    records = OrthopedicsRecord.objects.select_related('patient', 'doctor').all()
    
    search_form = OrthopedicsRecordSearchForm(request.GET)
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
                Q(diagnosis__icontains=search_query) |
                Q(injury_type__icontains=search_query) |
                Q(affected_body_part__icontains=search_query)
            )
            
        if date_from:
            records = records.filter(visit_date__gte=date_from)
            
        if date_to:
            records = records.filter(visit_date__lte=date_to)
    
    # Get counts for stats
    total_records = records.count()
    follow_up_count = records.filter(follow_up_required=True).count()
    
    # Pagination
    paginator = Paginator(records, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'search_query': search_query,
        'total_records': total_records,
        'follow_up_count': follow_up_count,
    }
    return render(request, 'orthopedics/orthopedics_records_list.html', context)


@login_required
def create_orthopedics_record(request):
    """View to create a new orthopedics record"""
    if request.method == 'POST':
        form = OrthopedicsRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Orthopedics record created successfully.')
            return redirect('orthopedics:orthopedics_record_detail', record_id=record.id)
    else:
        form = OrthopedicsRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Orthopedics Record'
    }
    return render(request, 'orthopedics/orthopedics_record_form.html', context)


@login_required
def orthopedics_record_detail(request, record_id):
    """View to display details of a specific orthopedics record"""
    record = get_object_or_404(
        OrthopedicsRecord.objects.select_related('patient', 'doctor'),
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
                message__contains="Orthopedics"
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
    return render(request, 'orthopedics/orthopedics_record_detail.html', context)


@login_required
def edit_orthopedics_record(request, record_id):
    """View to edit an existing orthopedics record"""
    record = get_object_or_404(OrthopedicsRecord, id=record_id)

    if request.method == 'POST':
        form = OrthopedicsRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Orthopedics record updated successfully.')
            return redirect('orthopedics:orthopedics_record_detail', record_id=record.id)
    else:
        form = OrthopedicsRecordForm(instance=record)

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
                message__contains="Orthopedics"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing."
                )

    context = {
        'form': form,
        'record': record,
        'title': 'Edit Orthopedics Record',
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'orthopedics/orthopedics_record_form.html', context)


@login_required
def delete_orthopedics_record(request, record_id):
    """View to delete an orthopedics record"""
    record = get_object_or_404(OrthopedicsRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Orthopedics record deleted successfully.')
        return redirect('orthopedics:orthopedics_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'orthopedics/orthopedics_record_confirm_delete.html', context)


@login_required
def search_orthopedics_patients(request):
    """AJAX view for searching patients in Orthopedics module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)


@login_required
def create_prescription_for_orthopedics(request, record_id):
    """Create a prescription for an Orthopedics patient"""
    record = get_object_or_404(OrthopedicsRecord, id=record_id)
    
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
                    return redirect('orthopedics:orthopedics_record_detail', record_id=record.id)
                    
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
    return render(request, 'orthopedics/create_prescription.html', context)


# Clinical Notes Views

@login_required
def add_clinical_note(request, record_id):
    """Add a clinical note (SOAP format) to an orthopedics record"""
    record = get_object_or_404(OrthopedicsRecord, id=record_id)

    if request.method == 'POST':
        form = OrthopedicsClinicalNoteForm(request.POST)
        if form.is_valid():
            clinical_note = form.save(commit=False)
            clinical_note.orthopedics_record = record
            clinical_note.created_by = request.user
            clinical_note.save()
            messages.success(request, 'Clinical note added successfully.')
            return redirect('orthopedics:orthopedics_record_detail', record_id=record.pk)
    else:
        form = OrthopedicsClinicalNoteForm()

    context = {
        'form': form,
        'record': record,
        'title': 'Add Clinical Note'
    }
    return render(request, 'orthopedics/clinical_note_form.html', context)


@login_required
def edit_clinical_note(request, note_id):
    """Edit an existing clinical note"""
    note = get_object_or_404(OrthopedicsClinicalNote, id=note_id)
    record = note.orthopedics_record

    if request.method == 'POST':
        form = OrthopedicsClinicalNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clinical note updated successfully.')
            return redirect('orthopedics:orthopedics_record_detail', record_id=record.pk)
    else:
        form = OrthopedicsClinicalNoteForm(instance=note)

    context = {
        'form': form,
        'note': note,
        'record': record,
        'title': 'Edit Clinical Note'
    }
    return render(request, 'orthopedics/clinical_note_form.html', context)


@login_required
def delete_clinical_note(request, note_id):
    """Delete a clinical note"""
    note = get_object_or_404(OrthopedicsClinicalNote, id=note_id)
    record_id = note.orthopedics_record.pk

    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Clinical note deleted successfully.')
        return redirect('orthopedics:orthopedics_record_detail', record_id=record_id)

    context = {
        'note': note
    }
    return render(request, 'orthopedics/clinical_note_confirm_delete.html', context)


@login_required
def view_clinical_note(request, note_id):
    """View a specific clinical note"""
    note = get_object_or_404(OrthopedicsClinicalNote, id=note_id)

    context = {
        'note': note,
        'record': note.orthopedics_record
    }
    return render(request, 'orthopedics/clinical_note_detail.html', context)
