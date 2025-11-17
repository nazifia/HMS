from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import OncologyRecord
from .forms import OncologyRecordForm, OncologyRecordSearchForm
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
@department_access_required('Oncology')
def oncology_dashboard(request):
    """Enhanced Dashboard for Oncology department with charts and cancer care metrics"""
    from django.db.models import Count, Avg, Q
    from datetime import timedelta

    user_department = get_user_department(request.user)

    if not user_department:
        messages.error(request, "You must be assigned to a department.")
        return redirect('dashboard:dashboard')

    # Build enhanced context with charts and trends
    context = build_enhanced_dashboard_context(
        department=user_department,
        record_model=OncologyRecord,
        record_queryset=OncologyRecord.objects.all(),
        priority_field=None,
        status_field='status',
        completed_status='completed'
    )

    # Oncology-specific statistics
    today = timezone.now().date()
    six_months_ago = today - timedelta(days=180)

    # Active patients (currently under treatment)
    # Count patients with recent visits (last 6 months) or with follow-ups required
    active_patients = OncologyRecord.objects.filter(
        Q(visit_date__gte=six_months_ago) | Q(follow_up_required=True)
    ).values('patient').distinct().count()

    # Patients by cancer type (top 5)
    cancer_type_data = OncologyRecord.objects.filter(
        cancer_type__isnull=False
    ).exclude(cancer_type='').values('cancer_type').annotate(count=Count('id')).order_by('-count')[:5]
    cancer_type_labels = [item['cancer_type'] for item in cancer_type_data]
    cancer_type_counts = [item['count'] for item in cancer_type_data]

    # Patients by stage
    stage_1 = OncologyRecord.objects.filter(stage='Stage I').count()
    stage_2 = OncologyRecord.objects.filter(stage='Stage II').count()
    stage_3 = OncologyRecord.objects.filter(stage='Stage III').count()
    stage_4 = OncologyRecord.objects.filter(stage='Stage IV').count()

    # Stage distribution for chart
    stage_labels = ['Stage I', 'Stage II', 'Stage III', 'Stage IV']
    stage_counts = [stage_1, stage_2, stage_3, stage_4]
    stage_colors = ['#28a745', '#ffc107', '#fd7e14', '#dc3545']

    # Chemotherapy sessions this month
    month_start = today.replace(day=1)
    chemo_sessions_month = OncologyRecord.objects.filter(
        visit_date__date__gte=month_start,
        chemotherapy_cycle__isnull=False
    ).count()

    # Radiation treatments this month
    radiation_treatments_month = OncologyRecord.objects.filter(
        visit_date__date__gte=month_start,
        radiation_dose__isnull=False
    ).count()

    # Patients with metastasis
    metastasis_patients = OncologyRecord.objects.filter(
        metastasis=True
    ).values('patient').distinct().count()

    # Average tumor size
    avg_tumor_size = OncologyRecord.objects.filter(
        tumor_size__isnull=False
    ).aggregate(avg=Avg('tumor_size'))['avg']
    avg_tumor_size = round(avg_tumor_size, 1) if avg_tumor_size else 0

    # Get recent records with patient info
    recent_records = OncologyRecord.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]

    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)

    # Add to context
    context.update({
        'active_patients': active_patients,
        'cancer_type_labels': json.dumps(cancer_type_labels),
        'cancer_type_counts': json.dumps(cancer_type_counts),
        'stage_1': stage_1,
        'stage_2': stage_2,
        'stage_3': stage_3,
        'stage_4': stage_4,
        'stage_labels': json.dumps(stage_labels),
        'stage_counts': json.dumps(stage_counts),
        'stage_colors': json.dumps(stage_colors),
        'chemo_sessions_month': chemo_sessions_month,
        'radiation_treatments_month': radiation_treatments_month,
        'metastasis_patients': metastasis_patients,
        'avg_tumor_size': avg_tumor_size,
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
    })

    return render(request, 'oncology/dashboard.html', context)


@login_required
def oncology_records_list(request):
    """View to list all oncology records with search and pagination"""
    records = OncologyRecord.objects.select_related('patient', 'doctor').all()
    
    search_form = OncologyRecordSearchForm(request.GET)
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
    return render(request, 'oncology/oncology_records_list.html', context)

@login_required
def create_oncology_record(request):
    """View to create a new oncology record"""
    if request.method == 'POST':
        form = OncologyRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Oncology record created successfully.')
            return redirect('oncology:oncology_record_detail', record_id=record.id)
    else:
        form = OncologyRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Oncology Record'
    }
    return render(request, 'oncology/oncology_record_form.html', context)

@login_required
def oncology_record_detail(request, record_id):
    """View to display details of a specific oncology record"""
    record = get_object_or_404(
        OncologyRecord.objects.select_related('patient', 'doctor'),
        id=record_id
    )

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
                f"Please contact the desk office to obtain authorization for oncology services."
            )

    context = {
        'record': record,
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
    }
    return render(request, 'oncology/oncology_record_detail.html', context)

@login_required
def edit_oncology_record(request, record_id):
    """View to edit an existing oncology record"""
    record = get_object_or_404(OncologyRecord, id=record_id)
    
    if request.method == 'POST':
        form = OncologyRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Oncology record updated successfully.')
            return redirect('oncology:oncology_record_detail', record_id=record.id)
    else:
        form = OncologyRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Oncology Record'
    }
    return render(request, 'oncology/oncology_record_form.html', context)

@login_required
def delete_oncology_record(request, record_id):
    """View to delete a oncology record"""
    record = get_object_or_404(OncologyRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Oncology record deleted successfully.')
        return redirect('oncology:oncology_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'oncology/oncology_record_confirm_delete.html', context)

@login_required
def search_oncology_patients(request):
    """AJAX view for searching patients in Oncology module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)


@login_required
def create_prescription_for_oncology(request, record_id):
    """Create a prescription for an oncology patient"""
    record = get_object_or_404(OncologyRecord, id=record_id)
    
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
                    return redirect('oncology:oncology_record_detail', record_id=record.id)
                    
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
    return render(request, 'oncology/create_prescription.html', context)