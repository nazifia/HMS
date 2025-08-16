from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Gynae_emergencyRecord
from .forms import Gynae_emergencyRecordForm
from patients.models import Patient
from doctors.models import Doctor


@login_required
def gynae_emergency_records_list(request):
    """View to list all gynae_emergency records with search and pagination"""
    records = Gynae_emergencyRecord.objects.select_related('patient', 'doctor').all()
    
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
    return render(request, 'gynae_emergency/gynae_emergency_records_list.html', context)


@login_required
def create_gynae_emergency_record(request):
    """View to create a new gynae_emergency record"""
    if request.method == 'POST':
        form = Gynae_emergencyRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Gynae_emergency record created successfully.')
            return redirect('gynae_emergency:gynae_emergency_record_detail', record_id=record.id)
    else:
        form = Gynae_emergencyRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Gynae_emergency Record'
    }
    return render(request, 'gynae_emergency/gynae_emergency_record_form.html', context)


@login_required
def gynae_emergency_record_detail(request, record_id):
    """View to display details of a specific gynae_emergency record"""
    record = get_object_or_404(
        Gynae_emergencyRecord.objects.select_related('patient', 'doctor'), 
        id=record_id
    )
    
    context = {
        'record': record,
    }
    return render(request, 'gynae_emergency/gynae_emergency_record_detail.html', context)


@login_required
def edit_gynae_emergency_record(request, record_id):
    """View to edit an existing gynae_emergency record"""
    record = get_object_or_404(Gynae_emergencyRecord, id=record_id)
    
    if request.method == 'POST':
        form = Gynae_emergencyRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gynae_emergency record updated successfully.')
            return redirect('gynae_emergency:gynae_emergency_record_detail', record_id=record.id)
    else:
        form = Gynae_emergencyRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Gynae_emergency Record'
    }
    return render(request, 'gynae_emergency/gynae_emergency_record_form.html', context)


@login_required
def delete_gynae_emergency_record(request, record_id):
    """View to delete a gynae_emergency record"""
    record = get_object_or_404(Gynae_emergencyRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Gynae_emergency record deleted successfully.')
        return redirect('gynae_emergency:gynae_emergency_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'gynae_emergency/gynae_emergency_record_confirm_delete.html', context)
