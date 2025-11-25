from django import forms
from .models import IcuRecord, IcuClinicalNote
from core.medical_forms import MedicalRecordSearchForm

class IcuRecordForm(forms.ModelForm):
    class Meta:
        model = IcuRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'gcs_score',
            'respiratory_rate',
            'oxygen_saturation',
            'blood_pressure_systolic',
            'blood_pressure_diastolic',
            'heart_rate',
            'body_temperature',
            'mechanical_ventilation',
            'vasopressor_use',
            'dialysis_required',
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

class IcuRecordSearchForm(MedicalRecordSearchForm):
    """Search form for ICU records"""
    pass

class IcuClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing icu clinical notes (SOAP format)"""

    class Meta:
        model = IcuClinicalNote
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
