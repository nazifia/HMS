from django import forms
from .models import RetainershipPatient
from patients.models import SharedWallet, Patient, WalletMembership


class RetainershipPatientForm(forms.ModelForm):
    class Meta:
        model = RetainershipPatient
        fields = "__all__"
        exclude = ["patient"]


class RetainershipWalletLinkForm(forms.Form):
    wallet = forms.ModelChoiceField(
        queryset=SharedWallet.objects.filter(
            wallet_type="retainership", is_active=True
        ),
        required=True,
        label="Select Retainership Wallet",
    )
    is_primary = forms.BooleanField(
        required=False, initial=True, label="Make this patient the primary member"
    )


class AddMemberToWalletForm(forms.Form):
    """Form for adding a patient to a retainership wallet"""

    patient = forms.ModelChoiceField(
        queryset=Patient.objects.filter(is_active=True),
        required=True,
        label="Select Patient",
        help_text="Search and select a patient to add to this wallet",
    )
    is_primary = forms.BooleanField(
        required=False,
        initial=False,
        label="Make Primary Member",
        help_text="Check to make this patient the primary member of the wallet",
    )

    def __init__(self, *args, **kwargs):
        self.wallet = kwargs.pop("wallet", None)
        super().__init__(*args, **kwargs)

        if self.wallet:
            # Exclude patients already in this wallet
            current_members = self.wallet.members.values_list("patient_id", flat=True)
            self.fields["patient"].queryset = (
                Patient.objects.filter(is_active=True)
                .exclude(id__in=current_members)
                .order_by("first_name", "last_name")
            )

            # Add custom class for patient search
            self.fields["patient"].widget.attrs.update(
                {"class": "form-select", "data-placeholder": "Search for a patient..."}
            )
