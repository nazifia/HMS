from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from billing.models import Invoice, Payment
from patients.models import PatientWallet


class RadiologyPaymentForm(forms.ModelForm):
    """Form for processing radiology test payments with dual payment method support"""
    
    PAYMENT_SOURCE_CHOICES = [
        ('billing_office', 'Direct Billing'),
        ('patient_wallet', 'Patient Wallet'),
    ]
    
    payment_source = forms.ChoiceField(
        choices=PAYMENT_SOURCE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='billing_office',
        help_text="Choose payment method"
    )
    
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'payment_date', 'transaction_id', 'notes', 'payment_source']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'transaction_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional transaction reference'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional payment notes'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.invoice = kwargs.pop('invoice', None)
        self.patient_wallet = kwargs.pop('patient_wallet', None)
        super().__init__(*args, **kwargs)
        
        # Display wallet balance if available
        if self.patient_wallet:
            wallet_balance = self.patient_wallet.balance
            self.fields['payment_source'].help_text = f"Wallet Balance: ₦{wallet_balance:.2f}"
        
        # Set payment method choices based on payment source
        if self.patient_wallet:
            self.fields['payment_method'].choices = [
                ('cash', 'Cash'),
                ('card', 'Card'),
                ('bank_transfer', 'Bank Transfer'),
                ('wallet', 'Wallet'),
            ]
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        payment_source = cleaned_data.get('payment_source')
        
        if not amount:
            raise ValidationError("Payment amount is required.")
        
        if amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")
        
        # Validate against invoice balance
        if self.invoice:
            remaining_balance = self.invoice.get_balance()
            if amount > remaining_balance:
                raise ValidationError(
                    f"Payment amount (₦{amount:.2f}) cannot exceed the remaining balance (₦{remaining_balance:.2f})."
                )
        
        # Allow wallet payments even with insufficient balance (negative balance allowed)
        # Wallet balance validation removed to support negative balances
        
        return cleaned_data
    
    def save(self, commit=True):
        payment = super().save(commit=False)
        
        # Handle wallet payment
        payment_source = self.cleaned_data['payment_source']
        if payment_source == 'patient_wallet' and self.patient_wallet:
            # Deduct from wallet balance
            self.patient_wallet.balance -= payment.amount
            if commit:
                self.patient_wallet.save()
        
        if commit:
            payment.save()
        
        return payment