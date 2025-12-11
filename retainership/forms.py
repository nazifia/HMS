from django import forms
from .models import RetainershipPatient
from patients.models import SharedWallet

class RetainershipPatientForm(forms.ModelForm):
    class Meta:
        model = RetainershipPatient
        fields = '__all__'
        exclude = ['patient']

class RetainershipWalletLinkForm(forms.Form):
    wallet = forms.ModelChoiceField(
        queryset=SharedWallet.objects.filter(wallet_type='retainership', is_active=True),
        required=True,
        label='Select Retainership Wallet'
    )
    is_primary = forms.BooleanField(
        required=False,
        initial=True,
        label='Make this patient the primary member'
    )
