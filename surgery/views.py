from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import SurgeryRecord, SurgeryClinicalNote
from .forms import SurgeryRecordForm, SurgeryRecordSearchForm, SurgeryClinicalNoteForm
from patients.models import Patient
from core.patient_search_utils import search_patients_by_query, format_patient_search_results
from core.medical_prescription_forms import MedicalModulePrescriptionForm, PrescriptionItemFormSet
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
@department_access_required('Surgery')
def surgery_dashboard(request):
    """Enhanced Dashboard for Surgery department with charts and metrics"""
    from django.db.models import Count, Avg, Q, F, ExpressionWrapper, DurationField
    from datetime import timedelta

    user_department = get_user_department(request.user)

    # Superusers can access all departments without assignment
    if not user_department and not request.user.is_superuser:
        messages.error(request, "You must be assigned to a department.")
        return redirect('dashboard:dashboard')

    # Build enhanced context with charts and trends
    context = build_enhanced_dashboard_context(
        department=user_department,
        record_model=SurgeryRecord,
        record_queryset=SurgeryRecord.objects.all(),
        priority_field=None,
        status_field=None,
        completed_status=None
    )

    # Surgery-specific statistics
    today = timezone.now().date()
    week_end = today + timedelta(days=7)

    # Total surgeries
    total_surgeries = SurgeryRecord.objects.count()

    # Surgeries today
    surgeries_today = SurgeryRecord.objects.filter(
        surgery_date__date=today
    ).count()

    # Surgeries this week
    surgeries_this_week = SurgeryRecord.objects.filter(
        surgery_date__date__gte=today,
        surgery_date__date__lte=week_end
    ).count()

    # Follow-ups due this week
    followups_due = SurgeryRecord.objects.filter(
        follow_up_required=True,
        follow_up_date__gte=today,
        follow_up_date__lte=week_end
    ).count()

    # Average blood loss
    avg_blood_loss = SurgeryRecord.objects.aggregate(avg=Avg('estimated_blood_loss'))['avg']
    avg_blood_loss = round(avg_blood_loss, 2) if avg_blood_loss else 0

    # Complications count
    complications_count = SurgeryRecord.objects.filter(
        complications__isnull=False
    ).exclude(complications='').count()

    # Post-op day tracking
    avg_postop_day = SurgeryRecord.objects.aggregate(avg=Avg('postop_day'))['avg']
    avg_postop_day = round(avg_postop_day, 1) if avg_postop_day else 0

    # Common surgery types (top 5)
    surgery_type_data = SurgeryRecord.objects.filter(
        surgery_type__isnull=False
    ).exclude(surgery_type='').values('surgery_type').annotate(count=Count('id')).order_by('-count')[:5]
    surgery_type_labels = [item['surgery_type'][:30] for item in surgery_type_data]
    surgery_type_counts = [item['count'] for item in surgery_type_data]

    # Get recent records with patient info
    recent_records = SurgeryRecord.objects.select_related('patient', 'doctor', 'surgeon').order_by('-created_at')[:10]

    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)

    # Add to context
    context.update({
        'total_surgeries': total_surgeries,
        'surgeries_today': surgeries_today,
        'surgeries_this_week': surgeries_this_week,
        'followups_due': followups_due,
        'avg_blood_loss': avg_blood_loss,
        'complications_count': complications_count,
        'avg_postop_day': avg_postop_day,
        'surgery_type_labels': json.dumps(surgery_type_labels),
        'surgery_type_counts': json.dumps(surgery_type_counts),
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
    })

    return render(request, 'surgery/dashboard.html', context)


@login_required
def surgery_records_list(request):
    """View to list all surgery records with search and pagination"""
    records = SurgeryRecord.objects.select_related('patient', 'doctor', 'surgeon').all()
    
    search_form = SurgeryRecordSearchForm(request.GET)
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
                Q(surgery_type__icontains=search_query) |
                Q(preop_diagnosis__icontains=search_query)
            )
            
        if date_from:
            records = records.filter(surgery_date__gte=date_from)
            
        if date_to:
            records = records.filter(surgery_date__lte=date_to)
    
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
    return render(request, 'surgery/surgery_records_list.html', context)


@login_required
def create_surgery_record(request):
    """View to create a new surgery record"""
    if request.method == 'POST':
        form = SurgeryRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Surgery record created successfully.')
            return redirect('surgery:surgery_record_detail', record_id=record.id)
    else:
        form = SurgeryRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Surgery Record'
    }
    return render(request, 'surgery/surgery_record_form.html', context)


