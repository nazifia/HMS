from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import GeneralMedicineRecord, GeneralMedicineClinicalNote
from .forms import GeneralMedicineRecordForm, GeneralMedicineRecordSearchForm, GeneralMedicineClinicalNoteForm
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
@department_access_required('General Medicine')
def general_medicine_dashboard(request):
    """Enhanced Dashboard for General Medicine department with charts and metrics"""
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
        record_model=GeneralMedicineRecord,
        record_queryset=GeneralMedicineRecord.objects.all(),
        priority_field=None,
        status_field=None,
        completed_status=None
    )

    # General Medicine-specific statistics
    today = timezone.now().date()
    week_end = today + timedelta(days=7)

    # Total visits
    total_visits = GeneralMedicineRecord.objects.count()

    # Visits today
    visits_today = GeneralMedicineRecord.objects.filter(
        visit_date__date=today
    ).count()

    # Follow-ups due this week
    followups_due = GeneralMedicineRecord.objects.filter(
        follow_up_required=True,
        follow_up_date__gte=today,
        follow_up_date__lte=week_end
    ).count()

    # Average BMI
    avg_bmi = GeneralMedicineRecord.objects.aggregate(avg=Avg('bmi'))['avg']
    avg_bmi = round(avg_bmi, 2) if avg_bmi else 0

    # Hypertensive patients (BP >= 140/90)
    hypertensive_count = GeneralMedicineRecord.objects.filter(
        blood_pressure_systolic__gte=140
    ).filter(
        blood_pressure_diastolic__gte=90
    ).count()

    # Patients with fever (temp > 37.5)
    fever_count = GeneralMedicineRecord.objects.filter(
        temperature__gt=37.5
    ).count()

    # Patients with low oxygen saturation (< 95%)
    low_oxygen_count = GeneralMedicineRecord.objects.filter(
        oxygen_saturation__lt=95
    ).count()

    # Common diagnoses (top 5)
    diagnosis_data = GeneralMedicineRecord.objects.filter(
        diagnosis__isnull=False
    ).exclude(diagnosis='').values('diagnosis').annotate(count=Count('id')).order_by('-count')[:5]
    diagnosis_labels = [item['diagnosis'][:30] for item in diagnosis_data]
    diagnosis_counts = [item['count'] for item in diagnosis_data]

    # Get recent records with patient info
    recent_records = GeneralMedicineRecord.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]

    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)

    # Add to context
    context.update({
        'total_visits': total_visits,
        'visits_today': visits_today,
        'followups_due': followups_due,
        'avg_bmi': avg_bmi,
        'hypertensive_count': hypertensive_count,
        'fever_count': fever_count,
        'low_oxygen_count': low_oxygen_count,
        'diagnosis_labels': json.dumps(diagnosis_labels),
        'diagnosis_counts': json.dumps(diagnosis_counts),
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
    })

    return render(request, 'general_medicine/dashboard.html', context)


@login_required
def general_medicine_records_list(request):
    """View to list all general medicine records with search and pagination"""
    records = GeneralMedicineRecord.objects.select_related('patient', 'doctor').all()
    
    search_form = GeneralMedicineRecordSearchForm(request.GET)
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
    return render(request, 'general_medicine/general_medicine_records_list.html', context)


@login_required
def create_general_medicine_record(request):
    """View to create a new general medicine record"""
    if request.method == 'POST':
        form = GeneralMedicineRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'General Medicine record created successfully.')
            return redirect('general_medicine:general_medicine_record_detail', record_id=record.id)
    else:
        form = GeneralMedicineRecordForm()
    
    context = {
        'form': form,
        'title': 'Create General Medicine Record'
    }
    return render(request, 'general_medicine/general_medicine_record_form.html', context)


@login_required
def general_medicine_record_detail(request, record_id):
    """View to display details of a specific general medicine record"""
    record = get_object_or_404(
        GeneralMedicineRecord.objects.select_related('patient', 'doctor'),
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
                message__contains="GENERAL_MEDICINE"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                    f"Please contact the desk office to obtain authorization for General Medicine services."
                )

    context = {
        'record': record,
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'general_medicine/general_medicine_record_detail.html', context)


