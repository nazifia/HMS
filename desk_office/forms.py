
from django import forms
from .models import AuthorizationCode
from patients.models import Patient

class AuthorizationCodeForm(forms.ModelForm):
    patient = forms.ModelChoiceField(queryset=Patient.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    class Meta:
        model = AuthorizationCode
        fields = ['patient', 'service', 'department']
