from django import forms
from .models import Patient, MedicalHistory, Vitals
from django.core.validators import RegexValidator
from doctors.models import Specialization

class PatientForm(forms.ModelForm):
    """Form for patient registration and editing"""

    # Custom validators
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )

    # Override fields for better validation and UI
    phone_number = forms.CharField(validators=[phone_regex], max_length=17)
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 'blood_group', 'marital_status',
            'address', 'city', 'state', 'postal_code', 'country', 'email', 'phone_number',
            'emergency_contact_name', 'emergency_contact_relation', 'emergency_contact_phone',
            'photo', 'id_document',
            'allergies', 'chronic_diseases', 'current_medications', 'primary_doctor',
            'insurance_provider', 'insurance_policy_number', 'insurance_expiry_date',
            'occupation', 'notes', 'is_active'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and Patient.objects.filter(email=email).exclude(id=self.instance.id if self.instance else None).exists():
            raise forms.ValidationError("This email is already registered with another patient.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and Patient.objects.filter(phone_number=phone_number).exclude(id=self.instance.id if self.instance else None).exists():
            raise forms.ValidationError("This phone number is already registered with another patient.")
        return phone_number

    def save(self, commit=True):
        patient = super().save(commit=False)

        # Generate patient ID if this is a new patient
        if not patient.pk and not patient.patient_id:
            # Format: PT-YYYYMMDD-XXXX where XXXX is a sequential number
            import datetime
            today = datetime.date.today().strftime('%Y%m%d')

            # Get the last patient ID with the same date prefix
            last_patient = Patient.objects.filter(
                patient_id__startswith=f'PT-{today}'
            ).order_by('-patient_id').first()

            if last_patient:
                # Extract the sequential number and increment it
                last_seq = int(last_patient.patient_id.split('-')[-1])
                new_seq = last_seq + 1
            else:
                new_seq = 1

            patient.patient_id = f'PT-{today}-{new_seq:04d}'

        if commit:
            patient.save()
        return patient

class MedicalHistoryForm(forms.ModelForm):
    """Form for adding and editing medical history records"""

    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = MedicalHistory
        fields = ['diagnosis', 'treatment', 'date', 'doctor_name', 'notes']
        widgets = {
            'treatment': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            # Add form-control to all widgets except checkboxes/radios
            if not isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                existing_classes = widget.attrs.get('class', '')
                widget.attrs['class'] = (existing_classes + ' form-control').strip()

class VitalsForm(forms.ModelForm):
    """Form for recording patient vitals"""

    class Meta:
        model = Vitals
        fields = [
            'temperature', 'blood_pressure_systolic', 'blood_pressure_diastolic',
            'pulse_rate', 'respiratory_rate', 'oxygen_saturation', 'height',
            'weight', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()

        # Calculate BMI if height and weight are provided
        height = cleaned_data.get('height')
        weight = cleaned_data.get('weight')

        if height and weight and height > 0:
            height_in_meters = height / 100
            bmi = weight / (height_in_meters ** 2)
            cleaned_data['bmi'] = round(bmi, 2)

        return cleaned_data

class PatientSearchForm(forms.Form):
    """Form for searching patients"""

    search = forms.CharField(required=False, label='Search',
                            widget=forms.TextInput(attrs={'placeholder': 'Name, ID, Phone or Email'}))
    gender = forms.ChoiceField(required=False, choices=[('', 'All')] + list(Patient.GENDER_CHOICES))
    blood_group = forms.ChoiceField(required=False, choices=[('', 'All')] + list(Patient.BLOOD_GROUP_CHOICES))
    city = forms.CharField(required=False)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

def get_specialization_choices():
    return [(s.id, s.name) for s in Specialization.objects.all()]

class AddFundsForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount to add',
            'step': '0.01'
        }),
        label='Amount to Add'
    )
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional description for this transaction'
        }),
        label='Description (Optional)'
    )
    payment_method = forms.ChoiceField(
        choices=[
            ('cash', 'Cash'),
            ('bank_transfer', 'Bank Transfer'),
            ('card', 'Card Payment'),
            ('mobile_money', 'Mobile Money'),
            ('check', 'Check'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Payment Method'
    )


class WalletWithdrawalForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount to withdraw',
            'step': '0.01'
        }),
        label='Amount to Withdraw'
    )
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Reason for withdrawal'
        }),
        label='Description (Optional)'
    )
    withdrawal_method = forms.ChoiceField(
        choices=[
            ('cash', 'Cash'),
            ('bank_transfer', 'Bank Transfer'),
            ('check', 'Check'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Withdrawal Method'
    )

    def __init__(self, *args, **kwargs):
        self.wallet = kwargs.pop('wallet', None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if self.wallet and amount > self.wallet.balance:
            raise forms.ValidationError(f"Insufficient balance. Available balance: ₦{self.wallet.balance}")
        return amount


class WalletTransferForm(forms.Form):
    recipient_patient = forms.ModelChoiceField(
        queryset=Patient.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Transfer To Patient',
        help_text='Select the patient to transfer funds to'
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount to transfer',
            'step': '0.01'
        }),
        label='Amount to Transfer'
    )
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Reason for transfer'
        }),
        label='Description (Optional)'
    )

    def __init__(self, *args, **kwargs):
        self.wallet = kwargs.pop('wallet', None)
        super().__init__(*args, **kwargs)
        if self.wallet:
            # Exclude the current patient from recipient choices
            self.fields['recipient_patient'].queryset = Patient.objects.filter(
                is_active=True
            ).exclude(id=self.wallet.patient.id)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if self.wallet and amount > self.wallet.balance:
            raise forms.ValidationError(f"Insufficient balance. Available balance: ₦{self.wallet.balance}")
        return amount

    def clean_recipient_patient(self):
        recipient = self.cleaned_data.get('recipient_patient')
        if self.wallet and recipient and recipient.id == self.wallet.patient.id:
            raise forms.ValidationError("Cannot transfer to the same patient.")
        return recipient


class WalletRefundForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter refund amount',
            'step': '0.01'
        }),
        label='Refund Amount'
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for refund'
        }),
        label='Refund Reason'
    )
    reference_invoice = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Related invoice number (optional)'
        }),
        label='Reference Invoice (Optional)'
    )


class WalletAdjustmentForm(forms.Form):
    ADJUSTMENT_TYPES = (
        ('credit', 'Credit Adjustment'),
        ('debit', 'Debit Adjustment'),
    )

    adjustment_type = forms.ChoiceField(
        choices=ADJUSTMENT_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Adjustment Type'
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter adjustment amount',
            'step': '0.01'
        }),
        label='Adjustment Amount'
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for adjustment'
        }),
        label='Adjustment Reason'
    )

    def __init__(self, *args, **kwargs):
        self.wallet = kwargs.pop('wallet', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        adjustment_type = cleaned_data.get('adjustment_type')
        amount = cleaned_data.get('amount')

        if adjustment_type == 'debit' and self.wallet and amount > self.wallet.balance:
            raise forms.ValidationError(f"Insufficient balance for debit adjustment. Available balance: ₦{self.wallet.balance}")

        return cleaned_data


class WalletTransactionSearchForm(forms.Form):
    TRANSACTION_TYPE_CHOICES = [
        ('', 'All Transaction Types'),
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('adjustment', 'Adjustment'),
    ]

    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by description or reference number'
        }),
        label='Search'
    )
    transaction_type = forms.ChoiceField(
        choices=TRANSACTION_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Transaction Type'
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Status'
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='From Date'
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='To Date'
    )
    amount_min = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minimum amount',
            'step': '0.01'
        }),
        label='Min Amount'
    )
    amount_max = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Maximum amount',
            'step': '0.01'
        }),
        label='Max Amount'
    )
