from django import forms
from django.db.models import Q
from .models import Patient, MedicalHistory, Vitals, ClinicalNote, PhysiotherapyRequest, SharedWallet, WalletMembership
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

    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='First Name',
        help_text='Enter patient first name'
    )

    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Last Name',
        help_text='Enter patient last name'
    )

    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Date of Birth',
        help_text='Select patient date of birth'
    )

    gender = forms.ChoiceField(
        choices=[
            ('M', 'Male'),
            ('F', 'Female'),
            ('O', 'Other'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Gender',
        help_text='Select patient gender'
    )

    marital_status = forms.ChoiceField(
        choices=[
            ('', 'Select Marital Status'),
            ('single', 'Single'),
            ('married', 'Married'),
            ('divorced', 'Divorced'),
            ('widowed', 'Widowed'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Marital Status',
        help_text='Select patient marital status'
    )

    patient_type = forms.ChoiceField(
        choices=[
            ('regular', 'Regular'),
            ('nhia', 'NHIA'),
            ('private', 'Private Pay'),
            ('insurance', 'Private Insurance'),
            ('corporate', 'Corporate'),
            ('staff', 'Staff'),
            ('dependant', 'Dependant'),
            ('emergency', 'Emergency'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Patient Type',
        help_text='Select patient type'
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label='Email',
        help_text='Enter patient email address'
    )

    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Phone Number',
        help_text='Enter patient phone number'
    )

    emergency_contact_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Emergency Contact Name',
        help_text='Enter emergency contact name'
    )

    emergency_contact_relation = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Emergency Contact Relation',
        help_text='Enter emergency contact relation'
    )

    emergency_contact_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Emergency Contact Phone',
        help_text='Enter emergency contact phone number'
    )

    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Address',
        help_text='Enter patient address'
    )

    city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='City',
        help_text='Enter patient city'
    )

    state = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='State',
        help_text='Enter patient state'
    )

    postal_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Postal Code',
        help_text='Enter patient postal code'
    )

    country = forms.CharField(
        max_length=100,
        initial='India',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Country',
        help_text='Enter patient country'
    )

    allergies = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Allergies',
        help_text='Enter any known allergies'
    )

    chronic_diseases = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Chronic Diseases',
        help_text='Enter any chronic diseases'
    )

    current_medications = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Current Medications',
        help_text='Enter current medications'
    )

    occupation = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Occupation',
        help_text='Enter patient occupation'
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Notes',
        help_text='Enter any additional notes'
    )

    blood_group = forms.ChoiceField(
        choices=[
            ('', 'Select Blood Group'),
            ('A+', 'A+'),
            ('A-', 'A-'),
            ('B+', 'B+'),
            ('B-', 'B-'),
            ('AB+', 'AB+'),
            ('AB-', 'AB-'),
            ('O+', 'O+'),
            ('O-', 'O-'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Blood Group',
        help_text='Select patient blood group'
    )

    photo = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        label='Patient Photo',
        help_text='Upload patient photo (Primary)'
    )

    id_document = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        label='ID Document',
        help_text='Upload patient ID document'
    )

    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 'marital_status',
            'patient_type', 'email', 'phone_number', 'emergency_contact_name',
            'emergency_contact_relation', 'emergency_contact_phone', 'address',
            'city', 'state', 'postal_code', 'country', 'allergies', 'chronic_diseases',
            'current_medications', 'occupation', 'notes', 'blood_group', 'photo', 'id_document'
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

    def clean_city(self):
        """Clean special characters from city"""
        city = self.cleaned_data.get('city')
        return self.clean_special_characters(city, 'location')

    def clean_state(self):
        """Clean special characters from state"""
        state = self.cleaned_data.get('state')
        return self.clean_special_characters(state, 'location')

    def clean_country(self):
        """Clean special characters from country"""
        country = self.cleaned_data.get('country')
        return self.clean_special_characters(country, 'location')

    def clean_allergies(self):
        """Clean special characters from allergies"""
        allergies = self.cleaned_data.get('allergies')
        return self.clean_special_characters(allergies, 'text')

    def clean_chronic_diseases(self):
        """Clean special characters from chronic diseases"""
        chronic_diseases = self.cleaned_data.get('chronic_diseases')
        return self.clean_special_characters(chronic_diseases, 'text')

    def clean_current_medications(self):
        """Clean special characters from current medications"""
        current_medications = self.cleaned_data.get('current_medications')
        return self.clean_special_characters(current_medications, 'text')

    def clean_occupation(self):
        """Clean special characters from occupation"""
        occupation = self.cleaned_data.get('occupation')
        return self.clean_special_characters(occupation, 'text')

    def clean_notes(self):
        """Clean special characters from notes"""
        notes = self.cleaned_data.get('notes')
        return self.clean_special_characters(notes, 'text')

    def clean_special_characters(self, text, field_type='text'):
        """
        Clean special characters from text based on field type
        """
        if not text:
            return text

        # Define allowed characters based on field type
        if field_type == 'name':
            # Allow letters, spaces, hyphens, apostrophes, and periods
            allowed_chars = r"[^a-zA-Z\s\-\.']"
        elif field_type == 'location':
            # Allow letters, spaces, hyphens, apostrophes, periods, and commas
            allowed_chars = r"[^a-zA-Z\s\-\.',]"
        else:  # text fields
            # Allow most characters but remove potentially harmful ones
            allowed_chars = r"[<>\"']"

        # Remove disallowed characters
        cleaned_text = re.sub(allowed_chars, '', text)
        
        # Remove leading/trailing whitespace
        cleaned_text = cleaned_text.strip()
        
        # Replace multiple spaces with single space
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        return cleaned_text

    def save(self, commit=True):
        patient = super().save(commit=False)
        
        if commit:
            patient.save()
        
        return patient


