from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import Family_planningRecord
from .forms import Family_planningRecordForm, FamilyPlanningRecordSearchForm
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
@department_access_required('Family Planning')
def family_planning_dashboard(request):
    """Enhanced Dashboard for Family Planning department with charts and contraceptive metrics"""
    from django.db.models import Count, Q
    from datetime import timedelta

    user_department = get_user_department(request.user)

    # Superusers can access all departments without assignment
    if not user_department and not request.user.is_superuser:
        messages.error(request, "You must be assigned to a department.")
        return redirect('dashboard:dashboard')

    # Build enhanced context with charts and trends
    context = build_enhanced_dashboard_context(
        department=user_department,
        record_model=Family_planningRecord,
        record_queryset=Family_planningRecord.objects.all(),
        priority_field=None,
        status_field='status',
        completed_status='completed'
    )

    # Family Planning-specific statistics
    today = timezone.now().date()
    week_end = today + timedelta(days=7)

    # Visits today
    visits_today = Family_planningRecord.objects.filter(
        visit_date__date=today
    ).count()

    # Contraceptive method distribution (top 5)
    method_data = Family_planningRecord.objects.filter(
        method_used__isnull=False
    ).exclude(method_used='').values('method_used').annotate(count=Count('id')).order_by('-count')[:5]
    method_labels = [item['method_used'] for item in method_data]
    method_counts = [item['count'] for item in method_data]

    # Education sessions this month
    month_start = today.replace(day=1)
    education_sessions_month = Family_planningRecord.objects.filter(
        visit_date__date__gte=month_start,
        education_provided=True
    ).count()

    # New clients this month (based on first visit date)
    new_clients_month = Family_planningRecord.objects.filter(
        visit_date__date__gte=month_start
    ).values('patient').distinct().count()

    # Follow-up visits due this week
    followups_due = Family_planningRecord.objects.filter(
        follow_up_date__gte=today,
        follow_up_date__lte=week_end
    ).count()

    # Active clients (on contraceptives)
    # Count patients with recent visits (last 6 months) or with follow-ups required
    six_months_ago = today - timedelta(days=180)
    active_clients = Family_planningRecord.objects.filter(
        Q(visit_date__date__gte=six_months_ago) | Q(follow_up_required=True)
    ).values('patient').distinct().count()

    # Get recent records with patient info
    recent_records = Family_planningRecord.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]

    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)

    # Add to context
    context.update({
        'visits_today': visits_today,
        'method_labels': json.dumps(method_labels),
        'method_counts': json.dumps(method_counts),
        'education_sessions_month': education_sessions_month,
        'new_clients_month': new_clients_month,
        'followups_due': followups_due,
        'active_clients': active_clients,
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
    })

    return render(request, 'family_planning/dashboard.html', context)


@login_required
def family_planning_records_list(request):
    """View to list all family planning records with search and pagination"""
    records = Family_planningRecord.objects.select_related('patient', 'doctor').all()
    
    search_form = FamilyPlanningRecordSearchForm(request.GET)
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
    return render(request, 'family_planning/family_planning_records_list.html', context)

@login_required
def create_family_planning_record(request):
    """View to create a new family planning record"""
    if request.method == 'POST':
        form = Family_planningRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Family Planning record created successfully.')
            return redirect('family_planning:family_planning_record_detail', record_id=record.id)
    else:
        form = Family_planningRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Family Planning Record'
    }
    return render(request, 'family_planning/family_planning_record_form.html', context)

@login_required
def family_planning_record_detail(request, record_id):
    """View to display details of a specific family planning record"""
    record = get_object_or_404(
        Family_planningRecord.objects.select_related('patient', 'doctor'),
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
                message__contains="Family Planning"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                    f"Please contact the desk office to obtain authorization for family planning services."
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
    return render(request, 'family_planning/family_planning_record_detail.html', context)

@login_required
def edit_family_planning_record(request, record_id):
    """View to edit an existing family planning record"""
    record = get_object_or_404(Family_planningRecord, id=record_id)

    if request.method == 'POST':
        form = Family_planningRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Family Planning record updated successfully.')
            return redirect('family_planning:family_planning_record_detail', record_id=record.id)
    else:
        form = Family_planningRecordForm(instance=record)

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
                message__contains="Family Planning"
            ).exists()

            if not authorization_request_pending:
                messages.warning(
                    request,
                    f"This is an NHIA patient. An authorization code from the desk office is required before proceeding with treatment or billing. "
                    f"Please contact the desk office to obtain authorization for family planning services."
                )

    context = {
        'form': form,
        'record': record,
        'title': 'Edit Family Planning Record',
        'is_nhia_patient': is_nhia_patient,
        'requires_authorization': requires_authorization,
        'authorization_valid': authorization_valid,
        'authorization_message': authorization_message,
        'authorization_request_pending': authorization_request_pending,
    }
    return render(request, 'family_planning/family_planning_record_form.html', context)

@login_required
def delete_family_planning_record(request, record_id):
    """View to delete a family planning record"""
    record = get_object_or_404(Family_planningRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Family Planning record deleted successfully.')
        return redirect('family_planning:family_planning_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'family_planning/family_planning_record_confirm_delete.html', context)

@login_required
def search_family_planning_patients(request):
    """AJAX view for searching patients in Family Planning module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)

@login_required
def create_prescription_for_family_planning(request, record_id):
    """Create a prescription for a Family Planning patient"""
    record = get_object_or_404(Family_planningRecord, id=record_id)
    
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
                    return redirect('family_planning:family_planning_record_detail', record_id=record.id)
                    
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
    return render(request, 'family_planning/create_prescription.html', context)