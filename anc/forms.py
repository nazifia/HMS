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
            'diagnosis': forms.Textarea(attrs={'rows': 2}),
            'treatment_plan': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get all patients (not filtering by is_active to include all patient types)
        self.fields['patient'].queryset = Patient.objects.all().order_by('last_name', 'first_name')
        self.fields['patient'].label_from_instance = self._format_patient_label
        
        # Get all doctors
        self.fields['doctor'].queryset = Doctor.objects.select_related('user').all().order_by('user__first_name', 'user__last_name')
    
    def _format_patient_label(self, obj):
        """Format patient label with type information"""
        if not obj:
            return str(obj)
        
        label = f"{obj.get_full_name()} ({obj.patient_id})"
        patient_type = obj.get_patient_type_display()
        
        # Add type-specific information
        if hasattr(obj, 'nhia_info') and obj.nhia_info and obj.nhia_info.is_active:
            label += f" [NHIA: {obj.nhia_info.nhia_reg_number}]"
        elif hasattr(obj, 'retainership_info') and obj.retainership_info and obj.retainership_info.is_active:
            label += f" [Retainership: {obj.retainership_info.retainership_reg_number}]"
        elif patient_type != 'regular':
            label += f" [{patient_type}]"
            
        return label

class AncRecordSearchForm(MedicalRecordSearchForm):
    """Search form for ANC records"""
    pass