from django import forms
from .models import LaborRecord
from django.utils import timezone


class LaborRecordForm(forms.ModelForm):
    class Meta:
        model = LaborRecord
        fields = [
            'patient', 'doctor', 'visit_date',
            'onset_time', 'presentation',
            'fetal_heart_rate',
            'cervical_dilation', 'effacement',
            'rupture_of_membranes', 'rupture_time',
            'mode_of_delivery',
            'duration_first_stage', 'placenta_delivery_time',
            'diagnosis', 'treatment_plan',
            'follow_up_required', 'follow_up_date', 'notes'
        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'onset_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'rupture_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'placenta_delivery_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'presentation': forms.Textarea(attrs={'rows': 3}),
            'mode_of_delivery': forms.Textarea(attrs={'rows': 3}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'treatment_plan': forms.Textarea(attrs={'rows': 4}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default visit date to today if creating new record
        if not self.instance.pk:
            self.fields['visit_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')