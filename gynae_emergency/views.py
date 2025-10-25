from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import Gynae_emergencyRecord
from .forms import Gynae_emergencyRecordForm, GynaeEmergencyRecordSearchForm
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
@department_access_required('Gynae Emergency')
def gynae_emergency_dashboard(request):
    """Enhanced Dashboard for Gynae Emergency department with charts and emergency metrics"""
    from django.db.models import Count, Avg, Q, F, ExpressionWrapper, DurationField
    from datetime import timedelta

    user_department = get_user_department(request.user)

    if not user_department:
        messages.error(request, "You must be assigned to a department.")
        return redirect('dashboard:dashboard')

    # Build enhanced context with charts and trends
    context = build_enhanced_dashboard_context(
        department=user_department,
        record_model=Gynae_emergencyRecord,
        record_queryset=Gynae_emergencyRecord.objects.all(),
        priority_field=None,
        status_field='status',
        completed_status='discharged'
    )

    # Gynae Emergency-specific statistics
    today = timezone.now().date()

    # Emergency cases today
    emergencies_today = Gynae_emergencyRecord.objects.filter(
        visit_date__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()

    # Total emergency cases
    total_emergencies = Gynae_emergencyRecord.objects.count()

    # Emergency cases this week
    week_start = today - timedelta(days=today.weekday())
    emergencies_this_week = Gynae_emergencyRecord.objects.filter(
        visit_date__gte=week_start
    ).count()

    # Common emergency types (top 5)
    emergency_type_data = Gynae_emergencyRecord.objects.filter(
        emergency_type__isnull=False
    ).exclude(emergency_type='').values('emergency_type').annotate(count=Count('id')).order_by('-count')[:5]
    emergency_type_labels = [item['emergency_type'][:30] for item in emergency_type_data]
    emergency_type_counts = [item['count'] for item in emergency_type_data]

    # Get recent records with patient info
    recent_records = Gynae_emergencyRecord.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]

    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)

    # Add to context
    context.update({
        'emergencies_today': emergencies_today,
        'total_emergencies': total_emergencies,
        'emergencies_this_week': emergencies_this_week,
        'emergency_type_labels': json.dumps(emergency_type_labels),
        'emergency_type_counts': json.dumps(emergency_type_counts),
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
    })

    return render(request, 'gynae_emergency/dashboard.html', context)


@login_required
def gynae_emergency_records_list(request):
    """View to list all gynae emergency records with search and pagination"""
    records = Gynae_emergencyRecord.objects.select_related('patient', 'doctor').all()
    
    search_form = GynaeEmergencyRecordSearchForm(request.GET)
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
    return render(request, 'gynae_emergency/gynae_emergency_records_list.html', context)

@login_required
def create_gynae_emergency_record(request):
    """View to create a new gynae emergency record"""
    if request.method == 'POST':
        form = Gynae_emergencyRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Gynae Emergency record created successfully.')
            return redirect('gynae_emergency:gynae_emergency_record_detail', record_id=record.id)
    else:
        form = Gynae_emergencyRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Gynae Emergency Record'
    }
    return render(request, 'gynae_emergency/gynae_emergency_record_form.html', context)

@login_required
def gynae_emergency_record_detail(request, record_id):
    """View to display details of a specific gynae emergency record"""
    record = get_object_or_404(
        Gynae_emergencyRecord.objects.select_related('patient', 'doctor'), 
        id=record_id
    )
    
    # Get prescriptions for this patient
    prescriptions = Prescription.objects.filter(patient=record.patient).order_by('-prescription_date')[:5]
    
    context = {
        'record': record,
        'prescriptions': prescriptions,
    }
    return render(request, 'gynae_emergency/gynae_emergency_record_detail.html', context)

@login_required
def edit_gynae_emergency_record(request, record_id):
    """View to edit an existing gynae emergency record"""
    record = get_object_or_404(Gynae_emergencyRecord, id=record_id)
    
    if request.method == 'POST':
        form = Gynae_emergencyRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gynae Emergency record updated successfully.')
            return redirect('gynae_emergency:gynae_emergency_record_detail', record_id=record.id)
    else:
        form = Gynae_emergencyRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Gynae Emergency Record'
    }
    return render(request, 'gynae_emergency/gynae_emergency_record_form.html', context)

@login_required
def delete_gynae_emergency_record(request, record_id):
    """View to delete a gynae emergency record"""
    record = get_object_or_404(Gynae_emergencyRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Gynae Emergency record deleted successfully.')
        return redirect('gynae_emergency:gynae_emergency_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'gynae_emergency/gynae_emergency_record_confirm_delete.html', context)

@login_required
def search_gynae_emergency_patients(request):
    """AJAX view for searching patients in Gynae Emergency module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)

@login_required
def create_prescription_for_gynae_emergency(request, record_id):
    """Create a prescription for a Gynae Emergency patient"""
    record = get_object_or_404(Gynae_emergencyRecord, id=record_id)
    
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
                    return redirect('gynae_emergency:gynae_emergency_record_detail', record_id=record.id)
                    
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
    return render(request, 'gynae_emergency/create_prescription.html', context)