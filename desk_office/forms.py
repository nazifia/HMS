from django import forms
from nhia.models import AuthorizationCode
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
        queryset=Patient.objects.all().order_by('last_name', 'first_name'),
        widget=forms.Select(attrs={'class': 'form-control', 'readonly': True}),
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Custom label_from_instance to show patient ID and type for better identification
        self.fields['patient'].label_from_instance = self._format_patient_label
        
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
            ('opthalmic', 'Opthalmic'),
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
        super().__init__(*args, **kwargs)
        if patient:
            self.fields['patient'].queryset = Patient.objects.filter(id=patient.id)
            self.fields['patient'].initial = patient