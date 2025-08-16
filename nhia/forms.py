from django import forms
from .models import AuthorizationCode
from patients.models import Patient
from datetime import date
from django.utils import timezone


class AuthorizationCodeForm(forms.ModelForm):
    """Form for creating authorization codes"""
    
    # Custom field for patient search
    patient_search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name or patient ID...'
        }),
        help_text="Search for a patient by name or ID"
    )
    
    class Meta:
        model = AuthorizationCode
        fields = ['patient', 'service_type', 'amount', 'expiry_date', 'notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-control'}),
            'service_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter patients to only show NHIA patients
        self.fields['patient'].queryset = Patient.objects.filter(patient_type='nhia')
        
        # Set default expiry date to 30 days from now
        if not self.instance.pk:  # Only for new instances
            self.fields['expiry_date'].initial = timezone.now().date() + timezone.timedelta(days=30)
    
    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date and expiry_date < date.today():
            raise forms.ValidationError("Expiry date cannot be in the past.")
        return expiry_date
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount