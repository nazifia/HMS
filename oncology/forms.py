from django import forms
from .models import OncologyRecord, OncologyClinicalNote
from core.medical_forms import MedicalRecordSearchForm

class OncologyRecordForm(forms.ModelForm):
    class Meta:
        model = OncologyRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'cancer_type',
            'stage',
            'tumor_size',
            'metastasis',
            'treatment_protocol',
            'chemotherapy_cycle',
            'radiation_dose',
            'surgery_details',
            'biopsy_results',
            'oncology_marker',
            'diagnosis', 
            'treatment_plan', 
            'follow_up_required', 
            'follow_up_date', 
            'authorization_code', 
            'notes'
        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'diagnosis': forms.Textarea(attrs={'rows': 2}),
            'treatment_plan': forms.Textarea(attrs={'rows': 2}),
            'treatment_protocol': forms.Textarea(attrs={'rows': 2}),
            'surgery_details': forms.Textarea(attrs={'rows': 2}),
            'biopsy_results': forms.Textarea(attrs={'rows': 2}),
            'oncology_marker': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

class OncologyRecordSearchForm(MedicalRecordSearchForm):
    """Search form for Oncology records"""
    pass

class OncologyClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing oncology clinical notes (SOAP format)"""

    class Meta:
        model = OncologyClinicalNote
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
