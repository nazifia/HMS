from django import forms
from django.core.exceptions import ValidationError
from .models import InterDispensaryTransfer, Medication, Dispensary
from django.forms import formset_factory


class EnhancedMedicationTransferForm(forms.Form):
    """Enhanced form for single medication transfer with inventory validation"""
    
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
        widget=forms.Select(attrs={'class': 'form-select medication-select', 'data-url': '/pharmacy/api/inventory-check/'}),
        label='Medication'
    )
    
    from_dispensary = forms.ModelChoiceField(
        queryset=Dispensary.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select source-dispensary'}),
        label='From Dispensary'
    )
    
    to_dispensary = forms.ModelChoiceField(
        queryset=Dispensary.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select destination-dispensary'}),
        label='To Dispensary'
    )
    
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control quantity-input',
            'placeholder': 'Enter quantity',
            'min': 1
        }),
        label='Quantity to Transfer'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add any notes or special instructions'
        }),
        label='Notes'
    )

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


class BulkMedicationTransferForm(forms.Form):
    """Form for bulk transferring multiple medications"""
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Filter dispensaries to active ones
        self.fields['from_dispensary'].queryset = Dispensary.objects.filter(is_active=True)
        self.fields['to_dispensary'].queryset = Dispensary.objects.filter(is_active=True)
        
        # Set default from_dispensary if user has associated dispensary
        if user and hasattr(user, 'profile') and hasattr(user.profile, 'dispensary'):
            self.fields['from_dispensary'].initial = user.profile.dispensary
    
    from_dispensary = forms.ModelChoiceField(
        queryset=Dispensary.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select source-dispensary'}),
        label='Source Dispensary',
        required=True
    )
    
    to_dispensary = forms.ModelChoiceField(
        queryset=Dispensary.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select destination-dispensary'}),
        label='Destination Dispensary',
        required=True
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add any notes or special instructions for bulk transfer'
        }),
        label='Bulk Transfer Notes'
    )


class MedicationTransferItemForm(forms.Form):
    """Form for individual medication items in bulk transfer"""
    
    medication = forms.ModelChoiceField(
        queryset=Medication.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select medication-select-item'}),
        label='Medication',
        required=True
    )
    
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control quantity-item',
            'min': 1,
            'placeholder': 'Quantity'
        }),
        label='Quantity',
        required=True
    )
    
    available_stock = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control available-stock',
            'readonly': True,
            'style': 'background-color: #f8f9fa;'
        }),
        label='Available Stock',
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        medication = cleaned_data.get('medication')
        quantity = cleaned_data.get('quantity')
        
        if medication and quantity:
            # This will be validated dynamically via JavaScript
            pass
        
        return cleaned_data


class TransferSearchForm(forms.Form):
    """Form for searching and filtering transfers"""
    
    TRANSFER_STATUS_CHOICES = [
        ('', 'All Status'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]
    
    search_term = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by medication name, transfer ID...'
        }),
        label='Search'
    )
    
    from_dispensary = forms.ModelChoiceField(
        queryset=Dispensary.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='From Dispensary',
        required=False
    )
    
    to_dispensary = forms.ModelChoiceField(
        queryset=Dispensary.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='To Dispensary',
        required=False
    )
    
    status = forms.ChoiceField(
        choices=TRANSFER_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Status',
        required=False
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Date From'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Date To'
    )


# Create formset for bulk transfer items
MedicationTransferItemFormSet = formset_factory(
    MedicationTransferItemForm,
    extra=3,  # Start with 3 empty forms
    can_delete=True
)


class TransferApprovalForm(forms.Form):
    """Form for approving transfers with optional notes"""
    
    approval_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add approval notes if needed'
        }),
        label='Approval Notes'
    )


class TransferRejectionForm(forms.Form):
    """Form for rejecting transfers with reason"""
    
    rejection_reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Please provide reason for rejection'
        }),
        label='Rejection Reason'
    )
