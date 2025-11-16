from django import forms
from patients.models import Patient
from .models import DentalRecord, DentalService, DentalXRay
from core.medical_forms import MedicalRecordSearchForm
from core.patient_search_forms import PatientSearchForm
from django.conf import settings
from typing import Any, cast


class DentalRecordForm(forms.ModelForm):
    """Form for creating and editing dental records with patient search"""
    
    # Add patient search field
    patient_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control patient-search',
            'placeholder': 'Search patient by name, ID, or phone...',
            'autocomplete': 'off'
        }),
        help_text='Search for a patient by name, ID, or phone number'
    )
    
    class Meta:
        model = DentalRecord
        fields = ['patient', 'tooth', 'service', 'diagnosis', 'treatment_procedure', 
                  'treatment_status', 'notes', 'appointment_date', 'next_appointment_date', 'dentist']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select select2 patient-select'}),
            'tooth': forms.Select(attrs={'class': 'form-select'}),
            'service': forms.Select(attrs={'class': 'form-select'}),
            'diagnosis': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'treatment_procedure': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'treatment_status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'appointment_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'next_appointment_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'dentist': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Order patients by name for better UX
        # Type annotation to help Pyright understand field type
        patient_field: forms.ModelChoiceField = self.fields['patient']  # type: ignore
        patient_field.queryset = Patient.objects.all().order_by('first_name', 'last_name')
        patient_field.empty_label = "Select a patient..."
        
        # Custom label_from_instance to show patient ID for better identification
        patient_field.label_from_instance = self._format_patient_label
        
    def _format_patient_label(self, obj):
        """Format patient label with type information"""
        if not obj:
            return str(obj)
        
        label = f"{obj.get_full_name()} ({obj.patient_id})"
        patient_type = obj.get_patient_type_display()
        
        # Add type-specific information
        if hasattr(obj, 'nhia_info') and obj.nhia_info and obj.nhia_info.is_active:
            label += f" [NHIA: {obj.nhia_info.nhia_reg_number}]"
        elif hasattr(obj, 'retainership_info') and obj.retainership_info and obj.retainership_info.is_active:
            label += f" [Retainership: {obj.retainership_info.retainership_reg_number}]"
        elif patient_type != 'regular':
            label += f" [{patient_type}]"
            
        return label
        
        # Order services by name
        service_field: forms.ModelChoiceField = self.fields['service']  # type: ignore
        service_field.queryset = DentalService.objects.filter(is_active=True).order_by('name')
        service_field.empty_label = "Select a service..."
        
        # Filter dentists
        from django.contrib.auth import get_user_model
        User = get_user_model()
        dentist_field: forms.ModelChoiceField = self.fields['dentist']  # type: ignore
        dentist_field.queryset = User.objects.filter(
            profile__specialization__icontains='dentist'
        ).order_by('first_name', 'last_name')
        dentist_field.empty_label = "Select a dentist..."
        
        # If editing an existing record, populate the search field
        if self.instance and self.instance.pk and self.instance.patient:
            patient = self.instance.patient
            self.fields['patient_search'].initial = f"{patient.first_name} {patient.last_name} ({patient.patient_id})"


class DentalRecordSearchForm(MedicalRecordSearchForm):
    """Search form for dental records"""
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text='Filter records from this date'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text='Filter records up to this date'
    )
    
    service = forms.ModelChoiceField(
        queryset=cast(Any, DentalService).objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Filter by dental service'
    )
    
    treatment_status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(DentalRecord.TREATMENT_STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Filter by treatment status'
    )


class DentalPatientSearchForm(PatientSearchForm):
    """Patient search form specifically for dental module"""
    pass


class DentalServiceForm(forms.ModelForm):
    """Form for creating and editing dental services"""
    
    class Meta:
        model = DentalService
        fields = ['name', 'description', 'price', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DentalXRayForm(forms.ModelForm):
    """Form for adding dental X-rays"""
    
    class Meta:
        model = DentalXRay
        fields = ['xray_type', 'image', 'notes']
        widgets = {
            'xray_type': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }