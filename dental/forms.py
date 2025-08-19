from django import forms
from patients.models import Patient
from .models import DentalRecord
from core.medical_forms import MedicalRecordSearchForm
from core.patient_search_forms import PatientSearchForm


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
        fields = ['patient', 'notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select select2 patient-select'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order patients by name for better UX
        self.fields['patient'].queryset = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # If editing an existing record, populate the search field
        if self.instance and self.instance.pk and self.instance.patient:
            patient = self.instance.patient
            self.fields['patient_search'].initial = f"{patient.first_name} {patient.last_name} ({patient.patient_id})"


class DentalRecordSearchForm(MedicalRecordSearchForm):
    """Search form for dental records"""
    pass


class DentalPatientSearchForm(PatientSearchForm):
    """Patient search form specifically for dental module"""
    pass