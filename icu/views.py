from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import IcuRecord
from .forms import IcuRecordForm, IcuRecordSearchForm
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
@department_access_required('ICU')
def icu_dashboard(request):
    """Enhanced Dashboard for ICU department with charts and critical care metrics"""
    from django.db.models import Count, Avg, Q
    from datetime import timedelta

    user_department = get_user_department(request.user)

    # Superusers can access all departments without assignment
    if not user_department and not request.user.is_superuser:
        messages.error(request, "You must be assigned to a department.")
        return redirect('dashboard:dashboard')

    # Build enhanced context with charts and trends
    # ICURecord uses 'visit_date' instead of 'created_at'
    context = build_enhanced_dashboard_context(
        department=user_department,
        record_model=IcuRecord,
        record_queryset=IcuRecord.objects.all(),
        priority_field=None,  # ICU records don't have priority field
        status_field=None,  # ICU records don't have status field
        completed_status='discharged',
        date_field='visit_date'  # ICURecord uses visit_date instead of created_at
    )

    # ICU-specific statistics
    today = timezone.now().date()

    # Current admissions (active patients) - last 7 days
    week_ago = today - timedelta(days=7)
    current_admissions = IcuRecord.objects.filter(
        visit_date__date__gte=week_ago
    ).count()

    # Critical patients (GCS score < 8 indicates severe impairment)
    critical_patients = IcuRecord.objects.filter(
        gcs_score__lt=8,
        visit_date__date__gte=week_ago
    ).count()

    # Patients on ventilator
    on_ventilator = IcuRecord.objects.filter(
        mechanical_ventilation=True,
        visit_date__date__gte=week_ago
    ).count()

    # Patients on dialysis
    on_dialysis = IcuRecord.objects.filter(
        dialysis_required=True,
        visit_date__date__gte=week_ago
    ).count()

    # Average GCS score for recent patients
    avg_gcs = IcuRecord.objects.filter(
        visit_date__date__gte=week_ago
    ).aggregate(avg=Avg('gcs_score'))['avg']
    avg_gcs_score = round(avg_gcs, 1) if avg_gcs else 0

    # Admissions today (using visit_date as ICURecord doesn't have admission_date)
    admissions_today = IcuRecord.objects.filter(
        visit_date__date=today
    ).count()

    # Note: ICURecord doesn't have discharge_date field, so we can't track discharges
    discharges_today = 0

    # Bed occupancy rate (assuming 10 beds - adjust as needed)
    total_beds = 10
    occupancy_rate = (current_admissions / total_beds * 100) if total_beds > 0 else 0

    # GCS distribution for chart (recent patients only - last 7 days)
    gcs_ranges = [
        ('Severe (3-8)', IcuRecord.objects.filter(gcs_score__gte=3, gcs_score__lte=8, visit_date__date__gte=week_ago).count()),
        ('Moderate (9-12)', IcuRecord.objects.filter(gcs_score__gte=9, gcs_score__lte=12, visit_date__date__gte=week_ago).count()),
        ('Mild (13-15)', IcuRecord.objects.filter(gcs_score__gte=13, gcs_score__lte=15, visit_date__date__gte=week_ago).count()),
    ]
    gcs_labels = [item[0] for item in gcs_ranges]
    gcs_counts = [item[1] for item in gcs_ranges]

    # Equipment usage (recent patients only - last 7 days)
    equipment_data = [
        ('Ventilator', on_ventilator),
        ('Dialysis', on_dialysis),
        ('Vasopressor', IcuRecord.objects.filter(vasopressor_use=True, visit_date__date__gte=week_ago).count()),
    ]
    equipment_labels = [item[0] for item in equipment_data]
    equipment_counts = [item[1] for item in equipment_data]

    # Get recent records with patient info
    recent_records = IcuRecord.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]

    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)

    # Add to context
    context.update({
        'current_admissions': current_admissions,
        'critical_patients': critical_patients,
        'on_ventilator': on_ventilator,
        'on_dialysis': on_dialysis,
        'avg_gcs_score': avg_gcs_score,
        'admissions_today': admissions_today,
        'discharges_today': discharges_today,
        'occupancy_rate': round(occupancy_rate, 1),
        'total_beds': total_beds,
        'gcs_labels': json.dumps(gcs_labels),
        'gcs_counts': json.dumps(gcs_counts),
        'equipment_labels': json.dumps(equipment_labels),
        'equipment_counts': json.dumps(equipment_counts),
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
    })

    return render(request, 'icu/dashboard.html', context)


@login_required
def icu_records_list(request):
    """View to list all icu records with search and pagination"""
    records = IcuRecord.objects.select_related('patient', 'doctor').all()
    
    search_form = IcuRecordSearchForm(request.GET)
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
    return render(request, 'icu/icu_records_list.html', context)

@login_required
def create_icu_record(request):
    """View to create a new icu record"""
    if request.method == 'POST':
        form = IcuRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'ICU record created successfully.')
            return redirect('icu:icu_record_detail', record_id=record.id)
    else:
        form = IcuRecordForm()
    
    context = {
        'form': form,
        'title': 'Create ICU Record'
    }
    return render(request, 'icu/icu_record_form.html', context)

@login_required
def icu_record_detail(request, record_id):
    """View to display details of a specific icu record"""
    record = get_object_or_404(
        IcuRecord.objects.select_related('patient', 'doctor'),
        id=record_id
    )

    # Get prescriptions for this patient
    prescriptions = Prescription.objects.filter(patient=record.patient).order_by('-prescription_date')[:5]

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
                message__contains="ICU"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                    f"Please contact the desk office to obtain authorization for ICU services."
                )

    context = {
        'record': record,
        'prescriptions': prescriptions,
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'icu/icu_record_detail.html', context)

@login_required
def edit_icu_record(request, record_id):
    """View to edit an existing icu record"""
    record = get_object_or_404(IcuRecord, id=record_id)

    if request.method == 'POST':
        form = IcuRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'ICU record updated successfully.')
            return redirect('icu:icu_record_detail', record_id=record.id)
    else:
        form = IcuRecordForm(instance=record)

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
                message__contains="ICU"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                    f"Please contact the desk office to obtain authorization for ICU services."
                )

    context = {
        'form': form,
        'record': record,
        'title': 'Edit ICU Record',
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'icu/icu_record_form.html', context)

@login_required
def delete_icu_record(request, record_id):
    """View to delete a icu record"""
    record = get_object_or_404(IcuRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'ICU record deleted successfully.')
        return redirect('icu:icu_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'icu/icu_record_confirm_delete.html', context)

@login_required
def search_icu_patients(request):
    """AJAX view for searching patients in ICU module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)

@login_required
def create_prescription_for_icu(request, record_id):
    """Create a prescription for an ICU patient"""
    record = get_object_or_404(IcuRecord, id=record_id)
    
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
                    return redirect('icu:icu_record_detail', record_id=record.id)
                    
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
    return render(request, 'icu/create_prescription.html', context)