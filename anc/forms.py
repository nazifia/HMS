from django import forms
from .models import AncRecord
from core.medical_forms import MedicalRecordSearchForm
from patients.models import Patient
from doctors.models import Doctor

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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get all active patients
        self.fields['patient'].queryset = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # Get all doctors
        self.fields['doctor'].queryset = Doctor.objects.select_related('user').all().order_by('user__first_name', 'user__last_name')

class AncRecordSearchForm(MedicalRecordSearchForm):
    """Search form for ANC records"""
    pass