from django import forms
from .models import IcuRecord
from core.medical_forms import MedicalRecordSearchForm

class IcuRecordForm(forms.ModelForm):
    class Meta:
        model = IcuRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'gcs_score',
            'respiratory_rate',
            'oxygen_saturation',
            'blood_pressure_systolic',
            'blood_pressure_diastolic',
            'heart_rate',
            'body_temperature',
            'mechanical_ventilation',
            'vasopressor_use',
            'dialysis_required',
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
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

class IcuRecordSearchForm(MedicalRecordSearchForm):
    """Search form for ICU records"""
    pass