class MedicalHistoryForm(forms.ModelForm):
    """
    Form for adding and editing medical history records
    """

    diagnosis = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Diagnosis',
        help_text='Enter the medical diagnosis'
    )

    treatment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Treatment',
        help_text='Describe the treatment provided'
    )

    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Date',
        help_text='Select the date of diagnosis'
    )

    doctor_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Doctor Name',
        help_text='Enter the name of the diagnosing doctor'
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Notes',
        help_text='Enter any additional notes'
    )

    class Meta:
        model = MedicalHistory
        fields = ['diagnosis', 'treatment', 'date', 'doctor_name', 'notes']


class VitalsForm(forms.ModelForm):
    """
    Form for recording patient vitals with comprehensive validation
    """

    temperature = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        min_value=30.0,
        max_value=45.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': 'Temperature in °C'
        }),
        label='Temperature (°C)',
        help_text='Enter temperature in Celsius (30.0 - 45.0)'
    )

    blood_pressure_systolic = forms.IntegerField(
        required=False,
        min_value=50,
        max_value=250,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Systolic (mmHg)'
        }),
        label='Blood Pressure - Systolic (mmHg)',
        help_text='Enter systolic blood pressure (50 - 250)'
    )

    blood_pressure_diastolic = forms.IntegerField(
        required=False,
        min_value=30,
        max_value=150,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Diastolic (mmHg)'
        }),
        label='Blood Pressure - Diastolic (mmHg)',
        help_text='Enter diastolic blood pressure (30 - 150)'
    )

    pulse_rate = forms.IntegerField(
        required=False,
        min_value=30,
        max_value=200,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Pulse rate (bpm)'
        }),
        label='Pulse Rate (bpm)',
        help_text='Enter pulse rate in beats per minute (30 - 200)'
    )

    respiratory_rate = forms.IntegerField(
        required=False,
        min_value=8,
        max_value=50,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Respiratory rate (breaths/min)'
        }),
        label='Respiratory Rate (breaths/min)',
        help_text='Enter respiratory rate (8 - 50)'
    )

    oxygen_saturation = forms.IntegerField(
        required=False,
        min_value=70,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Oxygen saturation (%)'
        }),
        label='Oxygen Saturation (%)',
        help_text='Enter oxygen saturation percentage (70 - 100)'
    )

    height = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        min_value=30.0,
        max_value=300.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': 'Height in cm'
        }),
        label='Height (cm)',
        help_text='Enter height in centimeters (30.0 - 300.0)'
    )

    weight = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        min_value=1.0,
        max_value=300.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': 'Weight in kg'
        }),
        label='Weight (kg)',
        help_text='Enter weight in kilograms (1.0 - 300.0)'
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Additional notes about vitals measurement'
        }),
        label='Notes',
        help_text='Enter any additional notes'
    )

    recorded_by = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Name of person recording vitals'
        }),
        label='Recorded By',
        help_text='Enter the name of the person recording these vitals'
    )

    class Meta:
        model = Vitals
        fields = [
            'temperature', 'blood_pressure_systolic', 'blood_pressure_diastolic',
            'pulse_rate', 'respiratory_rate', 'oxygen_saturation',
            'height', 'weight', 'notes', 'recorded_by'
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

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


class AddFundsForm(forms.Form):
    """
    Form for adding funds to patient wallet with enhanced validation and user experience
    """

    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01'
        }),
        label='Amount to Add',
        help_text='Enter the amount you want to add to the wallet'
    )

    payment_method = forms.ChoiceField(
        choices=[
            ('cash', 'Cash'),
            ('bank_transfer', 'Bank Transfer'),
            ('cheque', 'Cheque'),
            ('card', 'Credit/Debit Card'),
            ('mobile_money', 'Mobile Money'),
            ('other', 'Other')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Payment Method',
        help_text='Select the payment method used'
    )

    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional: Reason for this deposit (e.g., Initial deposit, Payment for services)'
        }),
        label='Description (Optional)',
        help_text='Provide a reason for this deposit for record keeping'
    )

    apply_to_outstanding = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Apply to Outstanding Charges',
        help_text='Check this box to automatically apply these funds to any outstanding charges'
    )

    def __init__(self, *args, **kwargs):
        self.wallet = kwargs.pop('wallet', None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        if not amount:
            raise forms.ValidationError("Amount is required.")

        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")

        return amount

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()

        # Clean any potentially harmful content
        if description:
            # Remove any HTML tags or special characters that might cause issues
            import re
            description = re.sub(r'[<>"\']', '', description)
            description = description[:500]  # Ensure it doesn't exceed max length

        return description


class WalletWithdrawalForm(forms.Form):
    """
    Form for wallet withdrawal with enhanced validation
    """

    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01'
        }),
        label='Amount to Withdraw',
        help_text='Enter the amount you want to withdraw from the wallet'
    )

    withdrawal_method = forms.ChoiceField(
        choices=[
            ('cash', 'Cash'),
            ('bank_transfer', 'Bank Transfer'),
            ('cheque', 'Cheque'),
            ('mobile_money', 'Mobile Money'),
            ('other', 'Other')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Withdrawal Method',
        help_text='Select the withdrawal method'
    )

    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional: Reason for this withdrawal'
        }),
        label='Description (Optional)',
        help_text='Provide a reason for this withdrawal for record keeping'
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
        label='Recipient Patient',
        help_text='Select the patient to receive the funds'
    )

    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
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
            'step': '0.01',
            'min': '0.01'
        }),
        label='Refund Amount',
        help_text='Enter the amount to refund to the patient'
    )

    reason = forms.ChoiceField(
        choices=[
            ('overpayment', 'Overpayment'),
            ('cancelled_service', 'Cancelled Service'),
            ('duplicate_payment', 'Duplicate Payment'),
            ('patient_request', 'Patient Request'),
            ('other', 'Other')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Refund Reason',
        help_text='Select the reason for this refund'
    )

    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Provide additional details about this refund'
        }),
        label='Additional Details (Optional)',
        help_text='Provide more information about this refund'
    )

    def __init__(self, *args, **kwargs):
        self.wallet = kwargs.pop('wallet', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        # No specific validation needed beyond what's in the fields
        return cleaned_data


class WalletAdjustmentForm(forms.Form):
    adjustment_type = forms.ChoiceField(
        choices=[
            ('credit', 'Credit Adjustment'),
            ('debit', 'Debit Adjustment')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Adjustment Type',
        help_text='Select whether this is a credit or debit adjustment'
    )

    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01'
        }),
        label='Adjustment Amount',
        help_text='Enter the adjustment amount'
    )

    reason = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Provide a detailed reason for this adjustment'
        }),
        label='Adjustment Reason',
        help_text='Provide a detailed explanation for this adjustment'
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
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('adjustment', 'Adjustment'),
        ('', '--- Medical Transactions ---'),
        ('admission_fee', 'Admission Fee'),
        ('daily_admission_charge', 'Daily Admission Charge'),
        ('lab_test_payment', 'Lab Test Payment'),
        ('pharmacy_payment', 'Pharmacy Payment'),
        ('consultation_fee', 'Consultation Fee'),
        ('procedure_fee', 'Procedure Fee'),
        ('', '--- Special Transactions ---'),
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
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Transaction Type'
    )

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Status'
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='Date From'
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='Date To'
    )

    min_amount = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Minimum amount'
        }),
        label='Minimum Amount'
    )

    max_amount = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Maximum amount'
        }),
        label='Maximum Amount'
    )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        min_amount = cleaned_data.get('min_amount')
        max_amount = cleaned_data.get('max_amount')

        # Validate date range
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("Date from cannot be after date to.")

        # Validate amount range
        if min_amount and max_amount and min_amount > max_amount:
            raise forms.ValidationError("Minimum amount cannot be greater than maximum amount.")

        return cleaned_data


