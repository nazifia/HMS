from django import forms
from django.forms import ModelForm
from .models import DermatologyRecord, DermatologyService, DermatologyTest, DermatologyClinicalNote
from patients.models import Patient
from core.patient_search_utils import search_patients_by_query
from django.utils import timezone

class DermatologyRecordForm(ModelForm):
    """Form for creating and updating dermatology records with patient search"""

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
        model = DermatologyRecord
        fields = ['patient', 'condition_type', 'service', 'diagnosis', 'treatment_procedure', 'treatment_status', 'notes', 'appointment_date', 'next_appointment_date', 'dermatologist']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select select2 patient-select'}),
            'condition_type': forms.Select(attrs={'class': 'form-select'}),
            'service': forms.Select(attrs={'class': 'form-select'}),
            'diagnosis': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'treatment_procedure': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'treatment_status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'appointment_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'next_appointment_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'dermatologist': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order patients by name for better UX
        patient_field = self.fields['patient']
        patient_field.queryset = Patient.objects.all().order_by('first_name', 'last_name')
        patient_field.empty_label = "Select a patient..."

        # Custom label_from_instance to show patient ID for better identification
        patient_field.label_from_instance = self._format_patient_label

        # Set default appointment date to current time if not provided
        if not self.instance.pk and not self.initial.get('appointment_date'):
            self.initial['appointment_date'] = timezone.now().strftime('%Y-%m-%dT%H:%M')

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

class DermatologyRecordSearchForm(forms.Form):
    """Form for searching dermatology records"""
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Search by patient name, ID, or diagnosis'}))
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    condition_type = forms.ChoiceField(required=False, choices=[('', 'All Conditions')] + list(DermatologyRecord.CONDITION_TYPE_CHOICES))
    treatment_status = forms.ChoiceField(required=False, choices=[('', 'All Statuses')] + list(DermatologyRecord.TREATMENT_STATUS_CHOICES))

class DermatologyServiceForm(ModelForm):
    """Form for creating and updating dermatology services"""
    
    class Meta:
        model = DermatologyService
        fields = ['name', 'description', 'price', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class DermatologyTestForm(ModelForm):
    """Form for adding dermatology tests"""
    
    class Meta:
        model = DermatologyTest
        fields = ['test_type', 'results', 'notes']
        widgets = {
            'results': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class DermatologyClinicalNoteForm(ModelForm):
    """Form for adding clinical notes (SOAP format)"""
    
    class Meta:
        model = DermatologyClinicalNote
        fields = ['subjective', 'objective', 'assessment', 'plan']
        widgets = {
            'subjective': forms.Textarea(attrs={'rows': 4}),
            'objective': forms.Textarea(attrs={'rows': 4}),
            'assessment': forms.Textarea(attrs={'rows': 4}),
            'plan': forms.Textarea(attrs={'rows': 4}),
        }

class PatientSearchForm(forms.Form):
    """Form for searching patients in dermatology module"""
    search_query = forms.CharField(label='Search Patients', widget=forms.TextInput(attrs={'placeholder': 'Search by name, ID, or phone...', 'class': 'form-control'}))

class DermatologyPatientSelectionForm(forms.Form):
    """Form for selecting a patient with autocomplete"""
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Patient'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize with empty queryset, will be populated via AJAX
        self.fields['patient'].queryset = Patient.objects.none()

class DermatologyReferralForm(forms.Form):
    """Form for creating referrals from dermatology"""
    referral_reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Reason for referral...'}))
    urgency = forms.ChoiceField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('emergency', 'Emergency')])
    referred_to_department = forms.CharField(max_length=100, help_text='Department to refer patient to')
