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
    
    context = {
        'record': record,
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
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit SCBU Record'
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