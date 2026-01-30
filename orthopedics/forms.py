from django import forms
from .models import OrthopedicsRecord, OrthopedicsClinicalNote
from core.medical_forms import MedicalRecordSearchForm


class OrthopedicsRecordForm(forms.ModelForm):
    class Meta:
        model = OrthopedicsRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'injury_type',
            'affected_body_part',
            'fracture_type',
            'fracture_classification',
            'pain_score',
            'range_of_motion',
            'neurovascular_status',
            'imaging_results',
            'procedure_done',
            'implant_used',
            'rehabilitation_plan',
            'weight_bearing_status',
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
            'injury_type': forms.TextInput(attrs={'placeholder': 'e.g., Fracture, Dislocation, Sprain, Strain'}),
            'affected_body_part': forms.TextInput(attrs={'placeholder': 'e.g., Spine, Hip, Knee, Shoulder, Wrist, Ankle'}),
            'fracture_type': forms.TextInput(attrs={'placeholder': 'Type of fracture if applicable'}),
            'fracture_classification': forms.TextInput(attrs={'placeholder': 'e.g., Simple, Compound, Comminuted, Greenstick'}),
            'pain_score': forms.NumberInput(attrs={'min': '0', 'max': '10', 'placeholder': '0-10'}),
            'range_of_motion': forms.Textarea(attrs={'rows': 2}),
            'neurovascular_status': forms.Textarea(attrs={'rows': 2}),
            'imaging_results': forms.Textarea(attrs={'rows': 3}),
            'procedure_done': forms.Textarea(attrs={'rows': 2}),
            'implant_used': forms.TextInput(attrs={'placeholder': 'e.g., Plates, Screws, Rods, Prosthesis'}),
            'rehabilitation_plan': forms.Textarea(attrs={'rows': 3}),
            'weight_bearing_status': forms.TextInput(attrs={'placeholder': 'e.g., Non-weight bearing, Partial, Full'}),
            'diagnosis': forms.TextInput(attrs={'placeholder': 'Primary diagnosis'}),
            'treatment_plan': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class OrthopedicsRecordSearchForm(MedicalRecordSearchForm):
    """Search form for Orthopedics records"""
    pass


class OrthopedicsClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing orthopedics clinical notes (SOAP format)"""

    class Meta:
        model = OrthopedicsClinicalNote
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
