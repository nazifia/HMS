from django import forms
from patients.models import Patient
from .models import EntRecord
from django.utils import timezone
from core.medical_forms import MedicalRecordSearchForm
from core.patient_search_forms import PatientSearchForm


class EntRecordForm(forms.ModelForm):
    """Form for creating and editing ENT records with patient search"""
    
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
        model = EntRecord
        fields = [
            'patient', 'doctor', 'visit_date', 'chief_complaint', 
            'history_of_present_illness', 'external_ear_right', 
            'external_ear_left', 'ear_canal_right', 'ear_canal_left', 
            'tympanic_membrane_right', 'tympanic_membrane_left', 
            'nose_examination', 'throat_examination', 'neck_examination', 
            'audio_test_right', 'audio_test_left', 'diagnosis', 
            'treatment_plan', 'follow_up_required', 'follow_up_date', 
            'authorization_code', 'notes'
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select select2 patient-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select select2'}),
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'external_ear_right': forms.Textarea(attrs={'rows': 2}),
            'external_ear_left': forms.Textarea(attrs={'rows': 2}),
            'ear_canal_right': forms.Textarea(attrs={'rows': 2}),
            'ear_canal_left': forms.Textarea(attrs={'rows': 2}),
            'tympanic_membrane_right': forms.Textarea(attrs={'rows': 2}),
            'tympanic_membrane_left': forms.Textarea(attrs={'rows': 2}),
            'nose_examination': forms.Textarea(attrs={'rows': 2}),
            'throat_examination': forms.Textarea(attrs={'rows': 2}),
            'neck_examination': forms.Textarea(attrs={'rows': 2}),
            'audio_test_right': forms.Textarea(attrs={'rows': 2}),
            'audio_test_left': forms.Textarea(attrs={'rows': 2}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'treatment_plan': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'authorization_code': forms.Select(attrs={'class': 'form-select select2'}),
            'follow_up_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order patients by name for better UX
        self.fields['patient'].queryset = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # Set default visit date to today if creating new record
        if not self.instance.pk:
            self.fields['visit_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
            
        # If editing an existing record, populate the search field
        if self.instance and self.instance.pk and self.instance.patient:
            patient = self.instance.patient
            self.fields['patient_search'].initial = f"{patient.first_name} {patient.last_name} ({patient.patient_id})"


class EntRecordSearchForm(MedicalRecordSearchForm):
    """Search form for ENT records"""
    pass


class EntPatientSearchForm(PatientSearchForm):
    """Patient search form specifically for ENT module"""
    pass