class NHIAPatientForm(forms.ModelForm):
    """
    Form for registering NHIA patients
    """

    nhia_reg_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='NHIA Registration Number',
        help_text='Enter NHIA registration number'
    )

    is_active = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Is Active',
        help_text='Check if this NHIA registration is active'
    )

    class Meta:
        model = NHIAPatient
        fields = ['nhia_reg_number', 'is_active']

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
            'retainership_reg_number': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
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

    note = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Enter clinical note content...'
        }),
        label='Clinical Note',
        help_text='Enter detailed clinical observations and recommendations'
    )

    class Meta:
        model = ClinicalNote
        fields = ['note', 'doctor']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Auto-populate doctor field with current user if they are a doctor
        if self.user and not self.instance.pk:
            self.fields['doctor'].initial = self.user
            self.fields['doctor'].widget = forms.HiddenInput()
        elif self.instance.pk:
            # If editing existing note, make doctor field readonly
            self.fields['doctor'].widget.attrs['readonly'] = True

        # Add form-control class to all widgets
        for field_name, field in self.fields.items():
            widget = field.widget
            if not isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                existing_classes = widget.attrs.get('class', '')
                widget.attrs['class'] = (existing_classes + ' form-control').strip()


class PhysiotherapyRequestForm(forms.ModelForm):
    """
    Form for creating and editing physiotherapy requests
    """
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Auto-populate referring_doctor with current user if they are a doctor
        if self.user and not self.instance.pk:
            self.fields['referring_doctor'].initial = self.user
        
        # Filter users to only show doctors/physiotherapists
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['referring_doctor'].queryset = User.objects.filter(
            Q(profile__role__in=['Doctor', 'Physiotherapist']) |
            Q(is_staff=True)
        ).distinct()
        
        self.fields['physiotherapist'].queryset = User.objects.filter(
            Q(profile__role__in=['Physiotherapist']) |
            Q(is_staff=True)
        ).distinct()
        
        # Set empty labels for optional fields
        self.fields['referring_doctor'].empty_label = '-- Select Referring Doctor (Optional) --'
        self.fields['physiotherapist'].empty_label = '-- Select Physiotherapist (Optional) --'
        
        # Add form-control class to all widgets
        for field_name, field in self.fields.items():
            if field_name not in ['start_date', 'end_date']:
                widget = field.widget
                if not isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                    existing_classes = widget.attrs.get('class', '')
                    widget.attrs['class'] = (existing_classes + ' form-control').strip()
            else:
                # For date fields, add form-control and date input type
                self.fields[field_name].widget.attrs.update({
                    'class': 'form-control',
                    'type': 'date'
                })
    
    class Meta:
        model = PhysiotherapyRequest
        fields = [
            'referring_doctor', 'physiotherapist', 'diagnosis',
            'treatment_plan', 'notes', 'priority', 'start_date', 'end_date'
        ]
        widgets = {
            'diagnosis': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter primary diagnosis...'}),
            'treatment_plan': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe the proposed treatment plan...'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Additional notes or instructions...'}),
            'referring_doctor': forms.Select(attrs={'class': 'form-control', 'empty_label': '-- Select Referring Doctor (Optional) --'}),
            'physiotherapist': forms.Select(attrs={'class': 'form-control', 'empty_label': '-- Select Physiotherapist (Optional) --'}),
        }
    
    def clean_end_date(self):
        start_date = self.cleaned_data.get('start_date')
        end_date = self.cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError('End date cannot be before start date.')
        
        return end_date


