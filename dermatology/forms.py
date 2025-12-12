from django import forms
from django.forms import ModelForm
from .models import DermatologyRecord, DermatologyService, DermatologyTest, DermatologyClinicalNote
from patients.models import Patient
from core.patient_search_utils import search_patients_by_query
from django.utils import timezone

class DermatologyRecordForm(ModelForm):
    """Form for creating and updating dermatology records"""
    
    class Meta:
        model = DermatologyRecord
        fields = ['patient', 'condition_type', 'service', 'diagnosis', 'treatment_procedure', 'treatment_status', 'notes', 'appointment_date', 'next_appointment_date', 'dermatologist']
        widgets = {
            'appointment_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'next_appointment_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'treatment_procedure': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default appointment date to current time if not provided
        if not self.instance.pk and not self.initial.get('appointment_date'):
            self.initial['appointment_date'] = timezone.now().strftime('%Y-%m-%dT%H:%M')

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
