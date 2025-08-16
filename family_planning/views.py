from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Family_planningRecord
from .forms import Family_planningRecordForm
from patients.models import Patient
from doctors.models import Doctor


@login_required
def family_planning_records_list(request):
    """View to list all family_planning records with search and pagination"""
    records = Family_planningRecord.objects.select_related('patient', 'doctor').all()
    
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
    return render(request, 'family_planning/family_planning_records_list.html', context)


@login_required
def create_family_planning_record(request):
    """View to create a new family_planning record"""
    if request.method == 'POST':
        form = Family_planningRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, 'Family_planning record created successfully.')
            return redirect('family_planning:family_planning_record_detail', record_id=record.id)
    else:
        form = Family_planningRecordForm()
    
    context = {
        'form': form,
        'title': 'Create Family_planning Record'
    }
    return render(request, 'family_planning/family_planning_record_form.html', context)


@login_required
def family_planning_record_detail(request, record_id):
    """View to display details of a specific family_planning record"""
    record = get_object_or_404(
        Family_planningRecord.objects.select_related('patient', 'doctor'), 
        id=record_id
    )
    
    context = {
        'record': record,
    }
    return render(request, 'family_planning/family_planning_record_detail.html', context)


@login_required
def edit_family_planning_record(request, record_id):
    """View to edit an existing family_planning record"""
    record = get_object_or_404(Family_planningRecord, id=record_id)
    
    if request.method == 'POST':
        form = Family_planningRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Family_planning record updated successfully.')
            return redirect('family_planning:family_planning_record_detail', record_id=record.id)
    else:
        form = Family_planningRecordForm(instance=record)
    
    context = {
        'form': form,
        'record': record,
        'title': 'Edit Family_planning Record'
    }
    return render(request, 'family_planning/family_planning_record_form.html', context)


@login_required
def delete_family_planning_record(request, record_id):
    """View to delete a family_planning record"""
    record = get_object_or_404(Family_planningRecord, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Family_planning record deleted successfully.')
        return redirect('family_planning:family_planning_records_list')
    
    context = {
        'record': record
    }
    return render(request, 'family_planning/family_planning_record_confirm_delete.html', context)
