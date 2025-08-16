from django import forms
from .models import AncRecord
from django.utils import timezone


class AncRecordForm(forms.ModelForm):
    class Meta:
        model = AncRecord
        fields = [
            'patient',            'doctor',            'visit_date',            'gravida',            'para',            'abortions',            'lmp',            'edd',            'fundal_height',            'fetal_heartbeat',            'fetal_position',            'blood_pressure',            'urine_protein',            'diagnosis',            'treatment_plan',            'follow_up_required',            'follow_up_date',            'notes',        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'fetal_position': forms.Textarea(attrs={'rows': 2}),            'blood_pressure': forms.Textarea(attrs={'rows': 2}),            'urine_protein': forms.Textarea(attrs={'rows': 2}),            'diagnosis': forms.Textarea(attrs={'rows': 3}),            'treatment_plan': forms.Textarea(attrs={'rows': 3}),            'notes': forms.Textarea(attrs={'rows': 3}),        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default visit date to today if creating new record
        if not self.instance.pk:
            self.fields['visit_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
