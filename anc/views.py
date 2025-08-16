from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import AncRecord
from .forms import AncRecordForm
from patients.models import Patient
from doctors.models import Doctor


@login_required
def anc_records_list(request):
    """View to list all anc records with search and pagination"""
    records = AncRecord.objects.select_related('patient', 'doctor').all()
    
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
    return render(request, 'anc/anc_records_list.html', context)


@login_required
def create_anc_record(request):
    """View to create a new anc record"""
    if request.method == 'POST':
        form = AncRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Anc record created successfully.')
            return redirect('anc:anc_record_detail', record_id=record.id)
    else:
        form = AncRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Anc Record'
    }
    return render(request, 'anc/anc_record_form.html', context)


@login_required
def anc_record_detail(request, record_id):
    """View to display details of a specific anc record"""
    record = get_object_or_404(
        AncRecord.objects.select_related('patient', 'doctor'), 
        id=record_id
    )
    
    context = {
        'record': record,
    }
    return render(request, 'anc/anc_record_detail.html', context)


@login_required
def edit_anc_record(request, record_id):
    """View to edit an existing anc record"""
    record = get_object_or_404(AncRecord, id=record_id)
    
    if request.method == 'POST':
        form = AncRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Anc record updated successfully.')
            return redirect('anc:anc_record_detail', record_id=record.id)
    else:
        form = AncRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Anc Record'
    }
    return render(request, 'anc/anc_record_form.html', context)


@login_required
def delete_anc_record(request, record_id):
    """View to delete a anc record"""
    record = get_object_or_404(AncRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Anc record deleted successfully.')
        return redirect('anc:anc_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'anc/anc_record_confirm_delete.html', context)
