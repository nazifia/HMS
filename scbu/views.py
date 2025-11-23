from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import ScbuRecord
from .forms import ScbuRecordForm, ScbuRecordSearchForm
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
@department_access_required('SCBU')
def scbu_dashboard(request):
    """Enhanced Dashboard for SCBU department with charts and neonatal care metrics"""
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
        record_model=ScbuRecord,
        record_queryset=ScbuRecord.objects.all(),
        priority_field=None,
        status_field=None,
        completed_status=None
    )

    # SCBU-specific statistics
    today = timezone.now().date()
    week_end = today + timedelta(days=7)

    # Total admissions
    total_admissions = ScbuRecord.objects.count()

    # Current admissions (all records since no discharge status field exists)
    current_admissions = ScbuRecord.objects.count()

    # Admissions today
    admissions_today = ScbuRecord.objects.filter(
        visit_date__date=today
    ).count()

    # Follow-ups due this week
    followups_due = ScbuRecord.objects.filter(
        follow_up_required=True,
        follow_up_date__gte=today,
        follow_up_date__lte=week_end
    ).count()

    # Average birth weight
    avg_birth_weight = ScbuRecord.objects.aggregate(avg=Avg('birth_weight'))['avg']
    avg_birth_weight = round(avg_birth_weight, 2) if avg_birth_weight else 0

    # Premature babies (gestational age < 37 weeks)
    premature_babies = ScbuRecord.objects.filter(
        gestational_age__lt=37
    ).count()

    # Low birth weight babies (<2.5kg)
    low_birth_weight = ScbuRecord.objects.filter(
        birth_weight__lt=2.5
    ).count()

    # Babies on respiratory support
    respiratory_support_count = ScbuRecord.objects.filter(
        respiratory_support=True
    ).count()

    # Babies with infection
    infection_count = ScbuRecord.objects.filter(
        infection_status=True
    ).count()

    # Average APGAR scores
    avg_apgar_1min = ScbuRecord.objects.aggregate(avg=Avg('apgar_score_1min'))['avg']
    avg_apgar_1min = round(avg_apgar_1min, 1) if avg_apgar_1min else 0

    avg_apgar_5min = ScbuRecord.objects.aggregate(avg=Avg('apgar_score_5min'))['avg']
    avg_apgar_5min = round(avg_apgar_5min, 1) if avg_apgar_5min else 0

    # Common diagnoses (top 5)
    diagnosis_data = ScbuRecord.objects.filter(
        diagnosis__isnull=False
    ).exclude(diagnosis='').values('diagnosis').annotate(count=Count('id')).order_by('-count')[:5]
    diagnosis_labels = [item['diagnosis'][:30] for item in diagnosis_data]
    diagnosis_counts = [item['count'] for item in diagnosis_data]

    # Get recent records with patient info
    recent_records = ScbuRecord.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]

    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)

    # Add to context
    context.update({
        'total_admissions': total_admissions,
        'current_admissions': current_admissions,
        'admissions_today': admissions_today,
        'followups_due': followups_due,
        'avg_birth_weight': avg_birth_weight,
        'premature_babies': premature_babies,
        'low_birth_weight': low_birth_weight,
        'respiratory_support_count': respiratory_support_count,
        'infection_count': infection_count,
        'avg_apgar_1min': avg_apgar_1min,
        'avg_apgar_5min': avg_apgar_5min,
        'diagnosis_labels': json.dumps(diagnosis_labels),
        'diagnosis_counts': json.dumps(diagnosis_counts),
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
    })

    return render(request, 'scbu/dashboard.html', context)


@login_required
def scbu_records_list(request):
    """View to list all scbu records with search and pagination"""
    records = ScbuRecord.objects.select_related('patient', 'doctor').all()
    
    search_form = ScbuRecordSearchForm(request.GET)
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
    return render(request, 'scbu/scbu_records_list.html', context)

@login_required
def create_scbu_record(request):
    """View to create a new scbu record"""
    if request.method == 'POST':
        form = ScbuRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'SCBU record created successfully.')
            return redirect('scbu:scbu_record_detail', record_id=record.id)
    else:
        form = ScbuRecordForm()
    
    context = {
        'form': form,
        'title': 'Create SCBU Record'
    }
    return render(request, 'scbu/scbu_record_form.html', context)

@login_required
def scbu_record_detail(request, record_id):
    """View to display details of a specific scbu record"""
    record = get_object_or_404(
        ScbuRecord.objects.select_related('patient', 'doctor'),
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
                message__contains="SCBU"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                    f"Please contact the desk office to obtain authorization for SCBU services."
                )

    context = {
        'record': record,
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'scbu/scbu_record_detail.html', context)

@login_required
def edit_scbu_record(request, record_id):
    """View to edit an existing scbu record"""
    record = get_object_or_404(ScbuRecord, id=record_id)

    if request.method == 'POST':
        form = ScbuRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'SCBU record updated successfully.')
            return redirect('scbu:scbu_record_detail', record_id=record.id)
    else:
        form = ScbuRecordForm(instance=record)

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
                message__contains="SCBU"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                    f"Please contact the desk office to obtain authorization for SCBU services."
                )

    context = {
        'form': form,
        'record': record,
        'title': 'Edit SCBU Record',
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'scbu/scbu_record_form.html', context)

@login_required
def delete_scbu_record(request, record_id):
    """View to delete a scbu record"""
    record = get_object_or_404(ScbuRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'SCBU record deleted successfully.')
        return redirect('scbu:scbu_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'scbu/scbu_record_confirm_delete.html', context)

@login_required
def search_scbu_patients(request):
    """AJAX view for searching patients in SCBU module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)


@login_required
def create_prescription_for_scbu(request, record_id):
    """Create a prescription for an SCBU patient"""
    record = get_object_or_404(ScbuRecord, id=record_id)
    
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
                    return redirect('scbu:scbu_record_detail', record_id=record.id)
                    
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
    return render(request, 'scbu/create_prescription.html', context)