from django import forms
from .models import RadiologyCategory, RadiologyTest, RadiologyOrder, RadiologyResult
from patients.models import Patient

class RadiologyOrderForm(forms.ModelForm):
    """Form for creating and updating radiology orders"""
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        patient_id = None
        if request:
            patient_id = request.GET.get('patient')
        if not patient_id:
            patient_id = self.initial.get('patient')
        if patient_id:
            self.fields['patient'].initial = patient_id
            # Keep patient field visible but pre-selected for user convenience
        # Always set queryset for dropdowns
        self.fields['patient'].queryset = Patient.objects.all()
        self.fields['test'].queryset = RadiologyTest.objects.filter(is_active=True)
        # Make referring_doctor not required in the form (set in view)
        self.fields['referring_doctor'].required = False

    class Meta:
        model = RadiologyOrder
        fields = ['patient', 'test', 'referring_doctor', 'priority', 
                  'scheduled_date', 'clinical_information', 'notes']
        widgets = {
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
            'study_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'study_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial values for new fields if creating a new instance
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['study_date'].initial = timezone.now().date()
            self.fields['study_time'].initial = timezone.now().time()
            self.fields['result_status'].initial = 'submitted'
