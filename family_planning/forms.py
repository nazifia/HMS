from django import forms
from .models import Family_planningRecord
from django.utils import timezone


class Family_planningRecordForm(forms.ModelForm):
    class Meta:
        model = Family_planningRecord
        fields = [
            'patient',            'doctor',            'visit_date',            'method_used',            'start_date',            'end_date',            'side_effects',            'compliance',            'refill_date',            'partner_involvement',            'education_provided',            'follow_up_date',            'discontinuation_reason',            'diagnosis',            'treatment_plan',            'follow_up_required',            'follow_up_date',            'notes',        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'method_used': forms.Textarea(attrs={'rows': 2}),            'side_effects': forms.Textarea(attrs={'rows': 2}),            'education_provided': forms.Textarea(attrs={'rows': 2}),            'discontinuation_reason': forms.Textarea(attrs={'rows': 2}),            'diagnosis': forms.Textarea(attrs={'rows': 3}),            'treatment_plan': forms.Textarea(attrs={'rows': 3}),            'notes': forms.Textarea(attrs={'rows': 3}),        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default visit date to today if creating new record
        if not self.instance.pk:
            self.fields['visit_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
