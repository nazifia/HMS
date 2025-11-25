from django import forms
from .models import OphthalmicRecord, OphthalmicClinicalNote
from core.medical_forms import MedicalRecordSearchForm


class OphthalmicRecordForm(forms.ModelForm):
    class Meta:
        model = OphthalmicRecord
        fields = [
            'patient',
            'doctor',
            'visit_date',
            'visual_acuity_right',
            'visual_acuity_left',
            'intraocular_pressure_right',
            'intraocular_pressure_left',
            'pupil_reaction_right',
            'pupil_reaction_left',
            'eyelid_exam_right',
            'eyelid_exam_left',
            'conjunctiva_exam_right',
            'conjunctiva_exam_left',
            'cornea_exam_right',
            'cornea_exam_left',
            'anterior_chamber_right',
            'anterior_chamber_left',
            'lens_exam_right',
            'lens_exam_left',
            'fundus_exam_right',
            'fundus_exam_left',
            'diagnosis',
            'treatment_plan',
            'follow_up_required',
            'follow_up_date',
            'authorization_code',
            'notes',
        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class OphthalmicRecordSearchForm(MedicalRecordSearchForm):
    """Search form for Ophthalmic records"""
    pass

class OphthalmicClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing ophthalmic clinical notes (SOAP format)"""

    class Meta:
        model = OphthalmicClinicalNote
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
