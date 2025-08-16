from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal
from .models import OphthalmicRecord
from .forms import OphthalmicRecordForm
from patients.models import Patient
from doctors.models import Doctor
from billing.models import Invoice, Service, Payment
from nhia.models import AuthorizationCode


@login_required
def ophthalmic_records_list(request):
    """View to list all ophthalmic records with search and pagination"""
    records = OphthalmicRecord.objects.select_related('patient', 'doctor').all()
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        records = records.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(diagnosis__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(records, 10)  # Show 10 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'ophthalmic/ophthalmic_records_list.html', context)


@login_required
def create_ophthalmic_record(request):
    """View to create a new ophthalmic record"""
    if request.method == 'POST':
        form = OphthalmicRecordForm(request.POST)
        if form.is_valid():
            # Handle authorization code if provided
            authorization_code = None
            authorization_code_input = form.cleaned_data.get('authorization_code')
            
            if authorization_code_input:
                try:
                    # Try to get the authorization code
                    authorization_code = AuthorizationCode.objects.get(code=authorization_code_input)
                    
                    # Check if the authorization code is valid
                    if not authorization_code.is_valid():
                        messages.error(request, 'The provided authorization code is not valid or has expired.')
                        return render(request, 'ophthalmic/ophthalmic_record_form.html', {'form': form, 'title': 'Create Ophthalmic Record'})
                    
                    # Check if the authorization code is for the correct service
                    if authorization_code.service_type not in ['opthalmic', 'general']:
                        messages.error(request, 'The provided authorization code is not valid for ophthalmic services.')
                        return render(request, 'ophthalmic/ophthalmic_record_form.html', {'form': form, 'title': 'Create Ophthalmic Record'})
                        
                except AuthorizationCode.DoesNotExist:
                    messages.error(request, 'The provided authorization code does not exist.')
                    return render(request, 'ophthalmic/ophthalmic_record_form.html', {'form': form, 'title': 'Create Ophthalmic Record'})
            
            # Save the record
            record = form.save()
            
            # Mark authorization code as used if provided
            if authorization_code:
                authorization_code.mark_as_used(f"Ophthalmic Record #{record.id}")
                messages.success(request, f'Ophthalmic record created successfully. Authorization code {authorization_code.code} has been marked as used.')
            else:
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
    
    medications = record.medications.all()
    tests = record.tests.all()
    
    context = {
        'record': record,
        'medications': medications,
        'tests': tests,
    }
    return render(request, 'ophthalmic/ophthalmic_record_detail.html', context)


@login_required
def edit_ophthalmic_record(request, record_id):
    """View to edit an existing ophthalmic record"""
    record = get_object_or_404(OphthalmicRecord, id=record_id)
    
    if request.method == 'POST':
        form = OphthalmicRecordForm(request.POST, instance=record)
        if form.is_valid():
            # Handle authorization code if provided
            authorization_code = None
            authorization_code_input = form.cleaned_data.get('authorization_code')
            
            if authorization_code_input and authorization_code_input != record.authorization_code:
                try:
                    # Try to get the authorization code
                    authorization_code = AuthorizationCode.objects.get(code=authorization_code_input)
                    
                    # Check if the authorization code is valid
                    if not authorization_code.is_valid():
                        messages.error(request, 'The provided authorization code is not valid or has expired.')
                        return render(request, 'ophthalmic/ophthalmic_record_form.html', {'form': form, 'record': record, 'title': 'Edit Ophthalmic Record'})
                    
                    # Check if the authorization code is for the correct service
                    if authorization_code.service_type not in ['opthalmic', 'general']:
                        messages.error(request, 'The provided authorization code is not valid for ophthalmic services.')
                        return render(request, 'ophthalmic/ophthalmic_record_form.html', {'form': form, 'record': record, 'title': 'Edit Ophthalmic Record'})
                        
                except AuthorizationCode.DoesNotExist:
                    messages.error(request, 'The provided authorization code does not exist.')
                    return render(request, 'ophthalmic/ophthalmic_record_form.html', {'form': form, 'record': record, 'title': 'Edit Ophthalmic Record'})
            
            # Save the record
            form.save()
            
            # Mark authorization code as used if provided and different from existing
            if authorization_code and authorization_code_input != record.authorization_code:
                authorization_code.mark_as_used(f"Ophthalmic Record #{record.id} (updated)")
                messages.success(request, f'Ophthalmic record updated successfully. Authorization code {authorization_code.code} has been marked as used.')
            else:
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
    """View to delete an ophthalmic record"""
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
def add_medication(request, record_id):
    """View to add a medication to an ophthalmic record"""
    record = get_object_or_404(OphthalmicRecord, id=record_id)
    
    if request.method == 'POST':
        form = OphthalmicMedicationForm(request.POST)
        if form.is_valid():
            medication = form.save(commit=False)
            medication.record = record
            medication.save()
            messages.success(request, 'Medication added successfully.')
            return redirect('ophthalmic:ophthalmic_record_detail', record_id=record.id)
    else:
        form = OphthalmicMedicationForm()
    
    context = {
        'form': form,
        'record': record,
        'title': 'Add Medication'
    }
    return render(request, 'ophthalmic/ophthalmic_medication_form.html', context)


@login_required
def edit_medication(request, medication_id):
    """View to edit an existing medication"""
    medication = get_object_or_404(OphthalmicMedication, id=medication_id)
    
    if request.method == 'POST':
        form = OphthalmicMedicationForm(request.POST, instance=medication)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medication updated successfully.')
            return redirect('ophthalmic:ophthalmic_record_detail', record_id=medication.record.id)
    else:
        form = OphthalmicMedicationForm(instance=medication)
    
    context = {
        'form': form,
        'medication': medication,
        'title': 'Edit Medication'
    }
    return render(request, 'ophthalmic/ophthalmic_medication_form.html', context)


@login_required
def delete_medication(request, medication_id):
    """View to delete a medication"""
    medication = get_object_or_404(OphthalmicMedication, id=medication_id)
    record_id = medication.record.id
    
    if request.method == 'POST':
        medication.delete()
        messages.success(request, 'Medication deleted successfully.')
        return redirect('ophthalmic:ophthalmic_record_detail', record_id=record_id)
    
    context = {
        'medication': medication
    }
    return render(request, 'ophthalmic/ophthalmic_medication_confirm_delete.html', context)


@login_required
def add_test(request, record_id):
    """View to add a test to an ophthalmic record"""
    record = get_object_or_404(OphthalmicRecord, id=record_id)
    
    if request.method == 'POST':
        form = OphthalmicTestForm(request.POST)
        if form.is_valid():
            test = form.save(commit=False)
            test.record = record
            test.save()
            messages.success(request, 'Test added successfully.')
            return redirect('ophthalmic:ophthalmic_record_detail', record_id=record.id)
    else:
        form = OphthalmicTestForm()
    
    context = {
        'form': form,
        'record': record,
        'title': 'Add Test'
    }
    return render(request, 'ophthalmic/ophthalmic_test_form.html', context)


@login_required
def edit_test(request, test_id):
    """View to edit an existing test"""
    test = get_object_or_404(OphthalmicTest, id=test_id)
    
    if request.method == 'POST':
        form = OphthalmicTestForm(request.POST, instance=test)
        if form.is_valid():
            form.save()
            messages.success(request, 'Test updated successfully.')
            return redirect('ophthalmic:ophthalmic_record_detail', record_id=test.record.id)
    else:
        form = OphthalmicTestForm(instance=test)
    
    context = {
        'form': form,
        'test': test,
        'title': 'Edit Test'
    }
    return render(request, 'ophthalmic/ophthalmic_test_form.html', context)


@login_required
def delete_test(request, test_id):
    """View to delete a test"""
    test = get_object_or_404(OphthalmicTest, id=test_id)
    record_id = test.record.id
    
    if request.method == 'POST':
        test.delete()
        messages.success(request, 'Test deleted successfully.')
        return redirect('ophthalmic:ophthalmic_record_detail', record_id=record_id)
    
    context = {
        'test': test
    }
    return render(request, 'ophthalmic/ophthalmic_test_confirm_delete.html', context)
