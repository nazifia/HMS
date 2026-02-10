from django import forms
from patients.models import Patient
from .models import PediatricsRecord, PediatricsClinicalNote
from core.medical_forms import MedicalRecordSearchForm


class PediatricsRecordForm(forms.ModelForm):
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
            'patient': forms.Select(attrs={'class': 'form-select select2 patient-select'}),
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
