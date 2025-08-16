from django import forms
from .models import Gynae_emergencyRecord
from django.utils import timezone


class Gynae_emergencyRecordForm(forms.ModelForm):
    class Meta:
        model = Gynae_emergencyRecord
        fields = [
            'patient',            'doctor',            'visit_date',            'emergency_type',            'pain_level',            'bleeding_amount',            'contractions',            'contraction_frequency',            'rupture_of_membranes',            'fetal_movement',            'vaginal_discharge',            'emergency_intervention',            'stabilization_status',            'diagnosis',            'treatment_plan',            'follow_up_required',            'follow_up_date',            'notes',        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'emergency_type': forms.Textarea(attrs={'rows': 2}),            'bleeding_amount': forms.Textarea(attrs={'rows': 2}),            'contraction_frequency': forms.Textarea(attrs={'rows': 2}),            'fetal_movement': forms.Textarea(attrs={'rows': 2}),            'vaginal_discharge': forms.Textarea(attrs={'rows': 2}),            'emergency_intervention': forms.Textarea(attrs={'rows': 2}),            'stabilization_status': forms.Textarea(attrs={'rows': 2}),            'diagnosis': forms.Textarea(attrs={'rows': 3}),            'treatment_plan': forms.Textarea(attrs={'rows': 3}),            'notes': forms.Textarea(attrs={'rows': 3}),        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default visit date to today if creating new record
        if not self.instance.pk:
            self.fields['visit_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
