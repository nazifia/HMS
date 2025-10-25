from django import forms
from pharmacy.models import Medication

class PrescriptionItemForm(forms.Form):
    """Form for adding prescription items in medical modules"""
    
    medication = forms.ModelChoiceField(
        queryset=Medication.objects.filter(is_active=True).order_by('name'),
        widget=forms.Select(attrs={
            'class': 'form-select select2',
            'data-placeholder': 'Select medication...'
        }),
        empty_label="Select medication"
    )
    
    dosage = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 1 tablet'
        }),
        help_text='Dosage instructions (e.g., 1 tablet, 5ml)'
    )
    
    frequency = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., twice daily'
        }),
        help_text='How often to take (e.g., once daily, twice daily)'
    )
    
    duration = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 7 days'
        }),
        help_text='Duration of treatment (e.g., 7 days, 2 weeks)'
    )
    
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 14',
            'min': '1'
        }),
        help_text='Total quantity prescribed'
    )
    
    instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 1,
            'placeholder': 'Additional instructions (e.g., take after meals)'
        }),
        help_text='Any special instructions for the patient'
    )

class MedicalModulePrescriptionForm(forms.Form):
    """Form for creating prescriptions from medical modules"""
    
    diagnosis = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter diagnosis'
        }),
        help_text='Primary diagnosis for this prescription'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Additional notes for pharmacy'
        }),
        help_text='Any additional notes for the pharmacy'
    )
    
    prescription_type = forms.ChoiceField(
        choices=[
            ('outpatient', 'Out-Patient (Take-Home)'),
            ('inpatient', 'In-Patient (MAR/eMAR)')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='outpatient',
        help_text='Type of prescription'
    )

# Formset for multiple prescription items
PrescriptionItemFormSet = forms.formset_factory(
    PrescriptionItemForm,
    extra=1,
    max_num=20,
    validate_max=True
)