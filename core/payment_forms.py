from django import forms
from django.utils import timezone
from decimal import Decimal
from billing.models import Payment, Invoice
from patients.models import PatientWallet
from .billing_office_integration import BillingOfficeFormMixin


class BasePaymentForm(BillingOfficeFormMixin, forms.ModelForm):
    """Base payment form that can be extended by all modules"""
    
    class Meta:
        model = Payment
        fields = ['amount', 'payment_date', 'payment_method', 'reference_number', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction reference (optional)'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Additional notes (optional)'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.module_name = kwargs.pop('module_name', 'General')
        super().__init__(*args, **kwargs)
        
        # Set default payment date to today
        if not self.instance.pk:
            self.fields['payment_date'].initial = timezone.now().date()
        
        # Set maximum amount to remaining balance
        if self.invoice:
            remaining_balance = self.invoice.get_balance()
            self.fields['amount'].widget.attrs['max'] = str(remaining_balance)
            self.fields['amount'].initial = remaining_balance
            self.fields['amount'].help_text = f"Maximum amount: ₦{remaining_balance:,.2f}"
        
        # Set wallet balance info
        if self.patient_wallet:
            if hasattr(self.fields['payment_source'], 'help_text'):
                self.fields['payment_source'].help_text += f' | Wallet Balance: ₦{self.patient_wallet.balance:.2f}'
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError("Payment amount must be greater than zero.")
        
        if self.invoice:
            remaining_balance = self.invoice.get_balance()
            if amount > remaining_balance:
                raise forms.ValidationError(
                    f"Payment amount (₦{amount:,.2f}) cannot exceed remaining balance (₦{remaining_balance:,.2f})."
                )
        
        return amount
    
    def clean(self):
        cleaned_data = super().clean()
        payment_source = cleaned_data.get('payment_source')
        amount = cleaned_data.get('amount')

        # Enhanced wallet payment validation with flexible options
        if payment_source == 'patient_wallet' and self.patient_wallet and amount:
            current_balance = self.patient_wallet.balance
            new_balance = current_balance - amount

            if amount > current_balance:
                # Allow negative balance but provide detailed warning
                cleaned_data['wallet_warning'] = True
                cleaned_data['current_balance'] = current_balance
                cleaned_data['new_balance'] = new_balance
                cleaned_data['deficit_amount'] = amount - current_balance

                # Add informational message (not an error)
                self.add_warning(
                    f"Wallet payment will result in negative balance. "
                    f"Current: ₦{current_balance:,.2f}, After payment: ₦{new_balance:,.2f}"
                )

        return cleaned_data

    def add_warning(self, message):
        """Add a warning message (not an error)"""
        if not hasattr(self, '_warnings'):
            self._warnings = []
        self._warnings.append(message)

    def get_warnings(self):
        """Get warning messages"""
        return getattr(self, '_warnings', [])


class LaboratoryPaymentForm(BasePaymentForm):
    """Payment form for laboratory services"""
    
    def __init__(self, *args, **kwargs):
        kwargs['module_name'] = 'Laboratory'
        super().__init__(*args, **kwargs)


class RadiologyPaymentForm(BasePaymentForm):
    """Payment form for radiology services"""
    
    def __init__(self, *args, **kwargs):
        kwargs['module_name'] = 'Radiology'
        super().__init__(*args, **kwargs)


class PharmacyPaymentForm(BasePaymentForm):
    """Payment form for pharmacy services"""
    
    def __init__(self, *args, **kwargs):
        kwargs['module_name'] = 'Pharmacy'
        super().__init__(*args, **kwargs)


class ConsultationPaymentForm(BasePaymentForm):
    """Payment form for consultation services"""
    
    def __init__(self, *args, **kwargs):
        kwargs['module_name'] = 'Consultation'
        super().__init__(*args, **kwargs)


class TheatrePaymentForm(BasePaymentForm):
    """Payment form for theatre/surgery services"""
    
    def __init__(self, *args, **kwargs):
        kwargs['module_name'] = 'Theatre'
        super().__init__(*args, **kwargs)


class InpatientPaymentForm(BasePaymentForm):
    """Payment form for inpatient services"""
    
    def __init__(self, *args, **kwargs):
        kwargs['module_name'] = 'Inpatient'
        super().__init__(*args, **kwargs)


class GeneralPaymentForm(BasePaymentForm):
    """General payment form for miscellaneous services"""
    
    def __init__(self, *args, **kwargs):
        kwargs['module_name'] = 'General'
        super().__init__(*args, **kwargs)


class QuickPaymentForm(forms.Form):
    """Quick payment form for immediate processing"""
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('wallet', 'Wallet'),
        ('transfer', 'Bank Transfer'),
    ]
    
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    
    reference = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Reference number (optional)'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.max_amount = kwargs.pop('max_amount', None)
        super().__init__(*args, **kwargs)
        
        if self.max_amount:
            self.fields['amount'].widget.attrs['max'] = str(self.max_amount)
            self.fields['amount'].help_text = f"Maximum: ₦{self.max_amount:,.2f}"
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if self.max_amount and amount > self.max_amount:
            raise forms.ValidationError(
                f"Amount cannot exceed ₦{self.max_amount:,.2f}"
            )
        return amount


