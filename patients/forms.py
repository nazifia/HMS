from django import forms
from .models import Patient, MedicalHistory, Vitals, ClinicalNote
from django.core.validators import RegexValidator
from doctors.models import Specialization
import re
from nhia.models import NHIAPatient # Import NHIAPatient
from nhia.utils import generate_nhia_reg_number
from retainership.models import RetainershipPatient # Import RetainershipPatient
from retainership.utils import generate_retainership_reg_number
import datetime



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
    phone_number = forms.CharField(validators=[phone_regex], max_length=17, required=False)
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 'marital_status',
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
        # Uniqueness check removed as requested
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
            'weight', 'notes', 'recorded_by'
        ]
        widgets = {
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'blood_pressure_systolic': forms.NumberInput(attrs={'class': 'form-control'}),
            'blood_pressure_diastolic': forms.NumberInput(attrs={'class': 'form-control'}),
            'pulse_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'respiratory_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'oxygen_saturation': forms.NumberInput(attrs={'class': 'form-control'}),
            'height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'recorded_by': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        # Extract user from kwargs if provided
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Make recorded_by optional
        self.fields['recorded_by'].required = False

        # Auto-populate recorded_by field with current user's name
        if self.user and not self.instance.pk:  # Only for new records
            if hasattr(self.user, 'get_full_name') and self.user.get_full_name():
                self.fields['recorded_by'].initial = self.user.get_full_name()
            elif hasattr(self.user, 'username'):
                self.fields['recorded_by'].initial = self.user.username

    def clean_temperature(self):
        data = self.cleaned_data.get('temperature')
        if data is not None:
            try:
                return float(data)
            except (ValueError, TypeError):
                raise forms.ValidationError("Enter a valid number.")
        return data

    def clean_height(self):
        data = self.cleaned_data.get('height')
        if data is not None:
            try:
                return float(data)
            except (ValueError, TypeError):
                raise forms.ValidationError("Enter a valid number.")
        return data

    def clean_weight(self):
        data = self.cleaned_data.get('weight')
        if data is not None:
            try:
                return float(data)
            except (ValueError, TypeError):
                raise forms.ValidationError("Enter a valid number.")
        return data

    def clean(self):
        cleaned_data = super().clean()

        # Set default value for recorded_by if not provided
        if not cleaned_data.get('recorded_by'):
            cleaned_data['recorded_by'] = 'System'

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
        # Allow withdrawals even with insufficient balance (negative balance allowed)
        # Wallet balance validation removed to support negative balances
        return amount


class WalletTransferForm(forms.Form):
    recipient_patient = forms.ModelChoiceField(
        queryset=Patient.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-placeholder': 'Select recipient patient...'
        }),
        label='Transfer To Patient',
        help_text='Select the patient to transfer funds to',
        empty_label="Choose recipient patient..."
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount to transfer (e.g., 100.00)',
            'step': '0.01',
            'min': '0.01'
        }),
        label='Amount to Transfer',
        help_text='Enter the amount you want to transfer'
    )
    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional: Reason for this transfer (e.g., Payment for services, Family support)'
        }),
        label='Description (Optional)',
        help_text='Provide a reason for this transfer for record keeping'
    )

    def __init__(self, *args, **kwargs):
        self.wallet = kwargs.pop('wallet', None)
        super().__init__(*args, **kwargs)
        if self.wallet:
            # Exclude the current patient from recipient choices and only show active patients
            self.fields['recipient_patient'].queryset = Patient.objects.filter(
                is_active=True
            ).exclude(id=self.wallet.patient.id).order_by('first_name', 'last_name')
            
            # Add wallet balance info to amount field help text
            self.fields['amount'].help_text = f'Available balance: ₦{self.wallet.balance:,.2f}. Enter the amount you want to transfer.'

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        
        if not amount:
            raise forms.ValidationError("Transfer amount is required.")
            
        if amount <= 0:
            raise forms.ValidationError("Transfer amount must be greater than zero.")
            
        # Note: We allow transfers even if they exceed balance (as per current system design)
        # But we provide a warning message
        if self.wallet and amount > self.wallet.balance:
            # This is a warning, not an error - the system allows negative balances
            pass
            
        return amount

    def clean_recipient_patient(self):
        recipient = self.cleaned_data.get('recipient_patient')
        
        if not recipient:
            raise forms.ValidationError("Please select a recipient patient.")
            
        if not recipient.is_active:
            raise forms.ValidationError("Cannot transfer to an inactive patient. Please select an active patient.")
            
        if self.wallet and recipient and recipient.id == self.wallet.patient.id:
            raise forms.ValidationError("Cannot transfer funds to the same patient. Please select a different recipient.")
            
        return recipient

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        
        # Clean any potentially harmful content
        if description:
            # Remove any HTML tags or special characters that might cause issues
            import re
            description = re.sub(r'[<>"\']', '', description)
            description = description[:500]  # Ensure it doesn't exceed max length
            
        return description

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        recipient = cleaned_data.get('recipient_patient')
        
        # Additional cross-field validation
        if amount and recipient and self.wallet:
            # Check if recipient has a wallet (create if needed is handled in view)
            if hasattr(recipient, 'wallet') and not recipient.wallet.is_active:
                raise forms.ValidationError("Recipient's wallet is not active. Please contact administrator.")
                
        return cleaned_data


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

        # Allow debit adjustments even with insufficient balance (negative balance allowed)
        # Wallet balance validation removed to support negative balances

        return cleaned_data


