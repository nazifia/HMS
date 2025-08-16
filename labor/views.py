from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import LaborRecord
from .forms import LaborRecordForm
from patients.models import Patient
from doctors.models import Doctor


@login_required
def labor_records_list(request):
    """View to list all labor records with search and pagination"""
    records = LaborRecord.objects.select_related('patient', 'doctor').all()
    
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
    return render(request, 'labor/labor_records_list.html', context)


@login_required
def create_labor_record(request):
    """View to create a new labor record"""
    if request.method == 'POST':
        form = LaborRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Labor record created successfully.')
            return redirect('labor:labor_record_detail', record_id=record.id)
    else:
        form = LaborRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Labor Record'
    }
    return render(request, 'labor/labor_record_form.html', context)


@login_required
def labor_record_detail(request, record_id):
    """View to display details of a specific labor record"""
    record = get_object_or_404(
        LaborRecord.objects.select_related('patient', 'doctor'), 
        id=record_id
    )
    
    context = {
        'record': record,
    }
    return render(request, 'labor/labor_record_detail.html', context)


@login_required
def edit_labor_record(request, record_id):
    """View to edit an existing labor record"""
    record = get_object_or_404(LaborRecord, id=record_id)
    
    if request.method == 'POST':
        form = LaborRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Labor record updated successfully.')
            return redirect('labor:labor_record_detail', record_id=record.id)
    else:
        form = LaborRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Labor Record'
    }
    return render(request, 'labor/labor_record_form.html', context)


@login_required
def delete_labor_record(request, record_id):
    """View to delete a labor record"""
    record = get_object_or_404(LaborRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Labor record deleted successfully.')
        return redirect('labor:labor_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'labor/labor_record_confirm_delete.html', context)
