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
    
    context = {
        'record': record,
        'prescriptions': prescriptions,
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
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Family Planning Record'
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