class BulkPaymentForm(forms.Form):
    """Form for processing multiple payments at once"""
    
    payment_method = forms.ChoiceField(
        choices=Payment.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    payment_date = forms.DateField(
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Bulk payment notes'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.invoices = kwargs.pop('invoices', [])
        super().__init__(*args, **kwargs)
        
        # Add dynamic fields for each invoice
        for i, invoice in enumerate(self.invoices):
            self.fields[f'amount_{invoice.id}'] = forms.DecimalField(
                max_digits=10,
                decimal_places=2,
                min_value=Decimal('0.00'),
                max_value=invoice.get_balance(),
                initial=invoice.get_balance(),
                required=False,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'step': '0.01'
                }),
                label=f"Payment for Invoice #{invoice.invoice_number}"
            )
    
    def get_invoice_payments(self):
        """Get list of invoice payments from form data"""
        payments = []
        for invoice in self.invoices:
            amount = self.cleaned_data.get(f'amount_{invoice.id}')
            if amount and amount > 0:
                payments.append({
                    'invoice': invoice,
                    'amount': amount
                })
        return payments


class PaymentSearchForm(forms.Form):
    """Form for searching and filtering payments"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by patient name, invoice number, or reference'
        })
    )

    payment_method = forms.ChoiceField(
        choices=[('', 'All Methods')] + list(Payment.PAYMENT_METHOD_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    amount_min = forms.DecimalField(
        required=False,
        min_value=Decimal('0.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Min amount'
        })
    )

    amount_max = forms.DecimalField(
        required=False,
        min_value=Decimal('0.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Max amount'
        })
    )


class FlexiblePaymentForm(forms.Form):
    """Enhanced flexible payment form allowing multiple payment methods and negative wallet balances"""

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card/POS'),
        ('bank_transfer', 'Bank Transfer'),
        ('wallet', 'Patient Wallet'),
        ('mixed', 'Mixed Payment'),
    ]

    PAYMENT_PRIORITY_CHOICES = [
        ('wallet_first', 'Use Wallet First, Then Cash/Card'),
        ('cash_first', 'Use Cash/Card First, Then Wallet'),
        ('wallet_only', 'Wallet Only (Allow Negative)'),
        ('cash_only', 'Cash/Card Only'),
    ]

    total_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'readonly': True
        })
    )

    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )

    payment_priority = forms.ChoiceField(
        choices=PAYMENT_PRIORITY_CHOICES,
        initial='wallet_first',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # Wallet payment amount
    wallet_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )

    # Cash/Card payment amount
    cash_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )

    # Reference numbers
    cash_reference = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Receipt/Transaction reference'
        })
    )

    # Allow negative wallet balance
    allow_negative_wallet = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    # Payment notes
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'form-control',
            'placeholder': 'Payment notes (optional)'
        })
    )

    def __init__(self, *args, **kwargs):
        self.invoice = kwargs.pop('invoice', None)
        self.patient_wallet = kwargs.pop('patient_wallet', None)
        super().__init__(*args, **kwargs)

        if self.invoice:
            self.fields['total_amount'].initial = self.invoice.get_balance()

        # Set wallet amount suggestions
        if self.patient_wallet:
            wallet_balance = self.patient_wallet.balance
            total_amount = self.invoice.get_balance() if self.invoice else 0

            if wallet_balance >= total_amount:
                self.fields['wallet_amount'].initial = total_amount
                self.fields['cash_amount'].initial = 0
            else:
                self.fields['wallet_amount'].initial = max(0, wallet_balance)
                self.fields['cash_amount'].initial = total_amount - max(0, wallet_balance)

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        total_amount = cleaned_data.get('total_amount')
        wallet_amount = cleaned_data.get('wallet_amount', 0) or 0
        cash_amount = cleaned_data.get('cash_amount', 0) or 0
        allow_negative = cleaned_data.get('allow_negative_wallet', True)

        # Validate payment amounts based on method
        if payment_method == 'wallet':
            if not wallet_amount:
                cleaned_data['wallet_amount'] = total_amount
                wallet_amount = total_amount

            # Check wallet balance if negative not allowed
            if not allow_negative and self.patient_wallet:
                if wallet_amount > self.patient_wallet.balance:
                    raise forms.ValidationError(
                        f"Insufficient wallet balance. Available: ₦{self.patient_wallet.balance:,.2f}"
                    )

        elif payment_method in ['cash', 'card', 'bank_transfer']:
            if not cash_amount:
                cleaned_data['cash_amount'] = total_amount
                cash_amount = total_amount

        elif payment_method == 'mixed':
            total_paid = wallet_amount + cash_amount
            if abs(total_paid - total_amount) > 0.01:  # Allow for rounding
                raise forms.ValidationError(
                    f"Total payment (₦{total_paid:,.2f}) must equal invoice amount (₦{total_amount:,.2f})"
                )

        # Add wallet warning if going negative
        if wallet_amount > 0 and self.patient_wallet:
            current_balance = self.patient_wallet.balance
            new_balance = current_balance - wallet_amount

            if new_balance < 0:
                cleaned_data['wallet_warning'] = True
                cleaned_data['new_wallet_balance'] = new_balance
                cleaned_data['deficit_amount'] = abs(new_balance)

        return cleaned_data

    def get_payment_breakdown(self):
        """Get breakdown of payment methods and amounts"""
        if not self.is_valid():
            return None

        breakdown = {
            'total_amount': self.cleaned_data['total_amount'],
            'wallet_amount': self.cleaned_data.get('wallet_amount', 0) or 0,
            'cash_amount': self.cleaned_data.get('cash_amount', 0) or 0,
            'payment_method': self.cleaned_data['payment_method'],
            'has_wallet_warning': self.cleaned_data.get('wallet_warning', False),
            'new_wallet_balance': self.cleaned_data.get('new_wallet_balance', 0),
        }

        return breakdown
