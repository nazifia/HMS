from django import forms
from django.utils import timezone
from .models import ConsultationOrder, ConsultingRoom, WaitingList, Referral, Consultation
from laboratory.models import TestRequest
from radiology.models import RadiologyOrder
from pharmacy.models import Prescription
from accounts.models import Department, CustomUser
from patients.models import Patient, Vitals
from appointments.models import Appointment


class ConsultingRoomForm(forms.ModelForm):
    """Form for creating and editing consulting rooms"""
    
    class Meta:
        model = ConsultingRoom
        fields = ['room_number', 'floor', 'department', 'description', 'is_active']
        widgets = {
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'floor': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select select2'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set queryset for department dropdown
        self.fields['department'].queryset = Department.objects.all().order_by('name')
        # Set empty label for department
        self.fields['department'].empty_label = "Select Department (Optional)"


class WaitingListForm(forms.ModelForm):
    """Form for adding patients to the waiting list"""
    
    class Meta:
        model = WaitingList
        fields = ['patient', 'consulting_room', 'doctor', 'appointment', 'priority', 'notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select select2'}),
            'consulting_room': forms.Select(attrs={'class': 'form-select select2'}),
            'doctor': forms.Select(attrs={'class': 'form-select select2'}),
            'appointment': forms.Select(attrs={'class': 'form-select select2'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set querysets for dropdowns
        self.fields['patient'].queryset = Patient.objects.all().order_by('first_name', 'last_name')
        self.fields['consulting_room'].queryset = ConsultingRoom.objects.filter(is_active=True).order_by('room_number')
        self.fields['doctor'].queryset = CustomUser.objects.filter(is_active=True, profile__role='doctor').order_by('first_name', 'last_name')
        self.fields['appointment'].queryset = Appointment.objects.filter(
            status__in=['scheduled', 'confirmed']
        ).order_by('appointment_date', 'appointment_time')
        
        # Set empty labels
        self.fields['doctor'].empty_label = "Select Doctor (Optional)"
        self.fields['appointment'].empty_label = "Select Appointment (Optional)"


class ReferralForm(forms.ModelForm):
    """Form for creating referrals"""

    authorization_code_input = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter authorization code (if required)'
        }),
        help_text="Required for NHIA patients referred from NHIA to non-NHIA units"
    )

    class Meta:
        model = Referral
        fields = ['patient', 'referred_to', 'reason', 'notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select select2'}),
            'referred_to': forms.Select(attrs={'class': 'form-select select2'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set querysets for dropdowns
        self.fields['patient'].queryset = Patient.objects.all().order_by('first_name', 'last_name')
        self.fields['referred_to'].queryset = CustomUser.objects.filter(
            is_active=True,
            profile__role='doctor'
        ).order_by('first_name', 'last_name')

        # Set empty labels
        self.fields['referred_to'].empty_label = "Select Referred Doctor"

    def clean_authorization_code_input(self):
        """Validate authorization code if provided"""
        code_str = self.cleaned_data.get('authorization_code_input', '').strip()
        if not code_str:
            return None

        from nhia.models import AuthorizationCode
        try:
            auth_code = AuthorizationCode.objects.get(code=code_str)
            if not auth_code.is_valid():
                raise forms.ValidationError(f"Authorization code is {auth_code.status}")
            return auth_code
        except AuthorizationCode.DoesNotExist:
            raise forms.ValidationError("Invalid authorization code")

    def save(self, commit=True):
        instance = super().save(commit=False)
        auth_code = self.cleaned_data.get('authorization_code_input')
        if auth_code:
            instance.authorization_code = auth_code
            instance.authorization_status = 'authorized'
        if commit:
            instance.save()
        return instance


class ConsultationForm(forms.ModelForm):
    """Form for creating and editing consultations"""

    authorization_code_input = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter authorization code (if required)'
        }),
        help_text="Required for NHIA patients in non-NHIA consulting rooms"
    )

    class Meta:
        model = Consultation
        fields = ['patient', 'doctor', 'vitals', 'chief_complaint', 'symptoms', 'diagnosis', 'consultation_notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select select2'}),
            'doctor': forms.Select(attrs={'class': 'form-select select2'}),
            'vitals': forms.Select(attrs={'class': 'form-select select2'}),
            'chief_complaint': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'symptoms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'consultation_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set querysets for dropdowns
        self.fields['patient'].queryset = Patient.objects.all().order_by('first_name', 'last_name')
        self.fields['doctor'].queryset = CustomUser.objects.filter(
            is_active=True,
            profile__role='doctor'
        ).order_by('first_name', 'last_name')
        self.fields['vitals'].queryset = Vitals.objects.all().order_by('-date_time')

        # Set empty labels
        self.fields['doctor'].empty_label = "Select Doctor (Optional)"
        self.fields['vitals'].empty_label = "Select Vitals (Optional)"

    def clean_authorization_code_input(self):
        """Validate authorization code if provided"""
        code_str = self.cleaned_data.get('authorization_code_input', '').strip()
        if not code_str:
            return None

        from nhia.models import AuthorizationCode
        try:
            auth_code = AuthorizationCode.objects.get(code=code_str)
            if not auth_code.is_valid():
                raise forms.ValidationError(f"Authorization code is {auth_code.status}")
            return auth_code
        except AuthorizationCode.DoesNotExist:
            raise forms.ValidationError("Invalid authorization code")

    def save(self, commit=True):
        instance = super().save(commit=False)
        auth_code = self.cleaned_data.get('authorization_code_input')
        if auth_code:
            instance.authorization_code = auth_code
            instance.authorization_status = 'authorized'
        if commit:
            instance.save()
        return instance


