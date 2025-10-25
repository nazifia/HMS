from django import forms
from .models import LaborRecord
from core.medical_forms import MedicalRecordSearchForm

class LaborRecordForm(forms.ModelForm):
    class Meta:
        model = LaborRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'onset_time',
            'presentation',
            'fetal_heart_rate',
            'cervical_dilation',
            'effacement',
            'rupture_of_membranes',
            'rupture_time',
            'mode_of_delivery',
            'duration_first_stage',
            'placenta_delivery_time',
            'diagnosis', 
            'treatment_plan', 
            'follow_up_required', 
            'follow_up_date', 
            'authorization_code', 
            'notes'
        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'onset_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'rupture_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'placenta_delivery_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'diagnosis': forms.Textarea(attrs={'rows': 2}),
            'treatment_plan': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

class LaborRecordSearchForm(MedicalRecordSearchForm):
    """Search form for Labor records"""
    pass