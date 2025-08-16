import os

# Define the modules
modules = [
    'ophthalmic',
    'ent',
    'oncology',
    'scbu',
    'anc',
    'labor',
    'icu',
    'family_planning',
    'gynae_emergency'
]

# Define the base path
base_path = os.getcwd()

# Generate views.py for each module
for module in modules:
    # Create views.py
    with open(os.path.join(base_path, module, 'views.py'), 'w') as f:
        class_name = module.capitalize() if module != 'gynae_emergency' else 'GynaeEmergency'
        model_name = f"{class_name}Record" if module != 'gynae_emergency' else 'GynaeEmergencyRecord'
        url_prefix = module.replace('_', '-')
        
        f.write(f'''from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import {model_name}
from .forms import {model_name}Form
from patients.models import Patient
from doctors.models import Doctor


@login_required
def {module}_records_list(request):
    """View to list all {module} records with search and pagination"""
    records = {model_name}.objects.select_related('patient', 'doctor').all()
    
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
    
    context = {{
        'page_obj': page_obj,
        'search_query': search_query,
    }}
    return render(request, '{module}/{module}_records_list.html', context)


@login_required
def create_{module}_record(request):
    """View to create a new {module} record"""
    if request.method == 'POST':
        form = {model_name}Form(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, '{module.capitalize()} record created successfully.')
            return redirect('{module}:{module}_record_detail', record_id=record.id)
    else:
        form = {model_name}Form()
    
    context = {{
        'form': form,
        'title': 'Create {module.capitalize()} Record'
    }}
    return render(request, '{module}/{module}_record_form.html', context)


@login_required
def {module}_record_detail(request, record_id):
    """View to display details of a specific {module} record"""
    record = get_object_or_404(
        {model_name}.objects.select_related('patient', 'doctor'), 
        id=record_id
    )
    
    context = {{
        'record': record,
    }}
    return render(request, '{module}/{module}_record_detail.html', context)


@login_required
def edit_{module}_record(request, record_id):
    """View to edit an existing {module} record"""
    record = get_object_or_404({model_name}, id=record_id)
    
    if request.method == 'POST':
        form = {model_name}Form(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, '{module.capitalize()} record updated successfully.')
            return redirect('{module}:{module}_record_detail', record_id=record.id)
    else:
        form = {model_name}Form(instance=record)
    
    context = {{
        'form': form,
        'record': record,
        'title': 'Edit {module.capitalize()} Record'
    }}
    return render(request, '{module}/{module}_record_form.html', context)


@login_required
def delete_{module}_record(request, record_id):
    """View to delete a {module} record"""
    record = get_object_or_404({model_name}, id=record_id)
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, '{module.capitalize()} record deleted successfully.')
        return redirect('{module}:{module}_records_list')
    
    context = {{
        'record': record
    }}
    return render(request, '{module}/{module}_record_confirm_delete.html', context)
''')

    # Create forms.py
    with open(os.path.join(base_path, module, 'forms.py'), 'w') as f:
        f.write(f'''from django import forms
from .models import {model_name}
from django.utils import timezone


class {model_name}Form(forms.ModelForm):
    class Meta:
        model = {model_name}
        fields = [
            'patient', 'doctor', 'visit_date',
            'chief_complaint', 'history_of_present_illness',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ]
        widgets = {{
            'visit_date': forms.DateTimeInput(attrs={{'type': 'datetime-local'}}),
            'follow_up_date': forms.DateInput(attrs={{'type': 'date'}}),
            'chief_complaint': forms.Textarea(attrs={{'rows': 3}}),
            'history_of_present_illness': forms.Textarea(attrs={{'rows': 4}}),
            'diagnosis': forms.Textarea(attrs={{'rows': 3}}),
            'treatment_plan': forms.Textarea(attrs={{'rows': 4}}),
            'notes': forms.Textarea(attrs={{'rows': 3}}),
        }}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default visit date to today if creating new record
        if not self.instance.pk:
            self.fields['visit_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
''')

print("Views and forms created successfully for all modules!")