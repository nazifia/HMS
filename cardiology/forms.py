from django import forms
from patients.models import Patient
from .models import CardiologyRecord, CardiologyClinicalNote
from core.medical_forms import MedicalRecordSearchForm


class CardiologyRecordForm(forms.ModelForm):
    """Form for creating and editing cardiology records with patient search"""

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
            'patient': forms.Select(attrs={'class': 'form-select select2 patient-select'}),
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'chest_pain_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Angina, Myocardial Infarction'}),
            'ecg_findings': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'echocardiogram_results': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'stress_test_results': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'cardiac_enzymes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'lipid_profile': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'rhythm': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Normal Sinus, Atrial Fibrillation'}),
            'diagnosis': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Hypertension, Heart Failure, Arrhythmia, CAD'}),
            'treatment_plan': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
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