@login_required
def edit_general_medicine_record(request, record_id):
    """View to edit an existing general medicine record"""
    record = get_object_or_404(GeneralMedicineRecord, id=record_id)

    if request.method == 'POST':
        form = GeneralMedicineRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'General Medicine record updated successfully.')
            return redirect('general_medicine:general_medicine_record_detail', record_id=record.id)
    else:
        form = GeneralMedicineRecordForm(instance=record)

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
                message__contains="GENERAL_MEDICINE"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                    f"Please contact the desk office to obtain authorization for General Medicine services."
                )

    context = {
        'form': form,
        'record': record,
        'title': 'Edit General Medicine Record',
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'general_medicine/general_medicine_record_form.html', context)


@login_required
def delete_general_medicine_record(request, record_id):
    """View to delete a general medicine record"""
    record = get_object_or_404(GeneralMedicineRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'General Medicine record deleted successfully.')
        return redirect('general_medicine:general_medicine_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'general_medicine/general_medicine_record_confirm_delete.html', context)


@login_required
def search_general_medicine_patients(request):
    """AJAX view for searching patients in General Medicine module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)


@login_required
def create_prescription_for_general_medicine(request, record_id):
    """Create a prescription for a General Medicine patient"""
    record = get_object_or_404(GeneralMedicineRecord, id=record_id)
    
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
                    return redirect('general_medicine:general_medicine_record_detail', record_id=record.id)
                    
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
    return render(request, 'general_medicine/create_prescription.html', context)


# Clinical Notes Views

@login_required
def add_clinical_note(request, record_id):
    """Add a clinical note (SOAP format) to a general medicine record"""
    record = get_object_or_404(GeneralMedicineRecord, id=record_id)

    if request.method == 'POST':
        form = GeneralMedicineClinicalNoteForm(request.POST)
        if form.is_valid():
            clinical_note = form.save(commit=False)
            clinical_note.general_medicine_record = record
            clinical_note.created_by = request.user
            clinical_note.save()
            messages.success(request, 'Clinical note added successfully.')
            return redirect('general_medicine:record_detail', record_id=record.pk)
    else:
        form = GeneralMedicineClinicalNoteForm()

    context = {
        'form': form,
        'record': record,
        'title': 'Add Clinical Note'
    }
    return render(request, 'general_medicine/clinical_note_form.html', context)


@login_required
def edit_clinical_note(request, note_id):
    """Edit an existing clinical note"""
    note = get_object_or_404(GeneralMedicineClinicalNote, id=note_id)
    record = note.general_medicine_record

    if request.method == 'POST':
        form = GeneralMedicineClinicalNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clinical note updated successfully.')
            return redirect('general_medicine:record_detail', record_id=record.pk)
    else:
        form = GeneralMedicineClinicalNoteForm(instance=note)

    context = {
        'form': form,
        'note': note,
        'record': record,
        'title': 'Edit Clinical Note'
    }
    return render(request, 'general_medicine/clinical_note_form.html', context)


@login_required
def delete_clinical_note(request, note_id):
    """Delete a clinical note"""
    note = get_object_or_404(GeneralMedicineClinicalNote, id=note_id)
    record_id = note.general_medicine_record.pk

    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Clinical note deleted successfully.')
        return redirect('general_medicine:record_detail', record_id=record_id)

    context = {
        'note': note
    }
    return render(request, 'general_medicine/clinical_note_confirm_delete.html', context)


@login_required
def view_clinical_note(request, note_id):
    """View a specific clinical note"""
    note = get_object_or_404(GeneralMedicineClinicalNote, id=note_id)

    context = {
        'note': note,
        'record': note.general_medicine_record
    }
    return render(request, 'general_medicine/clinical_note_detail.html', context)