class VitalsSelectionForm(forms.Form):
    """Form for selecting vitals for a consultation"""
    
    vitals = forms.ModelChoiceField(
        queryset=Vitals.objects.none(),  # Will be set in __init__
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        required=False,
        empty_label="Select Vitals (Optional)"
    )
    
    def __init__(self, patient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set queryset for vitals dropdown based on the patient
        self.fields['vitals'].queryset = Vitals.objects.filter(
            patient=patient
        ).order_by('-date_time')


class ConsultationOrderForm(forms.ModelForm):
    """Form for creating orders from consultations"""
    
    ORDER_TYPE_CHOICES = (
        ('', 'Select Order Type'),
        ('lab_test', 'Laboratory Test'),
        ('radiology', 'Radiology Order'),
        ('prescription', 'Prescription'),
    )
    
    order_type = forms.ChoiceField(
        choices=ORDER_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Order Type'
    )
    
    # Fields for lab test orders
    lab_tests = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.SelectMultiple(attrs={'class': 'form-select select2'}),
        required=False,
        label='Laboratory Tests'
    )
    
    # Fields for radiology orders
    radiology_test = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        required=False,
        label='Radiology Test',
        empty_label="Select Radiology Test"
    )
    
    # Fields for prescriptions
    diagnosis = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False,
        label='Diagnosis'
    )
    
    prescription_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label='Prescription Notes'
    )
    
    # Common fields
    priority = forms.ChoiceField(
        choices=[
            ('normal', 'Normal'),
            ('urgent', 'Urgent'),
            ('emergency', 'Emergency')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='normal',
        label='Priority'
    )
    
    clinical_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label='Clinical Notes'
    )
    
    class Meta:
        model = ConsultationOrder
        fields = ['order_type', 'priority', 'clinical_notes']
    
    def __init__(self, *args, **kwargs):
        self.consultation = kwargs.pop('consultation', None)
        super().__init__(*args, **kwargs)
        
        # Set querysets for dropdowns
        if self.consultation:
            # Lab tests
            from laboratory.models import Test
            self.fields['lab_tests'].queryset = Test.objects.filter(is_active=True)
            
            # Radiology tests
            from radiology.models import RadiologyTest
            self.fields['radiology_test'].queryset = RadiologyTest.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        order_type = cleaned_data.get('order_type')
        
        # Validate required fields based on order type
        if order_type == 'lab_test':
            if not cleaned_data.get('lab_tests'):
                raise forms.ValidationError("Please select at least one laboratory test.")
        elif order_type == 'radiology':
            if not cleaned_data.get('radiology_test'):
                raise forms.ValidationError("Please select a radiology test.")
        elif order_type == 'prescription':
            diagnosis = cleaned_data.get('diagnosis')
            if not diagnosis:
                raise forms.ValidationError("Diagnosis is required for prescriptions.")
        
        return cleaned_data


