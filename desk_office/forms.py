from django import forms
from .models import AuthorizationCode
from patients.models import Patient

class PatientSearchForm(forms.Form):
    """Form for searching NHIA patients"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by patient name or NHIA number...',
            'id': 'patient-search'
        })
    )

class AuthorizationCodeForm(forms.ModelForm):
    # We'll override the patient field to make it readonly after selection
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.filter(patient_type='nhia'),
        widget=forms.Select(attrs={'class': 'form-control', 'readonly': True}),
        required=True
    )
    
    service_type = forms.ChoiceField(
        choices=AuthorizationCode.SERVICE_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    service_description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Describe the specific service requested (e.g., CBC, X-Ray, Surgery, etc.)'
        }),
        required=False
    )
    
    department = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Department where service will be delivered'
        }),
        required=True
    )

    class Meta:
        model = AuthorizationCode
        fields = ['patient', 'service_type', 'service_description', 'department']

    def __init__(self, *args, **kwargs):
        patient = kwargs.pop('patient', None)
        super().__init__(*args, **kwargs)
        if patient:
            self.fields['patient'].queryset = Patient.objects.filter(id=patient.id)
            self.fields['patient'].initial = patient