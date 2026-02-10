from django import forms
from patients.models import Patient
from .models import OncologyRecord, OncologyClinicalNote
from core.medical_forms import MedicalRecordSearchForm

class OncologyRecordForm(forms.ModelForm):
    """Form for creating and editing oncology records with patient search"""

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
        model = OncologyRecord
        fields = [
            'patient',
            'doctor',
            'visit_date',
            'cancer_type',
            'stage',
            'tumor_size',
            'metastasis',
            'treatment_protocol',
            'chemotherapy_cycle',
            'radiation_dose',
            'surgery_details',
            'biopsy_results',
            'oncology_marker',
            'diagnosis',
            'treatment_plan',
            'follow_up_required',
            'follow_up_date',
            'authorization_code',
            'notes'
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select select2 patient-select'}),
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'diagnosis': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'treatment_plan': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'treatment_protocol': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'surgery_details': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'biopsy_results': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'oncology_marker': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
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

class OncologyRecordSearchForm(MedicalRecordSearchForm):
    """Search form for Oncology records"""
    pass

class OncologyClinicalNoteForm(forms.ModelForm):
    """Form for creating and editing oncology clinical notes (SOAP format)"""

    class Meta:
        model = OncologyClinicalNote
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
