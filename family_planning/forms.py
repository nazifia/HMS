from django import forms
from .models import Family_planningRecord, FamilyPlanningClinicalNote
from core.medical_forms import MedicalRecordSearchForm

class Family_planningRecordForm(forms.ModelForm):
    class Meta:
        model = Family_planningRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'method_used',
            'start_date',
            'end_date',
            'side_effects',
            'compliance',
            'refill_date',
            'partner_involvement',
            'education_provided',
            'discontinuation_reason',
            'diagnosis', 
            'treatment_plan', 
            'follow_up_required', 
            'follow_up_date', 
            'authorization_code', 
            'notes'
        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'refill_date': forms.DateInput(attrs={'type': 'date'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'side_effects': forms.Textarea(attrs={'rows': 2}),
            'education_provided': forms.Textarea(attrs={'rows': 2}),
            'discontinuation_reason': forms.Textarea(attrs={'rows': 2}),
            'diagnosis': forms.Textarea(attrs={'rows': 2}),
            'treatment_plan': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

class FamilyPlanningRecordSearchForm(MedicalRecordSearchForm):
    """Search form for Family Planning records"""
    pass

class FamilyPlanningClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing family_planning clinical notes (SOAP format)"""

    class Meta:
        model = FamilyPlanningClinicalNote
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
