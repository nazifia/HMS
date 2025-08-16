from django import forms
from .models import EntRecord
from django.utils import timezone


class EntRecordForm(forms.ModelForm):
    class Meta:
        model = EntRecord
        fields = [
            'patient',            'doctor',            'visit_date',            'external_ear_right',            'external_ear_left',            'ear_canal_right',            'ear_canal_left',            'tympanic_membrane_right',            'tympanic_membrane_left',            'nose_examination',            'throat_examination',            'neck_examination',            'audio_test_right',            'audio_test_left',            'diagnosis',            'treatment_plan',            'follow_up_required',            'follow_up_date',            'notes',        ]
        widgets = {
            'visit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'external_ear_right': forms.Textarea(attrs={'rows': 2}),            'external_ear_left': forms.Textarea(attrs={'rows': 2}),            'ear_canal_right': forms.Textarea(attrs={'rows': 2}),            'ear_canal_left': forms.Textarea(attrs={'rows': 2}),            'tympanic_membrane_right': forms.Textarea(attrs={'rows': 2}),            'tympanic_membrane_left': forms.Textarea(attrs={'rows': 2}),            'nose_examination': forms.Textarea(attrs={'rows': 2}),            'throat_examination': forms.Textarea(attrs={'rows': 2}),            'neck_examination': forms.Textarea(attrs={'rows': 2}),            'audio_test_right': forms.Textarea(attrs={'rows': 2}),            'audio_test_left': forms.Textarea(attrs={'rows': 2}),            'diagnosis': forms.Textarea(attrs={'rows': 3}),            'treatment_plan': forms.Textarea(attrs={'rows': 3}),            'notes': forms.Textarea(attrs={'rows': 3}),        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default visit date to today if creating new record
        if not self.instance.pk:
            self.fields['visit_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
