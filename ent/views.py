from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import EntRecord
from .forms import EntRecordForm
from patients.models import Patient
from doctors.models import Doctor


@login_required
def ent_records_list(request):
    """View to list all ent records with search and pagination"""
    records = EntRecord.objects.select_related('patient', 'doctor').all()
    
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
    return render(request, 'ent/ent_records_list.html', context)


@login_required
def create_ent_record(request):
    """View to create a new ent record"""
    if request.method == 'POST':
        form = EntRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Ent record created successfully.')
            return redirect('ent:ent_record_detail', record_id=record.id)
    else:
        form = EntRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Ent Record'
    }
    return render(request, 'ent/ent_record_form.html', context)


@login_required
def ent_record_detail(request, record_id):
    """View to display details of a specific ent record"""
    record = get_object_or_404(
        EntRecord.objects.select_related('patient', 'doctor'), 
        id=record_id
    )
    
    context = {
        'record': record,
    }
    return render(request, 'ent/ent_record_detail.html', context)


@login_required
def edit_ent_record(request, record_id):
    """View to edit an existing ent record"""
    record = get_object_or_404(EntRecord, id=record_id)
    
    if request.method == 'POST':
        form = EntRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ent record updated successfully.')
            return redirect('ent:ent_record_detail', record_id=record.id)
    else:
        form = EntRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Ent Record'
    }
    return render(request, 'ent/ent_record_form.html', context)


@login_required
def delete_ent_record(request, record_id):
    """View to delete a ent record"""
    record = get_object_or_404(EntRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Ent record deleted successfully.')
        return redirect('ent:ent_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'ent/ent_record_confirm_delete.html', context)
