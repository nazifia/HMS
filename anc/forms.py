from django import forms
from .models import AncRecord
from core.medical_forms import MedicalRecordSearchForm

class AncRecordForm(forms.ModelForm):
    class Meta:
        model = AncRecord
        fields = [
            'patient', 
            'doctor', 
            'visit_date', 
            'gravida',
            'para',
            'abortions',
            'lmp',
            'edd',
            'fundal_height',
            'fetal_heartbeat',
            'fetal_position',
            'blood_pressure',
            'urine_protein',
            'diagnosis', 
            'treatment_plan', 
            'follow_up_required', 
            'follow_up_date', 
            'authorization_code', 
            'notes'
        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'lmp': forms.DateInput(attrs={'type': 'date'}),
            'edd': forms.DateInput(attrs={'type': 'date'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'treatment_plan': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

class AncRecordSearchForm(MedicalRecordSearchForm):
    """Search form for ANC records"""
    pass