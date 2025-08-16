from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import OncologyRecord
from .forms import OncologyRecordForm
from patients.models import Patient
from doctors.models import Doctor


@login_required
def oncology_records_list(request):
    """View to list all oncology records with search and pagination"""
    records = OncologyRecord.objects.select_related('patient', 'doctor').all()
    
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
    
    context = {
        'record': record,
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
