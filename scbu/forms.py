from django import forms
from .models import ScbuRecord
from django.utils import timezone


class ScbuRecordForm(forms.ModelForm):
    class Meta:
        model = ScbuRecord
        fields = [
            'patient',            'doctor',            'visit_date',            'gestational_age',            'birth_weight',            'apgar_score_1min',            'apgar_score_5min',            'respiratory_support',            'ventilation_type',            'feeding_method',            'infection_status',            'antibiotic_name',            'discharge_weight',            'diagnosis',            'treatment_plan',            'follow_up_required',            'follow_up_date',            'notes',        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'ventilation_type': forms.Textarea(attrs={'rows': 2}),            'feeding_method': forms.Textarea(attrs={'rows': 2}),            'antibiotic_name': forms.Textarea(attrs={'rows': 2}),            'diagnosis': forms.Textarea(attrs={'rows': 3}),            'treatment_plan': forms.Textarea(attrs={'rows': 3}),            'notes': forms.Textarea(attrs={'rows': 3}),        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default visit date to today if creating new record
        if not self.instance.pk:
            self.fields['visit_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
