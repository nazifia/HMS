from django import forms
from .models import Gynae_emergencyRecord, GynaeEmergencyClinicalNote
from core.medical_forms import MedicalRecordSearchForm

class Gynae_emergencyRecordForm(forms.ModelForm):
    class Meta:
        model = Gynae_emergencyRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'emergency_type',
            'pain_level',
            'bleeding_amount',
            'contractions',
            'contraction_frequency',
            'rupture_of_membranes',
            'fetal_movement',
            'vaginal_discharge',
            'emergency_intervention',
            'stabilization_status',
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
            'vaginal_discharge': forms.Textarea(attrs={'rows': 2}),
            'emergency_intervention': forms.Textarea(attrs={'rows': 2}),
            'diagnosis': forms.Textarea(attrs={'rows': 2}),
            'treatment_plan': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

class GynaeEmergencyRecordSearchForm(MedicalRecordSearchForm):
    """Search form for Gynae Emergency records"""
    pass

class GynaeEmergencyClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing gynae_emergency clinical notes (SOAP format)"""

    class Meta:
        model = GynaeEmergencyClinicalNote
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