@login_required
def surgery_record_detail(request, record_id):
    """View to display details of a specific surgery record"""
    record = get_object_or_404(
        SurgeryRecord.objects.select_related('patient', 'doctor', 'surgeon', 'assistant_surgeon', 'anesthesiologist'),
        id=record_id
    )

    # **NHIA AUTHORIZATION CHECK**
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

            # Check for pending authorization request
            from core.models import InternalNotification
            authorization_request_pending = InternalNotification.objects.filter(
                message__contains=f"Record ID: {record.id}",
                is_read=False
            ).filter(
                message__contains="SURGERY"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                    f"Please contact the desk office to obtain authorization for Surgery services."
                )

    context = {
        'record': record,
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'surgery/surgery_record_detail.html', context)


@login_required
def edit_surgery_record(request, record_id):
    """View to edit an existing surgery record"""
    record = get_object_or_404(SurgeryRecord, id=record_id)

    if request.method == 'POST':
        form = SurgeryRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Surgery record updated successfully.')
            return redirect('surgery:surgery_record_detail', record_id=record.id)
    else:
        form = SurgeryRecordForm(instance=record)

    # **NHIA AUTHORIZATION CHECK**
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

            # Check for pending authorization request
            from core.models import InternalNotification
            authorization_request_pending = InternalNotification.objects.filter(
                message__contains=f"Record ID: {record.id}",
                is_read=False
            ).filter(
                message__contains="SURGERY"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                    f"Please contact the desk office to obtain authorization for Surgery services."
                )

    context = {
        'form': form,
        'record': record,
        'title': 'Edit Surgery Record',
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'surgery/surgery_record_form.html', context)


@login_required
def delete_surgery_record(request, record_id):
    """View to delete a surgery record"""
    record = get_object_or_404(SurgeryRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Surgery record deleted successfully.')
        return redirect('surgery:surgery_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'surgery/surgery_record_confirm_delete.html', context)


@login_required
def search_surgery_patients(request):
    """AJAX view for searching patients in Surgery module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)


@login_required
def create_prescription_for_surgery(request, record_id):
    """Create a prescription for a Surgery patient"""
    record = get_object_or_404(SurgeryRecord, id=record_id)
    
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
                    return redirect('surgery:surgery_record_detail', record_id=record.id)
                    
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
    return render(request, 'surgery/create_prescription.html', context)


# Clinical Notes Views

@login_required
def add_clinical_note(request, record_id):
    """Add a clinical note (SOAP format) to a surgery record"""
    record = get_object_or_404(SurgeryRecord, id=record_id)

    if request.method == 'POST':
        form = SurgeryClinicalNoteForm(request.POST)
        if form.is_valid():
            clinical_note = form.save(commit=False)
            clinical_note.surgery_record = record
            clinical_note.created_by = request.user
            clinical_note.save()
            messages.success(request, 'Clinical note added successfully.')
            return redirect('surgery:record_detail', record_id=record.pk)
    else:
        form = SurgeryClinicalNoteForm()

    context = {
        'form': form,
        'record': record,
        'title': 'Add Clinical Note'
    }
    return render(request, 'surgery/clinical_note_form.html', context)


@login_required
def edit_clinical_note(request, note_id):
    """Edit an existing clinical note"""
    note = get_object_or_404(SurgeryClinicalNote, id=note_id)
    record = note.surgery_record

    if request.method == 'POST':
        form = SurgeryClinicalNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clinical note updated successfully.')
            return redirect('surgery:record_detail', record_id=record.pk)
    else:
        form = SurgeryClinicalNoteForm(instance=note)

    context = {
        'form': form,
        'note': note,
        'record': record,
        'title': 'Edit Clinical Note'
    }
    return render(request, 'surgery/clinical_note_form.html', context)


@login_required
def delete_clinical_note(request, note_id):
    """Delete a clinical note"""
    note = get_object_or_404(SurgeryClinicalNote, id=note_id)
    record_id = note.surgery_record.pk

    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Clinical note deleted successfully.')
        return redirect('surgery:record_detail', record_id=record_id)

    context = {
        'note': note
    }
    return render(request, 'surgery/clinical_note_confirm_delete.html', context)


@login_required
def view_clinical_note(request, note_id):
    """View a specific clinical note"""
    note = get_object_or_404(SurgeryClinicalNote, id=note_id)

    context = {
        'note': note,
        'record': note.surgery_record
    }
    return render(request, 'surgery/clinical_note_detail.html', context)
