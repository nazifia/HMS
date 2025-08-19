from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from .models import DentalRecord
from .forms import DentalRecordForm, DentalRecordSearchForm
from patients.models import Patient
from core.patient_search_utils import search_patients_by_query, format_patient_search_results
from core.medical_prescription_forms import MedicalModulePrescriptionForm, PrescriptionItemFormSet
from pharmacy.models import Prescription, PrescriptionItem

@login_required
def dental_records(request):
    """View to list all dental records with search and pagination"""
    records = DentalRecord.objects.select_related('patient').all()
    
    # Add search functionality
    search_form = DentalRecordSearchForm(request.GET)
    search_query = request.GET.get('search', '')
    
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search', search_query)
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        
        if search_query:
            records = records.filter(
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query) |
                Q(patient__phone_number__icontains=search_query) |
                Q(notes__icontains=search_query)
            )
            
        if date_from:
            records = records.filter(created_at__date__gte=date_from)
            
        if date_to:
            records = records.filter(created_at__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(records, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'search_query': search_query,
        'total_records': records.count(),
    }
    return render(request, 'dental/dental_records.html', context)

@login_required
def create_dental_record(request):
    """View to create a new dental record"""
    if request.method == 'POST':
        form = DentalRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Dental record created successfully.')
            return redirect('dental:dental_record_detail', record_id=record.id)
    else:
        form = DentalRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Dental Record'
    }
    return render(request, 'dental/dental_record_form.html', context)

@login_required
def dental_record_detail(request, record_id):
    """View to display details of a specific dental record"""
    record = get_object_or_404(DentalRecord.objects.select_related('patient'), id=record_id)
    
    # Get prescriptions for this patient
    prescriptions = Prescription.objects.filter(patient=record.patient).order_by('-prescription_date')[:5]
    
    context = {
        'record': record,
        'prescriptions': prescriptions,
    }
    return render(request, 'dental/dental_record_detail.html', context)

@login_required
def edit_dental_record(request, record_id):
    """View to edit an existing dental record"""
    record = get_object_or_404(DentalRecord, id=record_id)
    
    if request.method == 'POST':
        form = DentalRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dental record updated successfully.')
            return redirect('dental:dental_record_detail', record_id=record.id)
    else:
        form = DentalRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Dental Record'
    }
    return render(request, 'dental/dental_record_form.html', context)

@login_required
def delete_dental_record(request, record_id):
    """View to delete a dental record"""
    record = get_object_or_404(DentalRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Dental record deleted successfully.')
        return redirect('dental:dental_records')
    
    context = {
        'record': record
    }
    return render(request, 'dental/dental_record_confirm_delete.html', context)

@login_required
def search_dental_patients(request):
    """AJAX view for searching patients in dental module"""
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    patients = search_patients_by_query(search_term)
    results = format_patient_search_results(patients)
    
    return JsonResponse(results, safe=False)

@login_required
def create_prescription_for_dental(request, record_id):
    """Create a prescription for a dental patient"""
    record = get_object_or_404(DentalRecord, id=record_id)
    
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
                    return redirect('dental:dental_record_detail', record_id=record.id)
                    
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
    return render(request, 'dental/create_prescription.html', context)