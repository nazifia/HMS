from django import forms
from .models import RetainershipPatient

class RetainershipPatientForm(forms.ModelForm):
    class Meta:
        model = RetainershipPatient
        fields = '__all__'
