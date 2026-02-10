from django import forms
from patients.models import Patient
from .models import EmergencyRecord, EmergencyClinicalNote
from core.medical_forms import MedicalRecordSearchForm


class EmergencyRecordForm(forms.ModelForm):
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
