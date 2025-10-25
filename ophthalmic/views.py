from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import OphthalmicRecord
from .forms import OphthalmicRecordForm, OphthalmicRecordSearchForm
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
@department_access_required('Ophthalmic')
def ophthalmic_dashboard(request):
    """Enhanced Dashboard for Ophthalmic department with charts and eye care metrics"""
    from django.db.models import Count, Avg, Q
    from datetime import timedelta

    user_department = get_user_department(request.user)

    if not user_department:
        messages.error(request, "You must be assigned to a department.")
        return redirect('dashboard:dashboard')

    # Build enhanced context with charts and trends
    context = build_enhanced_dashboard_context(
        department=user_department,
        record_model=OphthalmicRecord,
        record_queryset=OphthalmicRecord.objects.all(),
        priority_field=None,
        status_field='status',
        completed_status='completed'
    )

    # Ophthalmic-specific statistics
    today = timezone.now().date()
    week_end = today + timedelta(days=7)

    # Visits today
    visits_today = OphthalmicRecord.objects.filter(
        visit_date__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()

    # Follow-ups due this week
    followups_due = OphthalmicRecord.objects.filter(
        follow_up_required=True,
        follow_up_date__gte=today,
        follow_up_date__lte=week_end
    ).count()

    # Common diagnoses (top 5)
    diagnosis_data = OphthalmicRecord.objects.filter(
        diagnosis__isnull=False
    ).exclude(diagnosis='').values('diagnosis').annotate(count=Count('id')).order_by('-count')[:5]
    diagnosis_labels = [item['diagnosis'][:30] for item in diagnosis_data]  # Truncate long diagnoses
    diagnosis_counts = [item['count'] for item in diagnosis_data]

    # Visual acuity statistics (patients with poor vision)
    poor_vision_right = OphthalmicRecord.objects.filter(
        Q(visual_acuity_right__icontains='6/60') |
        Q(visual_acuity_right__icontains='CF') |
        Q(visual_acuity_right__icontains='HM')
    ).count()

    poor_vision_left = OphthalmicRecord.objects.filter(
        Q(visual_acuity_left__icontains='6/60') |
        Q(visual_acuity_left__icontains='CF') |
        Q(visual_acuity_left__icontains='HM')
    ).count()

    # Patients requiring surgery
    surgery_required = OphthalmicRecord.objects.filter(
        treatment_plan__icontains='surgery'
    ).count()

    # Patients with glaucoma (high IOP)
    high_iop_patients = OphthalmicRecord.objects.filter(
        Q(intraocular_pressure_right__gte=21) |
        Q(intraocular_pressure_left__gte=21)
    ).count()

    # Get recent records with patient info
    recent_records = OphthalmicRecord.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]

    # Categorize referrals
    categorized_referrals = categorize_referrals(user_department)

    # Add to context
    context.update({
        'visits_today': visits_today,
        'followups_due': followups_due,
        'diagnosis_labels': json.dumps(diagnosis_labels),
        'diagnosis_counts': json.dumps(diagnosis_counts),
        'poor_vision_right': poor_vision_right,
        'poor_vision_left': poor_vision_left,
        'surgery_required': surgery_required,
        'high_iop_patients': high_iop_patients,
        'recent_records': recent_records,
        'categorized_referrals': categorized_referrals,
    })

    return render(request, 'ophthalmic/dashboard.html', context)


@login_required
def ophthalmic_records_list(request):
    """View to list all ophthalmic records with search and pagination"""
    records = OphthalmicRecord.objects.select_related('patient', 'doctor').all()
    
    search_form = OphthalmicRecordSearchForm(request.GET)
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
    return render(request, 'ophthalmic/ophthalmic_records_list.html', context)

@login_required
def create_ophthalmic_record(request):
    """View to create a new ophthalmic record"""
    if request.method == 'POST':
        form = OphthalmicRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Ophthalmic record created successfully.')
            return redirect('ophthalmic:ophthalmic_record_detail', record_id=record.id)
    else:
        form = OphthalmicRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Ophthalmic Record'
    }
    return render(request, 'ophthalmic/ophthalmic_record_form.html', context)

@login_required
def ophthalmic_record_detail(request, record_id):
    """View to display details of a specific ophthalmic record"""
    record = get_object_or_404(
        OphthalmicRecord.objects.select_related('patient', 'doctor'), 
        id=record_id
    )
    
    context = {
        'record': record,
    }
    return render(request, 'ophthalmic/ophthalmic_record_detail.html', context)

@login_required
def edit_ophthalmic_record(request, record_id):
    """View to edit an existing ophthalmic record"""
    record = get_object_or_404(OphthalmicRecord, id=record_id)
    
    if request.method == 'POST':
        form = OphthalmicRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ophthalmic record updated successfully.')
            return redirect('ophthalmic:ophthalmic_record_detail', record_id=record.id)
    else:
        form = OphthalmicRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Ophthalmic Record'
    }
    return render(request, 'ophthalmic/ophthalmic_record_form.html', context)

@login_required
def delete_ophthalmic_record(request, record_id):
    """View to delete a ophthalmic record"""
    record = get_object_or_404(OphthalmicRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Ophthalmic record deleted successfully.')
        return redirect('ophthalmic:ophthalmic_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'ophthalmic/ophthalmic_record_confirm_delete.html', context)

@login_required
def search_ophthalmic_patients(request):
    """AJAX view for searching patients in Ophthalmic module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)


@login_required
def create_prescription_for_ophthalmic(request, record_id):
    """Create a prescription for an ophthalmic patient"""
    record = get_object_or_404(OphthalmicRecord, id=record_id)
    
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
                    return redirect('ophthalmic:ophthalmic_record_detail', record_id=record.id)
                    
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
    return render(request, 'ophthalmic/create_prescription.html', context)