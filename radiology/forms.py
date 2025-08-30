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
    
    # Authorization code field
    authorization_code = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select Authorization Code (Optional)"
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
        
        # Set authorization code queryset based on patient
        try:
            from nhia.models import AuthorizationCode
        except ImportError:
            AuthorizationCode = None

        if patient_instance and patient_instance.patient_type == 'nhia' and AuthorizationCode:
            self.fields['authorization_code'].queryset = AuthorizationCode.objects.filter(
                patient=patient_instance,
                status='active'
            ).order_by('-generated_at')
        else:
            # Use empty queryset if AuthorizationCode is not available or patient is not NHIA
            if AuthorizationCode:
                self.fields['authorization_code'].queryset = AuthorizationCode.objects.none()
            else:
                # If NHIA app is not available, disable the field
                self.fields['authorization_code'].widget.attrs['disabled'] = True
                self.fields['authorization_code'].required = False
            
        # If editing an existing record, populate the search field
        if self.instance and self.instance.pk and self.instance.patient:
            patient = self.instance.patient
            self.fields['patient_search'].initial = f"{patient.first_name} {patient.last_name} ({patient.patient_id})"

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