class QuickLabOrderForm(forms.Form):
    """Quick form for creating lab test orders"""
    
    tests = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.SelectMultiple(attrs={'class': 'form-select select2'}),
        label='Laboratory Tests'
    )
    
    priority = forms.ChoiceField(
        choices=[
            ('normal', 'Normal'),
            ('urgent', 'Urgent'),
            ('emergency', 'Emergency')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='normal'
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label='Notes'
    )
    
    def __init__(self, *args, **kwargs):
        self.consultation = kwargs.pop('consultation', None)
        super().__init__(*args, **kwargs)
        
        # Set queryset for tests
        from laboratory.models import Test
        self.fields['tests'].queryset = Test.objects.filter(is_active=True).select_related('category')
    
    def save(self, commit=True):
        """Create a lab test request from the form data"""
        if not self.consultation:
            raise ValueError("Consultation is required to create a lab test order")
            
        from laboratory.models import TestRequest
            
        # Create the test request
        test_request = TestRequest(
            patient=self.consultation.patient,
            doctor=self.consultation.doctor,
            request_date=timezone.now().date(),
            priority=self.cleaned_data['priority'],
            notes=self.cleaned_data['notes'],
            created_by=self.consultation.doctor
        )
        
        if commit:
            test_request.save()
            test_request.tests.set(self.cleaned_data['tests'])
            
            # Create consultation order link
            content_type = ContentType.objects.get_for_model(TestRequest)
            ConsultationOrder.objects.create(
                consultation=self.consultation,
                order_type='lab_test',
                content_type=content_type,
                object_id=test_request.id,
                created_by=self.consultation.doctor
            )
            
        return test_request


class QuickRadiologyOrderForm(forms.Form):
    """Quick form for creating radiology orders"""
    
    test = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        label='Radiology Test'
    )
    
    priority = forms.ChoiceField(
        choices=[
            ('normal', 'Normal'),
            ('urgent', 'Urgent'),
            ('emergency', 'Emergency')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='normal'
    )
    
    clinical_information = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label='Clinical Information'
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        required=False,
        label='Notes'
    )
    
    def __init__(self, *args, **kwargs):
        self.consultation = kwargs.pop('consultation', None)
        super().__init__(*args, **kwargs)
        
        # Set queryset for tests
        from radiology.models import RadiologyTest
        self.fields['test'].queryset = RadiologyTest.objects.filter(is_active=True).select_related('category')
    
    def save(self, commit=True):
        """Create a radiology order from the form data"""
        if not self.consultation:
            raise ValueError("Consultation is required to create a radiology order")
            
        from radiology.models import RadiologyOrder
            
        # Create the radiology order
        radiology_order = RadiologyOrder(
            patient=self.consultation.patient,
            test=self.cleaned_data['test'],
            referring_doctor=self.consultation.doctor,
            order_date=timezone.now(),
            priority=self.cleaned_data['priority'],
            clinical_information=self.cleaned_data['clinical_information'],
            notes=self.cleaned_data['notes']
        )
        
        if commit:
            radiology_order.save()
            
            # Create consultation order link
            content_type = ContentType.objects.get_for_model(RadiologyOrder)
            ConsultationOrder.objects.create(
                consultation=self.consultation,
                order_type='radiology',
                content_type=content_type,
                object_id=radiology_order.id,
                created_by=self.consultation.doctor
            )
            
        return radiology_order


class QuickPrescriptionForm(forms.Form):
    """Quick form for creating prescriptions"""
    
    diagnosis = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Diagnosis'
    )
    
    prescription_type = forms.ChoiceField(
        choices=[
            ('outpatient', 'Out-Patient (Take-Home)'),
            ('inpatient', 'In-Patient (MAR/eMAR)')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='outpatient',
        label='Prescription Type'
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label='Notes'
    )
    
    def __init__(self, *args, **kwargs):
        self.consultation = kwargs.pop('consultation', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        """Create a prescription from the form data"""
        if not self.consultation:
            raise ValueError("Consultation is required to create a prescription")
            
        from pharmacy.models import Prescription
            
        # Create the prescription
        prescription = Prescription(
            patient=self.consultation.patient,
            doctor=self.consultation.doctor,
            prescription_date=timezone.now().date(),
            diagnosis=self.cleaned_data['diagnosis'],
            prescription_type=self.cleaned_data['prescription_type'],
            notes=self.cleaned_data['notes']
        )
        
        if commit:
            prescription.save()
            
            # Create consultation order link
            content_type = ContentType.objects.get_for_model(Prescription)
            ConsultationOrder.objects.create(
                consultation=self.consultation,
                order_type='prescription',
                content_type=content_type,
                object_id=prescription.id,
                created_by=self.consultation.doctor
            )
            
        return prescription