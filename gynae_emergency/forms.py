from django import forms
from .models import Gynae_emergencyRecord
from core.medical_forms import MedicalRecordSearchForm

class Gynae_emergencyRecordForm(forms.ModelForm):
    class Meta:
        model = Gynae_emergencyRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'emergency_type',
            'pain_level',
            'bleeding_amount',
            'contractions',
            'contraction_frequency',
            'rupture_of_membranes',
            'fetal_movement',
            'vaginal_discharge',
            'emergency_intervention',
            'stabilization_status',
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
            'vaginal_discharge': forms.Textarea(attrs={'rows': 2}),
            'emergency_intervention': forms.Textarea(attrs={'rows': 2}),
            'diagnosis': forms.Textarea(attrs={'rows': 2}),
            'treatment_plan': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

class GynaeEmergencyRecordSearchForm(MedicalRecordSearchForm):
    """Search form for Gynae Emergency records"""
    pass