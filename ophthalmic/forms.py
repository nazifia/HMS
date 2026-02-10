from django import forms
from patients.models import Patient
from .models import OphthalmicRecord, OphthalmicClinicalNote
from core.medical_forms import MedicalRecordSearchForm


class OphthalmicRecordForm(forms.ModelForm):
    """Form for creating and editing ophthalmic records with patient search"""

    # Add patient search field
    patient_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control patient-search',
            'placeholder': 'Search patient by name, ID, or phone...',
            'autocomplete': 'off'
        }),
        help_text='Search for a patient by name, ID, or phone number'
    )

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
            'patient': forms.Select(attrs={'class': 'form-select select2 patient-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'visit_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'visual_acuity_right': forms.TextInput(attrs={'class': 'form-control'}),
            'visual_acuity_left': forms.TextInput(attrs={'class': 'form-control'}),
            'intraocular_pressure_right': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'intraocular_pressure_left': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'pupil_reaction_right': forms.TextInput(attrs={'class': 'form-control'}),
            'pupil_reaction_left': forms.TextInput(attrs={'class': 'form-control'}),
            'eyelid_exam_right': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'eyelid_exam_left': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'conjunctiva_exam_right': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'conjunctiva_exam_left': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'cornea_exam_right': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'cornea_exam_left': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'anterior_chamber_right': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'anterior_chamber_left': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'lens_exam_right': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'lens_exam_left': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'fundus_exam_right': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'fundus_exam_left': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'diagnosis': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'treatment_plan': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'follow_up_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'follow_up_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'authorization_code': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order patients by name for better UX
        patient_field = self.fields['patient']
        patient_field.queryset = Patient.objects.all().order_by('first_name', 'last_name')
        patient_field.empty_label = "Select a patient..."

        # Custom label_from_instance to show patient ID for better identification
        patient_field.label_from_instance = self._format_patient_label

        # If editing an existing record, populate the search field
        if self.instance and self.instance.pk and self.instance.patient:
            patient = self.instance.patient
            self.fields['patient_search'].initial = f"{patient.first_name} {patient.last_name} ({patient.patient_id})"

    def _format_patient_label(self, obj):
        """Format patient label with type information"""
        if not obj:
            return str(obj)

        label = f"{obj.get_full_name()} ({obj.patient_id})"
        patient_type = obj.get_patient_type_display()

        # Add type-specific information
        if hasattr(obj, 'nhia_info') and obj.nhia_info and obj.nhia_info.is_active:
            label += f" [NHIA: {obj.nhia_info.nhia_reg_number}]"
        elif hasattr(obj, 'retainership_info') and obj.retainership_info and obj.retainership_info.is_active:
            label += f" [Retainership: {obj.retainership_info.retainership_reg_number}]"
        elif patient_type != 'regular':
            label += f" [{patient_type}]"

        return label


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