class WalletTransactionSearchForm(forms.Form):
    TRANSACTION_TYPE_CHOICES = [
        ('', 'All Transaction Types'),
        ('', '--- Basic Transactions ---'),
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('', '--- Transfers ---'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('', '--- Hospital Services ---'),
        ('admission_fee', 'Admission Fee'),
        ('daily_admission_charge', 'Daily Admission Charge'),
        ('', '--- Medical Services ---'),
        ('lab_test_payment', 'Lab Test Payment'),
        ('pharmacy_payment', 'Pharmacy Payment'),
        ('consultation_fee', 'Consultation Fee'),
        ('procedure_fee', 'Procedure Fee'),
        ('', '--- Other ---'),
        ('adjustment', 'Adjustment'),
        ('insurance_claim', 'Insurance Claim'),
        ('discount_applied', 'Discount Applied'),
        ('penalty_fee', 'Penalty Fee'),
        ('reversal', 'Transaction Reversal'),
        ('bonus', 'Bonus Credit'),
        ('cashback', 'Cashback'),
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

from nhia.utils import generate_nhia_reg_number

class NHIAIndependentPatientForm(PatientForm):
    is_nhia_active = forms.BooleanField(
        label="Is NHIA Active?",
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta(PatientForm.Meta):
        fields = PatientForm.Meta.fields + ['is_nhia_active']
        exclude = ['allergies', 'chronic_diseases', 'current_medications', 'primary_doctor', 'notes', 'postal_code']

    def save(self, commit=True):
        patient = super().save(commit=False)
        patient.patient_type = 'nhia'  # Ensure type
        if commit:
            patient.save()
            if not hasattr(patient, 'nhia_info'):
                nhia_patient = NHIAPatient.objects.create(
                    patient=patient,
                    nhia_reg_number=generate_nhia_reg_number(),
                    is_active=self.cleaned_data.get('is_nhia_active', True)
                )
        return patient

class RetainershipRegistrationForm(forms.ModelForm):
    class Meta:
        model = RetainershipPatient
        fields = ['retainership_reg_number', 'is_active']
        widgets = {
            'retainership_reg_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If updating an existing RetainershipPatient, disable the retainership_reg_number field
        if self.instance and self.instance.pk:
            self.fields['retainership_reg_number'].widget.attrs['readonly'] = True
            self.fields['retainership_reg_number'].help_text = "Retainership Registration Number cannot be changed after creation."

    def clean_retainership_reg_number(self):
        retainership_reg_number = self.cleaned_data.get('retainership_reg_number')
        if retainership_reg_number and RetainershipPatient.objects.filter(retainership_reg_number=retainership_reg_number).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This Retainership Registration Number is already in use.")
        return retainership_reg_number

from retainership.utils import generate_retainership_reg_number

class RetainershipIndependentPatientForm(PatientForm):
    is_retainership_active = forms.BooleanField(
        label="Is Retainership Active?",
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta(PatientForm.Meta):
        fields = PatientForm.Meta.fields + ['is_retainership_active']
        exclude = ['allergies', 'chronic_diseases', 'current_medications', 'primary_doctor', 'notes', 'postal_code']

    def save(self, commit=True):
        patient = super().save(commit=False)
        patient.patient_type = 'retainership'  # Ensure type
        if commit:
            patient.save()
            if not hasattr(patient, 'retainership_info'):
                retainership_patient = RetainershipPatient.objects.create(
                    patient=patient,
                    retainership_reg_number=generate_retainership_reg_number(),
                    is_active=self.cleaned_data.get('is_retainership_active', True)
                )
        return patient


class ClinicalNoteForm(forms.ModelForm):
    """Form for adding and editing clinical notes"""

    class Meta:
        model = ClinicalNote
        fields = ['doctor', 'note']
        widgets = {
            'doctor': forms.Select(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Enter clinical note...'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Auto-populate doctor field with current user if they are a doctor
        if self.user and not self.instance.pk:
            self.fields['doctor'].initial = self.user

        # Add form-control class to all widgets
        for field_name, field in self.fields.items():
            widget = field.widget
            if not isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                existing_classes = widget.attrs.get('class', '')
                widget.attrs['class'] = (existing_classes + ' form-control').strip()
