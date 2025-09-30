from django import forms
from patients.models import Patient
from .models import RadiologyCategory, RadiologyTest, RadiologyOrder, RadiologyResult
from core.patient_search_forms import PatientSearchForm

class RadiologyOrderForm(forms.ModelForm):
    """Form for creating and updating radiology orders with patient search"""
    
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
    
    # Authorization code input field
    authorization_code_input = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter authorization code (if required)'
        }),
        help_text="Required for NHIA patients from non-NHIA consultations"
    )
    
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        patient_id = None
        patient_instance = None
        if request:
            patient_id = request.GET.get('patient')
        if not patient_id:
            patient_id = self.initial.get('patient')
        if patient_id:
            self.fields['patient'].initial = patient_id
            try:
                patient_instance = Patient.objects.get(id=patient_id)
            except Patient.DoesNotExist:
                patient_instance = None
                
        # Order patients by name for better UX
        self.fields['patient'].queryset = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
        self.fields['test'].queryset = RadiologyTest.objects.filter(is_active=True)
        # Make referring_doctor not required in the form (set in view)
        self.fields['referring_doctor'].required = False

        # If editing an existing record, populate the search field
        if self.instance and self.instance.pk and self.instance.patient:
            patient = self.instance.patient
            self.fields['patient_search'].initial = f"{patient.first_name} {patient.last_name} ({patient.patient_id})"

    def clean_authorization_code_input(self):
        """Validate authorization code if provided"""
        code_str = self.cleaned_data.get('authorization_code_input', '').strip()
        if not code_str:
            return None

        from nhia.models import AuthorizationCode
        try:
            auth_code = AuthorizationCode.objects.get(code=code_str)
            if not auth_code.is_valid():
                raise forms.ValidationError(f"Authorization code is {auth_code.status}")
            return auth_code
        except AuthorizationCode.DoesNotExist:
            raise forms.ValidationError("Invalid authorization code")

    def save(self, commit=True):
        instance = super().save(commit=False)
        auth_code = self.cleaned_data.get('authorization_code_input')
        if auth_code:
            instance.authorization_code = auth_code
            instance.authorization_status = 'authorized'
        if commit:
            instance.save()
        return instance

    class Meta:
        model = RadiologyOrder
        fields = ['patient', 'test', 'referring_doctor', 'priority', 
                  'scheduled_date', 'clinical_information', 'notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select select2 patient-select'}),
            'test': forms.Select(attrs={'class': 'form-select select2'}),
            'referring_doctor': forms.Select(attrs={'class': 'form-select select2'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'clinical_information': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

class RadiologyResultForm(forms.ModelForm):
    """Form for adding radiology test results"""
    class Meta:
        model = RadiologyResult
        fields = ['findings', 'impression', 'image_file', 'is_abnormal', 
                  'study_date', 'study_time', 'result_status']
        widgets = {
            'findings': forms.Textarea(attrs={'rows': 4}),
            'impression': forms.Textarea(attrs={'rows': 4}),
            'image_file': forms.FileInput(attrs={'class': 'form-control'}),
            'is_abnormal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'study_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'study_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'result_status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial values for new fields if creating a new instance
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['study_date'].initial = timezone.now().date()
            self.fields['study_time'].initial = timezone.now().time()
            self.fields['result_status'].initial = 'submitted'


class RadiologyPatientSearchForm(PatientSearchForm):
    """Patient search form specifically for radiology module"""
    pass
