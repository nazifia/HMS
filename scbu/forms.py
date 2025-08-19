from django import forms
from .models import ScbuRecord
from core.medical_forms import MedicalRecordSearchForm

class ScbuRecordForm(forms.ModelForm):
    class Meta:
        model = ScbuRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'gestational_age',
            'birth_weight',
            'apgar_score_1min',
            'apgar_score_5min',
            'respiratory_support',
            'ventilation_type',
            'feeding_method',
            'infection_status',
            'antibiotic_name',
            'discharge_weight',
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

class ScbuRecordSearchForm(MedicalRecordSearchForm):
    """Search form for SCBU records"""
    pass