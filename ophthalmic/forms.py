from django import forms
from .models import OphthalmicRecord
from django.utils import timezone
from datetime import date


class OphthalmicRecordForm(forms.ModelForm):
    class Meta:
        model = OphthalmicRecord
        fields = [
            'patient', 'doctor', 'visit_date',
            'visual_acuity_right', 'visual_acuity_left',
            'refraction_right_sphere', 'refraction_right_cylinder', 'refraction_right_axis',
            'refraction_left_sphere', 'refraction_left_cylinder', 'refraction_left_axis',
            'iop_right', 'iop_left',
            'clinical_findings', 'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'authorization_code', 'notes'
        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'clinical_findings': forms.Textarea(attrs={'rows': 4}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'treatment_plan': forms.Textarea(attrs={'rows': 4}),
            'authorization_code': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default visit date to today if creating new record
        if not self.instance.pk:
            self.fields['visit_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
        
        # Make patient field read-only if editing existing record
        if self.instance.pk:
            self.fields['patient'].widget.attrs['readonly'] = True
