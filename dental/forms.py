from django import forms
from .models import DentalRecord

class DentalRecordForm(forms.ModelForm):
    class Meta:
        model = DentalRecord
        fields = ['patient', 'notes']