from django import forms
from django.core.exceptions import ValidationError
from .models import InterDispensaryTransfer, Medication, Dispensary


class InterDispensaryTransferForm(forms.ModelForm):
    """Form for creating inter-dispensary transfers"""
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Filter dispensaries to active ones
        self.fields['from_dispensary'].queryset = Dispensary.objects.filter(is_active=True)
        self.fields['to_dispensary'].queryset = Dispensary.objects.filter(is_active=True)
        
        # Set default from_dispensary if user has associated dispensary
        if user and hasattr(user, 'profile') and hasattr(user.profile, 'dispensary'):
            self.fields['from_dispensary'].initial = user.profile.dispensary
    
    medication = forms.ModelChoiceField(
        queryset=Medication.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select medication-select'}),
        label='Medication'
    )
    
    from_dispensary = forms.ModelChoiceField(
        queryset=Dispensary.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='From Dispensary'
    )
    
    to_dispensary = forms.ModelChoiceField(
        queryset=Dispensary.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='To Dispensary'
    )
    
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        label='Quantity to Transfer'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Notes'
    )

    class Meta:
        model = InterDispensaryTransfer
        fields = ['medication', 'from_dispensary', 'to_dispensary', 'quantity', 'notes']
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Get form data
        from_dispensary = cleaned_data.get('from_dispensary')
        to_dispensary = cleaned_data.get('to_dispensary')
        medication = cleaned_data.get('medication')
        quantity = cleaned_data.get('quantity')
        
        # Validation
        if from_dispensary and to_dispensary:
            if from_dispensary == to_dispensary:
                raise ValidationError("Cannot transfer to the same dispensary")
        
        if from_dispensary and medication and quantity:
            # Check availability
            can_transfer, message = InterDispensaryTransfer.check_transfer_feasibility(
                medication, from_dispensary, quantity
            )
            if not can_transfer:
                raise ValidationError(message)
        
        return cleaned_data


class InterDispensaryTransferApprovalForm(forms.ModelForm):
    """Form for approving/rejecting inter-dispensary transfers"""
    
    class Meta:
        model = InterDispensaryTransfer
        fields = []
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class InterDispensaryTransferRejectForm(forms.Form):
    """Form for rejecting inter-dispensary transfers with reason"""
    
    rejection_reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Rejection Reason'
    )


class InterDispensaryTransferSearchForm(forms.Form):
    """Form for searching inter-dispensary transfers"""
    
    STATUS_CHOICES = [('', 'All Status')] + InterDispensaryTransfer.TRANSFER_STATUS_CHOICES
    
    from_dispensary = forms.ModelChoiceField(
        queryset=Dispensary.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='From Dispensary'
    )
    
    to_dispensary = forms.ModelChoiceField(
        queryset=Dispensary.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='To Dispensary'
    )
    
    medication = forms.ModelChoiceField(
        queryset=Medication.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Medication'
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Status'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='From Date'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='To Date'
    )
