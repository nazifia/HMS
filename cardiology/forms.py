from django import forms
from .models import CardiologyRecord, CardiologyClinicalNote
from core.medical_forms import MedicalRecordSearchForm


class CardiologyRecordForm(forms.ModelForm):
    class Meta:
        model = CardiologyRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'chest_pain_type',
            'ecg_findings',
            'echocardiogram_results',
            'stress_test_results',
            'cardiac_enzymes',
            'lipid_profile',
            'blood_pressure_systolic',
            'blood_pressure_diastolic',
            'heart_rate',
            'rhythm',
            'ejection_fraction',
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
            'chest_pain_type': forms.TextInput(attrs={'placeholder': 'e.g., Angina, Myocardial Infarction'}),
            'ecg_findings': forms.Textarea(attrs={'rows': 3}),
            'echocardiogram_results': forms.Textarea(attrs={'rows': 3}),
            'stress_test_results': forms.Textarea(attrs={'rows': 3}),
            'cardiac_enzymes': forms.Textarea(attrs={'rows': 2}),
            'lipid_profile': forms.Textarea(attrs={'rows': 2}),
            'rhythm': forms.TextInput(attrs={'placeholder': 'e.g., Normal Sinus, Atrial Fibrillation'}),
            'diagnosis': forms.TextInput(attrs={'placeholder': 'e.g., Hypertension, Heart Failure, Arrhythmia, CAD'}),
            'treatment_plan': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class CardiologyRecordSearchForm(MedicalRecordSearchForm):
    """Search form for Cardiology records"""
    pass


class CardiologyClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing cardiology clinical notes (SOAP format)"""

    class Meta:
        model = CardiologyClinicalNote
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