# Shared Wallet Forms
class SharedWalletForm(forms.ModelForm):
    class Meta:
        model = SharedWallet
        fields = ['wallet_name', 'wallet_type', 'retainership_registration', 'is_active']
        widgets = {
            'wallet_name': forms.TextInput(attrs={'class': 'form-control'}),
            'wallet_type': forms.Select(attrs={'class': 'form-select'}),
            'retainership_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['retainership_registration'].required = False


class WalletMembershipForm(forms.ModelForm):
    class Meta:
        model = WalletMembership
        fields = ['patient', 'is_primary']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        wallet = kwargs.pop('wallet', None)
        super().__init__(*args, **kwargs)
        
        if wallet:
            # Filter out patients already in this wallet
            current_members = wallet.members.values_list('patient', flat=True)
            self.fields['patient'].queryset = Patient.objects.exclude(id__in=current_members)


class AddFundsToSharedWalletForm(forms.Form):
    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    payment_method = forms.ChoiceField(
        choices=[
            ('cash', 'Cash'),
            ('bank_transfer', 'Bank Transfer'),
            ('cheque', 'Cheque'),
            ('other', 'Other')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class TransferBetweenWalletsForm(forms.Form):
    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    recipient_wallet = forms.ModelChoiceField(
        queryset=SharedWallet.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        source_wallet = kwargs.pop('source_wallet', None)
        super().__init__(*args, **kwargs)
        
        if source_wallet:
            # Exclude the source wallet from recipient choices
            self.fields['recipient_wallet'].queryset = SharedWallet.objects.exclude(id=source_wallet.id)


class WalletSearchForm(forms.Form):
    """
    Form for searching patient wallets with focus on name and number search
    """
    PATIENT_TYPE_CHOICES = [
        ('', 'All Patient Types'),
        ('regular', 'Regular'),
        ('nhia', 'NHIA'),
        ('retainership', 'Retainership'),
    ]
    
    BALANCE_FILTER_CHOICES = [
        ('', 'All Balances'),
        ('positive', 'Positive Balance'),
        ('zero', 'Zero Balance'),
        ('negative', 'Negative Balance'),
    ]
    
    # Focused search fields for name and number
    patient_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by patient name (first or last)'
        }),
        label='Patient Name'
    )
    
    patient_id_or_phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by patient ID or phone number'
        }),
        label='Patient ID or Phone Number'
    )
    
    patient_type = forms.ChoiceField(
        choices=PATIENT_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Patient Type'
    )
    
    balance_filter = forms.ChoiceField(
        choices=BALANCE_FILTER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Balance Filter'
    )
    
    min_balance = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Minimum balance'
        }),
        label='Minimum Balance'
    )
    
    max_balance = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Maximum balance'
        }),
        label='Maximum Balance'
    )
