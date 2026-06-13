from django import forms
from patients.models import Patient
from doctors.models import Doctor
from .models import CardiologyRecord, CardiologyClinicalNote
from core.medical_forms import MedicalRecordSearchForm
from core.clinical_notes import CLERKING_FIELDS, CLERKING_LABELS, clerking_widgets


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
            'ecg_pr_interval',
            'ecg_qrs_duration',
            'ecg_qt_interval',
            'ecg_axis',
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
            'doctor': forms.Select(attrs={'class': 'form-select select2 doctor-select'}),
            'ecg_pr_interval': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ms (120-200)'}),
            'ecg_qrs_duration': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ms (< 120)'}),
            'ecg_qt_interval': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ms'}),
            'ecg_axis': forms.Select(attrs={'class': 'form-select'}),
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

        # Doctor dropdown: real Doctor records (FK target), searchable via select2
        doctor_field = self.fields['doctor']
        doctor_field.queryset = Doctor.objects.select_related('user').all()
        doctor_field.required = False
        doctor_field.empty_label = "Select a doctor..."
        doctor_field.label_from_instance = lambda obj: obj.get_full_name()

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
    """Form for the Nigerian clerking proforma clinical note."""

    class Meta:
        model = CardiologyClinicalNote
        fields = CLERKING_FIELDS
        widgets = clerking_widgets()
        labels = CLERKING_LABELS

