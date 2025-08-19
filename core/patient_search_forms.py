from django import forms
from patients.models import Patient


class PatientSearchForm(forms.Form):
    """Unified patient search form for all medical modules"""
    
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by patient name, ID, or phone...',
            'autocomplete': 'off'
        }),
        help_text='Search by patient name, ID, or phone number'
    )
    
    # Hidden field to store selected patient ID
    selected_patient = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    def clean_selected_patient(self):
        """Validate that the selected patient exists and is active"""
        patient_id = self.cleaned_data.get('selected_patient')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id, is_active=True)
                return patient
            except Patient.DoesNotExist:
                raise forms.ValidationError("Selected patient does not exist or is inactive.")
        return None


class EnhancedPatientSearchForm(PatientSearchForm):
    """Enhanced patient search form with additional filters"""
    
    patient_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Patient.PATIENT_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Filter by patient type'
    )
    
    gender = forms.ChoiceField(
        choices=[('', 'All Genders')] + list(Patient.GENDER_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Filter by gender'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text='Filter patients registered from this date'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text='Filter patients registered up to this date'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("Start date cannot be after end date.")
            
        return cleaned_data