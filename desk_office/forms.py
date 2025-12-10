from django import forms
from django.utils import timezone
from datetime import timedelta
import string
import random
from nhia.models import AuthorizationCode
from patients.models import Patient

class PatientSearchForm(forms.Form):
    """Form for searching NHIA patients"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by patient name, patient ID, or NHIA number...',
            'id': 'nhia-patient-search-input',
            'autocomplete': 'off',
            'data-bs-toggle': 'tooltip',
            'title': 'Search by name, patient ID, NHIA number, or phone'
        })
    )

class AuthorizationCodeForm(forms.ModelForm):
    # We'll override the patient field to make it readonly after selection
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.all().order_by('last_name', 'first_name'),
        widget=forms.Select(attrs={'class': 'form-control', 'readonly': True}),
        required=True
    )
        
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
    
    service_type = forms.ChoiceField(
        choices=[
            ('laboratory', 'Laboratory'),
            ('radiology', 'Radiology'),
            ('theatre', 'Theatre'),
            ('inpatient', 'Inpatient'),
            ('dental', 'Dental'),
            ('opthalmic', 'Ophthalmic'),  # Fixed typo
            ('ent', 'ENT'),
            ('oncology', 'Oncology'),
            ('general', 'General'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        required=True
    )

    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=True,
        help_text='Expiry date for this authorization code'
    )

    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Additional notes or remarks (optional)'
        }),
        required=False
    )

    class Meta:
        model = AuthorizationCode
        fields = ['patient', 'service_type', 'amount', 'expiry_date', 'notes']

    def __init__(self, *args, **kwargs):
        patient = kwargs.pop('patient', None)
        self.user = kwargs.pop('user', None)  # Get the current user for generated_by field
        super().__init__(*args, **kwargs)
        # Custom label_from_instance to show patient ID and type for better identification
        self.fields['patient'].label_from_instance = self._format_patient_label
        if patient:
            self.fields['patient'].queryset = Patient.objects.filter(id=patient.id)
            self.fields['patient'].initial = patient

    def save(self, commit=True):
        """Custom save method to generate authorization code and set metadata"""
        instance = super().save(commit=False)

        # Generate unique authorization code if not already set
        if not instance.code:
            while True:
                date_str = timezone.now().strftime('%Y%m%d')
                random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                code_str = f"AUTH-{date_str}-{random_str}"
                if not AuthorizationCode.objects.filter(code=code_str).exists():
                    instance.code = code_str
                    break

        # Set generated_by user if provided
        if self.user and not instance.generated_by:
            instance.generated_by = self.user

        # Ensure status is active
        if not instance.status:
            instance.status = 'active'

        if commit:
            instance.save()

        return instance