from django import forms
from .models import OncologyRecord
from core.medical_forms import MedicalRecordSearchForm

class OncologyRecordForm(forms.ModelForm):
    class Meta:
        model = OncologyRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'cancer_type',
            'stage',
            'tumor_size',
            'metastasis',
            'treatment_protocol',
            'chemotherapy_cycle',
            'radiation_dose',
            'surgery_details',
            'biopsy_results',
            'oncology_marker',
            'diagnosis', 
            'treatment_plan', 
            'follow_up_required', 
            'follow_up_date', 
            'authorization_code', 
            'notes'
        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'treatment_plan': forms.Textarea(attrs={'rows': 3}),
            'treatment_protocol': forms.Textarea(attrs={'rows': 3}),
            'surgery_details': forms.Textarea(attrs={'rows': 3}),
            'biopsy_results': forms.Textarea(attrs={'rows': 3}),
            'oncology_marker': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

class OncologyRecordSearchForm(MedicalRecordSearchForm):
    """Search form for Oncology records"""
    pass