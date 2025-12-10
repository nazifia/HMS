from django import forms
from .models import ScbuRecord, ScbuClinicalNote
from core.medical_forms import MedicalRecordSearchForm

class ScbuRecordForm(forms.ModelForm):
    class Meta:
        model = ScbuRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'gestational_age',
            'birth_weight',
            'apgar_score_1min',
            'apgar_score_5min',
            'respiratory_support',
            'ventilation_type',
            'feeding_method',
            'infection_status',
            'antibiotic_name',
            'discharge_weight',
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
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

class ScbuRecordSearchForm(MedicalRecordSearchForm):
    """Search form for SCBU records"""
    pass

class ScbuClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing scbu clinical notes (SOAP format)"""

    class Meta:
        model = ScbuClinicalNote
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
