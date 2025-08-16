from django import forms
from .models import OncologyRecord
from django.utils import timezone


class OncologyRecordForm(forms.ModelForm):
    class Meta:
        model = OncologyRecord
        fields = [
            'patient',            'doctor',            'visit_date',            'cancer_type',            'stage',            'tumor_size',            'metastasis',            'treatment_protocol',            'chemotherapy_cycle',            'radiation_dose',            'surgery_details',            'biopsy_results',            'oncology_marker',            'diagnosis',            'treatment_plan',            'follow_up_required',            'follow_up_date',            'notes',        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'treatment_protocol': forms.Textarea(attrs={'rows': 2}),            'surgery_details': forms.Textarea(attrs={'rows': 2}),            'biopsy_results': forms.Textarea(attrs={'rows': 2}),            'oncology_marker': forms.Textarea(attrs={'rows': 2}),            'diagnosis': forms.Textarea(attrs={'rows': 3}),            'treatment_plan': forms.Textarea(attrs={'rows': 3}),            'notes': forms.Textarea(attrs={'rows': 3}),        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default visit date to today if creating new record
        if not self.instance.pk:
            self.fields['visit_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
