from django import forms
from .models import GeneralMedicineRecord, GeneralMedicineClinicalNote
from core.medical_forms import MedicalRecordSearchForm


class GeneralMedicineRecordForm(forms.ModelForm):
    class Meta:
        model = GeneralMedicineRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'chief_complaint',
            'history_of_present_illness',
            'past_medical_history',
            'family_history',
            'social_history',
            'temperature',
            'blood_pressure_systolic',
            'blood_pressure_diastolic',
            'pulse_rate',
            'respiratory_rate',
            'oxygen_saturation',
            'weight',
            'height',
            'bmi',
            'general_appearance',
            'cardiovascular_exam',
            'respiratory_exam',
            'gastrointestinal_exam',
            'neurological_exam',
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
            'chief_complaint': forms.Textarea(attrs={'rows': 2}),
            'history_of_present_illness': forms.Textarea(attrs={'rows': 2}),
            'past_medical_history': forms.Textarea(attrs={'rows': 2}),
            'family_history': forms.Textarea(attrs={'rows': 2}),
            'social_history': forms.Textarea(attrs={'rows': 2}),
            'general_appearance': forms.Textarea(attrs={'rows': 2}),
            'cardiovascular_exam': forms.Textarea(attrs={'rows': 2}),
            'respiratory_exam': forms.Textarea(attrs={'rows': 2}),
            'gastrointestinal_exam': forms.Textarea(attrs={'rows': 2}),
            'neurological_exam': forms.Textarea(attrs={'rows': 2}),
            'diagnosis': forms.Textarea(attrs={'rows': 2}),
            'treatment_plan': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class GeneralMedicineRecordSearchForm(MedicalRecordSearchForm):
    """Search form for General Medicine records"""
    pass


class GeneralMedicineClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing general medicine clinical notes (SOAP format)"""

    class Meta:
        model = GeneralMedicineClinicalNote
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
