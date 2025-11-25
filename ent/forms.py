from django import forms
from patients.models import Patient
from .models import EntRecord, EntClinicalNote
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
            'diagnosis': forms.Textarea(attrs={'rows': 2}),
            'treatment_plan': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
            'authorization_code': forms.Select(attrs={'class': 'form-select select2'}),
            'follow_up_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order patients by name for better UX - include all patients regardless of type
        self.fields['patient'].queryset = Patient.objects.all().order_by('last_name', 'first_name')
        self.fields['patient'].label_from_instance = self._format_patient_label
        
        # Set default visit date to today if creating new record
        if not self.instance.pk:
            self.fields['visit_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
            
        # If editing an existing record, populate the search field
        if self.instance and self.instance.pk and self.instance.patient:
            patient = self.instance.patient
            self.fields['patient_search'].initial = f"{patient.first_name} {patient.last_name} ({patient.patient_id})"
    
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


class EntRecordSearchForm(MedicalRecordSearchForm):
    """Search form for ENT records"""
    pass


class EntPatientSearchForm(PatientSearchForm):
    """Patient search form specifically for ENT module"""
    pass


class EntClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing ent clinical notes (SOAP format)"""

    class Meta:
        model = EntClinicalNote
        fields = ['subjective', 'objective', 'assessment', 'plan']
        widgets = {
            'subjective': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': "Patient's description of symptoms, concerns, and history..."
            }),
            'objective': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observable findings, examination results, measurements...'
            }),
            'assessment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Clinical assessment, diagnosis, and interpretation...'
            }),
            'plan': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Treatment plan, interventions, follow-up...'
            }),
        }
        labels = {
            'subjective': 'Subjective (S)',
            'objective': 'Objective (O)',
            'assessment': 'Assessment (A)',
            'plan': 'Plan (P)',
        }
