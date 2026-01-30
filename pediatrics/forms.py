from django import forms
from .models import PediatricsRecord, PediatricsClinicalNote
from core.medical_forms import MedicalRecordSearchForm


class PediatricsRecordForm(forms.ModelForm):
    class Meta:
        model = PediatricsRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'age_category',
            'birth_weight',
            'gestational_age',
            'current_weight',
            'current_height',
            'head_circumference',
            'weight_for_age_percentile',
            'height_for_age_percentile',
            'weight_for_height_percentile',
            'temperature',
            'respiratory_rate',
            'heart_rate',
            'blood_pressure',
            'developmental_milestones',
            'developmental_concerns',
            'immunization_status',
            'feeding_pattern',
            'nutritional_status',
            'chief_complaint',
            'history_of_present_illness',
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
            'developmental_milestones': forms.Textarea(attrs={'rows': 2}),
            'developmental_concerns': forms.Textarea(attrs={'rows': 2}),
            'immunization_status': forms.Textarea(attrs={'rows': 2}),
            'feeding_pattern': forms.Textarea(attrs={'rows': 2}),
            'chief_complaint': forms.Textarea(attrs={'rows': 2}),
            'history_of_present_illness': forms.Textarea(attrs={'rows': 2}),
            'diagnosis': forms.Textarea(attrs={'rows': 2}),
            'treatment_plan': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class PediatricsRecordSearchForm(MedicalRecordSearchForm):
    """Search form for Pediatrics records"""
    pass


class PediatricsClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing pediatrics clinical notes (SOAP format)"""

    class Meta:
        model = PediatricsClinicalNote
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
