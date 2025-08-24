from django import forms
from django.utils import timezone
from .models import Invoice, InvoiceItem, Payment, Service

class InvoiceForm(forms.ModelForm):
    """Form for creating and editing invoices"""
    class Meta:
        model = Invoice
        fields = ['patient', 'notes', 'due_date', 'status']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select select2'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'due_date': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default due date to 30 days from now
        if not self.instance.pk and not self.initial.get('due_date'):
            self.initial['due_date'] = timezone.now().date() + timezone.timedelta(days=30)

        # Set initial values for required fields that aren't in the form
        if not self.instance.pk:
            self.instance.subtotal = 0
            self.instance.tax_amount = 0
            self.instance.total_amount = 0

class InvoiceItemForm(forms.ModelForm):
    """Form for adding items to an invoice"""
    class Meta:
        model = InvoiceItem
        fields = ['service', 'description', 'quantity', 'unit_price']
        widgets = {
            'service': forms.Select(attrs={'class': 'form-select select2'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].required = False

        # Set initial values for required fields that aren't in the form
        if not self.instance.pk:
            self.instance.tax_percentage = 0
            self.instance.tax_amount = 0
            self.instance.discount_percentage = 0
            self.instance.discount_amount = 0
            self.instance.total_amount = 0

    def clean(self):
        cleaned_data = super().clean()
        service = cleaned_data.get('service')
        description = cleaned_data.get('description')
        unit_price = cleaned_data.get('unit_price')

        # If service is selected, use its price and description
        if service:
            if not description:
                cleaned_data['description'] = service.name
            if not unit_price:
                cleaned_data['unit_price'] = service.price

        # Either service or description must be provided
        if not service and not description:
            raise forms.ValidationError("Either select a service or provide a description.")

        return cleaned_data

class PaymentForm(forms.ModelForm):
    """Enhanced form for recording payments with dual payment method support"""
    
    payment_source = forms.ChoiceField(
        choices=[
            ('billing_office', 'Billing Office Payment'),
            ('patient_wallet', 'Patient Wallet Payment')
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Payment Source',
        initial='billing_office'
    )
    
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'payment_date', 'transaction_id', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.invoice = kwargs.pop('invoice', None)
        self.patient_wallet = kwargs.pop('patient_wallet', None)
        super().__init__(*args, **kwargs)
        
        # Add wallet balance info to the form if wallet is provided
        if self.patient_wallet:
            self.fields['payment_source'].help_text = f'Wallet Balance: ₦{self.patient_wallet.balance:.2f}'
    
    def clean(self):
        cleaned_data = super().clean()
        payment_source = cleaned_data.get('payment_source')
        amount = cleaned_data.get('amount')
        
        # Force wallet payment method for wallet payments
        if payment_source == 'patient_wallet':
            cleaned_data['payment_method'] = 'wallet'

        # Allow wallet payments even with insufficient balance (negative balance allowed)
        # Wallet balance validation removed to support negative balances
        
        if self.invoice and amount:
            remaining_balance = self.invoice.get_balance()
            if amount > remaining_balance:
                raise forms.ValidationError(
                    f'Payment amount exceeds remaining balance of ₦{remaining_balance:.2f}'
                )
        
        return cleaned_data


class AdmissionPaymentForm(forms.ModelForm):
    """Enhanced form for admission payments supporting both billing office and wallet payments"""

    payment_source = forms.ChoiceField(
        choices=[
            ('billing_office', 'Billing Office Payment'),
            ('patient_wallet', 'Patient Wallet Payment')
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Payment Source',
        initial='billing_office'
    )

    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'payment_date', 'transaction_id', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control datepicker', 'type': 'date'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.invoice = kwargs.pop('invoice', None)
        self.patient_wallet = kwargs.pop('patient_wallet', None)
        super().__init__(*args, **kwargs)

        if self.invoice:
            remaining_amount = self.invoice.get_balance()
            self.fields['amount'].initial = remaining_amount
            self.fields['amount'].widget.attrs['max'] = str(remaining_amount)

        # Update payment method choices based on payment source
        if self.patient_wallet:
            wallet_balance = self.patient_wallet.balance
            self.fields['payment_source'].help_text = f'Patient wallet balance: ₦{wallet_balance:.2f}'

    def clean(self):
        cleaned_data = super().clean()
        payment_source = cleaned_data.get('payment_source')
        amount = cleaned_data.get('amount')
        payment_method = cleaned_data.get('payment_method')

        if payment_source == 'patient_wallet':
            # Force wallet payment method for wallet payments
            cleaned_data['payment_method'] = 'wallet'

            # Allow wallet payments even with insufficient balance (negative balance allowed)
            # Wallet balance validation removed to support negative balances
            
        elif payment_source == 'billing_office':
            # Ensure wallet is not selected for billing office payments
            if payment_method == 'wallet':
                raise forms.ValidationError('Wallet payment method is only available for patient wallet payments.')

        # Validate amount against invoice balance
        if self.invoice and amount:
            remaining_amount = self.invoice.get_balance()
            if amount > remaining_amount:
                raise forms.ValidationError(
                    f'Payment amount cannot exceed the remaining balance of ₦{remaining_amount:.2f}'
                )

        return cleaned_data

class ServiceForm(forms.ModelForm):
    """Form for creating and editing services"""
    class Meta:
        model = Service
        fields = ['name', 'category', 'price', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class InvoiceSearchForm(forms.Form):
    """Form for searching and filtering invoices"""
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Search by invoice number or patient name'
    }))

    status = forms.ChoiceField(required=False, choices=[('', 'All Statuses')] + list(Invoice.STATUS_CHOICES),
                              widget=forms.Select(attrs={'class': 'form-select'}))

    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={
        'class': 'form-control datepicker',
        'type': 'date',
        'placeholder': 'From Date'
    }))

    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={
        'class': 'form-control datepicker',
        'type': 'date',
        'placeholder': 'To Date'
    }))
