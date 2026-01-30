from django import forms
from .models import SurgeryRecord, SurgeryClinicalNote
from core.medical_forms import MedicalRecordSearchForm


class SurgeryRecordForm(forms.ModelForm):
    class Meta:
        model = SurgeryRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'surgery_type',
            'surgery_date',
            'procedure_code',
            'preop_diagnosis',
            'preop_assessment',
            'anesthesia_type',
            'surgeon',
            'assistant_surgeon',
            'anesthesiologist',
            'operative_findings',
            'procedure_performed',
            'implants_used',
            'complications',
            'estimated_blood_loss',
            'postop_diagnosis',
            'postop_instructions',
            'discharge_summary',
            'postop_day',
            'wound_status',
            'pain_level',
            'mobility_status',
            'follow_up_required', 
            'follow_up_date', 
            'authorization_code', 
            'notes'
        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'surgery_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'preop_diagnosis': forms.Textarea(attrs={'rows': 2}),
            'preop_assessment': forms.Textarea(attrs={'rows': 2}),
            'operative_findings': forms.Textarea(attrs={'rows': 2}),
            'procedure_performed': forms.Textarea(attrs={'rows': 2}),
            'implants_used': forms.Textarea(attrs={'rows': 2}),
            'complications': forms.Textarea(attrs={'rows': 2}),
            'postop_diagnosis': forms.Textarea(attrs={'rows': 2}),
            'postop_instructions': forms.Textarea(attrs={'rows': 2}),
            'discharge_summary': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class SurgeryRecordSearchForm(MedicalRecordSearchForm):
    """Search form for Surgery records"""
    pass


class SurgeryClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing surgery clinical notes (SOAP format)"""

    class Meta:
        model = SurgeryClinicalNote
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
