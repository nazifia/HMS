from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import EntRecord
from .forms import EntRecordForm, EntRecordSearchForm
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
@department_access_required('ENT')
def ent_dashboard(request):
    """Enhanced Dashboard for ENT department with charts and ENT care metrics"""
    from django.db.models import Count, Q
    from datetime import timedelta

    user_department = get_user_department(request.user)

    if not user_department:
        messages.error(request, "You must be assigned to a department.")
        return redirect('dashboard:dashboard')

    # Build enhanced context with charts and trends
    context = build_enhanced_dashboard_context(
        department=user_department,
        record_model=EntRecord,
        record_queryset=EntRecord.objects.all(),
        priority_field=None,
        status_field='status',
        completed_status='completed'
    )

    # ENT-specific statistics
    today = timezone.now().date()
    week_end = today + timedelta(days=7)

    # Visits today
    visits_today = EntRecord.objects.filter(
        visit_date__date=today
    ).count()

    # Follow-ups due this week
    followups_due = EntRecord.objects.filter(
        follow_up_required=True,
        follow_up_date__gte=today,
        follow_up_date__lte=week_end
    ).count()

    # Common diagnoses (top 5)
    diagnosis_data = EntRecord.objects.filter(
        diagnosis__isnull=False
    ).exclude(diagnosis='').values('diagnosis').annotate(count=Count('id')).order_by('-count')[:5]
    diagnosis_labels = [item['diagnosis'][:30] for item in diagnosis_data]
    diagnosis_counts = [item['count'] for item in diagnosis_data]

    # Procedures performed this month
    month_start = today.replace(day=1)
    procedures_month = EntRecord.objects.filter(
        visit_date__date__gte=month_start,
        treatment_plan__isnull=False
    ).exclude(treatment_plan='').count()

    # Patients requiring surgery
    surgery_required = EntRecord.objects.filter(
        treatment_plan__icontains='surgery'
    ).count()

    # Emergency cases this week
    week_start = today - timedelta(days=today.weekday())
    emergency_cases = EntRecord.objects.filter(
        visit_date__date__gte=week_start,
        chief_complaint__icontains='emergency'
    ).count() + EntRecord.objects.filter(
        visit_date__date__gte=week_start,
        chief_complaint__icontains='acute'
    ).count()

    # Get recent records with patient info
    recent_records = EntRecord.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]

    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)

    # Add to context
    context.update({
        'visits_today': visits_today,
        'followups_due': followups_due,
        'diagnosis_labels': json.dumps(diagnosis_labels),
        'diagnosis_counts': json.dumps(diagnosis_counts),
        'procedures_month': procedures_month,
        'surgery_required': surgery_required,
        'emergency_cases': emergency_cases,
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
    })

    return render(request, 'ent/dashboard.html', context)


@login_required
def ent_records_list(request):
    """View to list all ent records with search and pagination"""
    records = EntRecord.objects.select_related('patient', 'doctor').all()
    
    search_form = EntRecordSearchForm(request.GET)
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
    return render(request, 'ent/ent_records_list.html', context)

@login_required
def create_ent_record(request):
    """View to create a new ent record"""
    if request.method == 'POST':
        form = EntRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'ENT record created successfully.')
            return redirect('ent:ent_record_detail', record_id=record.id)
    else:
        form = EntRecordForm()
    
    context = {
        'form': form,
        'title': 'Create ENT Record'
    }
    return render(request, 'ent/ent_record_form.html', context)

@login_required
def ent_record_detail(request, record_id):
    """View to display details of a specific ent record"""
    record = get_object_or_404(
        EntRecord.objects.select_related('patient', 'doctor'),
        id=record_id
    )

    # Get prescriptions for this patient
    prescriptions = Prescription.objects.filter(patient=record.patient).order_by('-prescription_date')[:5]

    # **NHIA AUTHORIZATION CHECK**
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
                f"Please contact the desk office to obtain authorization for ENT services."
            )

    context = {
        'record': record,
        'prescriptions': prescriptions,
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
    }
    return render(request, 'ent/ent_record_detail.html', context)

@login_required
def edit_ent_record(request, record_id):
    """View to edit an existing ent record"""
    record = get_object_or_404(EntRecord, id=record_id)
    
    if request.method == 'POST':
        form = EntRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'ENT record updated successfully.')
            return redirect('ent:ent_record_detail', record_id=record.id)
    else:
        form = EntRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit ENT Record'
    }
    return render(request, 'ent/ent_record_form.html', context)

@login_required
def delete_ent_record(request, record_id):
    """View to delete a ent record"""
    record = get_object_or_404(EntRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'ENT record deleted successfully.')
        return redirect('ent:ent_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'ent/ent_record_confirm_delete.html', context)

@login_required
def search_ent_patients(request):
    """AJAX view for searching patients in ENT module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)

@login_required
def create_prescription_for_ent(request, record_id):
    """Create a prescription for an ENT patient"""
    record = get_object_or_404(EntRecord, id=record_id)
    
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
                    return redirect('ent:ent_record_detail', record_id=record.id)
                    
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
    return render(request, 'ent/create_prescription.html', context)


@login_required
def delete_ent_record(request, record_id):
    """View to delete an ent record"""
    record = get_object_or_404(EntRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'ENT record deleted successfully.')
        return redirect('ent:ent_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'ent/ent_record_confirm_delete.html', context)
