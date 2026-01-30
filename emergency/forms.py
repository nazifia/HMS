from django import forms
from .models import EmergencyRecord, EmergencyClinicalNote
from core.medical_forms import MedicalRecordSearchForm


class EmergencyRecordForm(forms.ModelForm):
    class Meta:
        model = EmergencyRecord
        fields = [
            'patient',
            'doctor',
            'arrival_time',
            'triage_level',
            'triage_notes',
            'mode_of_arrival',
            'brought_by',
            'temperature',
            'pulse_rate',
            'respiratory_rate',
            'blood_pressure_systolic',
            'blood_pressure_diastolic',
            'oxygen_saturation',
            'gcs_score',
            'chief_complaint',
            'history_of_present_illness',
            'past_medical_history',
            'allergies',
            'medications',
            'general_appearance',
            'physical_examination',
            'primary_diagnosis',
            'secondary_diagnosis',
            'investigations_done',
            'treatment_given',
            'status',
            'discharge_time',
            'discharge_diagnosis',
            'discharge_medications',
            'follow_up_required',
            'follow_up_instructions',
            'authorization_code',
            'referred_to_department',
            'referral_reason',
            'notes'
        ]
        widgets = {
            'arrival_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'discharge_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'triage_notes': forms.Textarea(attrs={'rows': 2}),
            'chief_complaint': forms.Textarea(attrs={'rows': 2}),
            'history_of_present_illness': forms.Textarea(attrs={'rows': 2}),
            'past_medical_history': forms.Textarea(attrs={'rows': 2}),
            'allergies': forms.Textarea(attrs={'rows': 2}),
            'medications': forms.Textarea(attrs={'rows': 2}),
            'general_appearance': forms.Textarea(attrs={'rows': 2}),
            'physical_examination': forms.Textarea(attrs={'rows': 3}),
            'primary_diagnosis': forms.Textarea(attrs={'rows': 2}),
            'secondary_diagnosis': forms.Textarea(attrs={'rows': 2}),
            'investigations_done': forms.Textarea(attrs={'rows': 2}),
            'treatment_given': forms.Textarea(attrs={'rows': 3}),
            'discharge_diagnosis': forms.Textarea(attrs={'rows': 2}),
            'discharge_medications': forms.Textarea(attrs={'rows': 2}),
            'follow_up_instructions': forms.Textarea(attrs={'rows': 2}),
            'referral_reason': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class EmergencyRecordSearchForm(MedicalRecordSearchForm):
    """Search form for Emergency records"""
    triage_level = forms.ChoiceField(
        choices=[('', 'All Levels')] + list(EmergencyRecord.TRIAGE_LEVELS),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(EmergencyRecord.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class EmergencyClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing emergency clinical notes (SOAP format)"""

    class Meta:
        model = EmergencyClinicalNote
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
