from django import forms
from .models import Patient, MedicalHistory, Vitals
from django.core.validators import RegexValidator
from doctors.models import Specialization
import re
from nhia.models import NHIAPatient # Import NHIAPatient
import datetime

def generate_unique_nhia_reg_number():
    """
    Generates a unique NHIA registration number.
    Format: NHIA-YYYYMMDD-XXXX (where XXXX is a sequential number)
    """
    today = datetime.date.today()
    prefix = f"NHIA-{today.strftime('%Y%m%d')}"
    
    # Find the last NHIA patient registered today to get the next sequential number
    last_nhia_patient = NHIAPatient.objects.filter(
        nhia_reg_number__startswith=prefix
    ).order_by('-nhia_reg_number').first()

    if last_nhia_patient:
        try:
            # Extract the sequential number and increment it
            last_number_str = last_nhia_patient.nhia_reg_number.split('-')[-1]
            last_number = int(last_number_str)
            new_number = last_number + 1
        except (IndexError, ValueError):
            new_number = 1
    else:
        new_number = 1
    
    return f"{prefix}-{new_number:04d}"

class PatientForm(forms.ModelForm):
    """
    Form for patient registration and editing

    Features:
    - Automatic special character removal from name, location, and text fields
    - Phone number validation with international format support
    - Email and phone number uniqueness validation
    - Automatic patient ID generation
    """

    # Custom validators
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )

    @staticmethod
    def clean_special_characters(value, field_type='name'):
        """
        Remove special characters from input fields

        Args:
            value: The input string to clean
            field_type: Type of field ('name', 'location', 'general')

        Returns:
            Cleaned string with special characters removed
        """
        if not value:
            return value

        if field_type == 'name':
            # For names: allow letters, spaces, hyphens, apostrophes, and dots
            cleaned = re.sub(r"[^a-zA-Z\s\-'.]", '', value)
        elif field_type == 'location':
            # For locations: allow letters, spaces, hyphens, and dots
            cleaned = re.sub(r"[^a-zA-Z\s\-.]", '', value)
        elif field_type == 'general':
            # For general text: allow letters, numbers, spaces, hyphens, and basic punctuation
            cleaned = re.sub(r"[^a-zA-Z0-9\s\-.,']", '', value)
        else:
            # Default: remove most special characters but keep basic punctuation
            cleaned = re.sub(r"[^a-zA-Z0-9\s\-.,']", '', value)

        # Remove multiple spaces and strip
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

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

    def clean_first_name(self):
        """Clean special characters from first name"""
        first_name = self.cleaned_data.get('first_name')
        return self.clean_special_characters(first_name, 'name')

    def clean_last_name(self):
        """Clean special characters from last name"""
        last_name = self.cleaned_data.get('last_name')
        return self.clean_special_characters(last_name, 'name')

    def clean_emergency_contact_name(self):
        """Clean special characters from emergency contact name"""
        emergency_contact_name = self.cleaned_data.get('emergency_contact_name')
        return self.clean_special_characters(emergency_contact_name, 'name')

    def clean_city(self):
        """Clean special characters from city name"""
        city = self.cleaned_data.get('city')
        return self.clean_special_characters(city, 'location')

    def clean_state(self):
        """Clean special characters from state name"""
        state = self.cleaned_data.get('state')
        return self.clean_special_characters(state, 'location')

    def clean_country(self):
        """Clean special characters from country name"""
        country = self.cleaned_data.get('country')
        return self.clean_special_characters(country, 'location')

    def clean_occupation(self):
        """Clean special characters from occupation"""
        occupation = self.cleaned_data.get('occupation')
        return self.clean_special_characters(occupation, 'general')

    def clean_insurance_provider(self):
        """Clean special characters from insurance provider name"""
        insurance_provider = self.cleaned_data.get('insurance_provider')
        return self.clean_special_characters(insurance_provider, 'general')

    def save(self, commit=True):
        patient = super().save(commit=False)

        # Generate patient ID if this is a new patient
        if not patient.pk and not patient.patient_id:
            # Format: YYYYMMNNNN (numeric only, no letters or hyphens)
            import datetime
            year = datetime.date.today().year
            month = datetime.date.today().month
            prefix = f"{year}{month:02d}"

            # Get the last patient ID with the same date prefix
            last_patient = Patient.objects.filter(
                patient_id__startswith=prefix
            ).order_by('-patient_id').first()

            if last_patient:
                try:
                    # Extract the sequential number and increment it
                    last_number = int(last_patient.patient_id[len(prefix):])
                    new_number = last_number + 1
                except (IndexError, ValueError):
                    new_number = 1
            else:
                new_number = 1

            patient.patient_id = f"{prefix}{new_number:04d}"

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

class NHIARegistrationForm(forms.ModelForm):
    class Meta:
        model = NHIAPatient
        fields = ['nhia_reg_number', 'is_active']
        widgets = {
            'nhia_reg_number': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If updating an existing NHIAPatient, disable the nhia_reg_number field
        if self.instance and self.instance.pk:
            self.fields['nhia_reg_number'].widget.attrs['readonly'] = True
            self.fields['nhia_reg_number'].help_text = "NHIA Registration Number cannot be changed after creation."

    def clean_nhia_reg_number(self):
        nhia_reg_number = self.cleaned_data.get('nhia_reg_number')
        if nhia_reg_number and NHIAPatient.objects.filter(nhia_reg_number=nhia_reg_number).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This NHIA Registration Number is already in use.")
        return nhia_reg_number

class NHIAIndependentPatientForm(PatientForm):
    is_nhia_active = forms.BooleanField(
        label="Is NHIA Active?",
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta(PatientForm.Meta):
        fields = PatientForm.Meta.fields + ['is_nhia_active']

    def save(self, commit=True):
        patient = super().save(commit=True) # This calls PatientForm.save(commit=True)
        if commit:
            nhia_reg_number = generate_unique_nhia_reg_number()
            is_nhia_active = self.cleaned_data.get('is_nhia_active')
            NHIAPatient.objects.create(
                patient=patient,
                nhia_reg_number=nhia_reg_number,
                is_active=is_nhia_active
            )
        return patient
