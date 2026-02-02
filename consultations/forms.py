from django import forms
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
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
    """Form for creating referrals to departments/units/specialists"""

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
        fields = ['patient', 'referral_type', 'referred_to_department', 'referred_to_specialty', 'referred_to_unit', 'referred_to_doctor', 'reason', 'notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'referral_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_referral_type'}),
            'referred_to_department': forms.Select(attrs={'class': 'form-select', 'id': 'id_referred_to_department'}),
            'referred_to_specialty': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_referred_to_specialty', 'placeholder': 'e.g., Cardiology, Neurology'}),
            'referred_to_unit': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_referred_to_unit', 'placeholder': 'e.g., ICU, Emergency'}),
            'referred_to_doctor': forms.Select(attrs={'class': 'form-select select2', 'id': 'id_referred_to_doctor'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set querysets for dropdowns
        self.fields['patient'].queryset = Patient.objects.all().order_by('first_name', 'last_name')
        self.fields['referred_to_department'].queryset = Department.objects.all().order_by('name')
        
        # Add unit suggestions as placeholder
        from .department_units import COMMON_UNITS
        unit_placeholder = "e.g., " + ", ".join(COMMON_UNITS[:3]) + "..."
        self.fields['referred_to_unit'].widget.attrs['placeholder'] = unit_placeholder
        
        # Add specialty suggestions as placeholder  
        specialty_placeholder = "e.g., Cardiology, Neurology, Orthopedics..."
        self.fields['referred_to_specialty'].widget.attrs['placeholder'] = specialty_placeholder

        # Get doctors using multiple role systems with fallback to all active users
        from django.db.models import Q

        # Try different role systems
        doctors_queryset = CustomUser.objects.filter(
            Q(is_active=True) & (
                Q(roles__name__iexact='doctor') |  # Many-to-many roles
                Q(profile__role__iexact='doctor') |  # Profile role
                Q(groups__name__iexact='doctor') |  # Django groups
                Q(is_staff=True)  # Fallback: staff users
            )
        ).distinct().order_by('first_name', 'last_name')

        # If no doctors found with role filtering, fall back to all active users
        if not doctors_queryset.exists():
            doctors_queryset = CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name')

        self.fields['referred_to_doctor'].queryset = doctors_queryset

        # Set empty labels
        self.fields['referred_to_department'].empty_label = "Select Department"
        self.fields['referred_to_doctor'].empty_label = "Select Doctor"

        # Set field labels with explicit messaging
        self.fields['referral_type'].label = "Refer To"
        self.fields['referred_to_department'].label = "Target Department *"
        self.fields['referred_to_specialty'].label = "Target Specialty"
        self.fields['referred_to_unit'].label = "Target Unit"
        self.fields['referred_to_doctor'].label = "Specific Doctor (Optional)"
        
        # Add help text for explicit targeting
        self.fields['referred_to_department'].help_text = "Select the department that will receive this referral. This is REQUIRED."
        self.fields['referral_type'].help_text = "Choose the type of destination. Department is the most common and explicit option."
        self.fields['referred_to_specialty'].help_text = "Optional: Specify a specialty within the department."
        self.fields['referred_to_unit'].help_text = "Optional: Specify a specific unit within the department."

        # Make all referral destination fields not required (validation in clean method)
        self.fields['referred_to_department'].required = False
        self.fields['referred_to_specialty'].required = False
        self.fields['referred_to_unit'].required = False
        self.fields['referred_to_doctor'].required = False

        # Set initial value for referral_type if not already set
        if not self.initial.get('referral_type'):
            self.fields['referral_type'].initial = 'department'

    def clean(self):
        cleaned_data = super().clean()
        referral_type = cleaned_data.get('referral_type')
        referred_to_department = cleaned_data.get('referred_to_department')
        referred_to_unit = cleaned_data.get('referred_to_unit')
        referred_to_specialty = cleaned_data.get('referred_to_specialty')
        referred_to_doctor = cleaned_data.get('referred_to_doctor')

        # Import mapping functions
        from .referral_mappings import get_department_for_unit, get_department_for_specialty

        # ENFORCE EXPLICIT DEPARTMENT TARGETING
        # Department is ALWAYS required for all referral types to ensure explicit routing
        if not referred_to_department:
            # Try to auto-detect from specialty or unit if provided
            detected_dept = None
            
            if referral_type == 'specialty' and referred_to_specialty:
                detected_dept = get_department_for_specialty(referred_to_specialty)
                if detected_dept:
                    from accounts.models import Department
                    try:
                        dept = Department.objects.get(name=detected_dept)
                        cleaned_data['referred_to_department'] = dept
                        detected_dept = dept
                    except Department.DoesNotExist:
                        raise forms.ValidationError(
                            f"Department '{detected_dept}' detected for specialty '{referred_to_specialty}' not found. "
                            f"Please select the target department explicitly."
                        )
            
            elif referral_type == 'unit' and referred_to_unit:
                detected_dept = get_department_for_unit(referred_to_unit)
                if detected_dept:
                    from accounts.models import Department
                    try:
                        dept = Department.objects.get(name=detected_dept)
                        cleaned_data['referred_to_department'] = dept
                        detected_dept = dept
                    except Department.DoesNotExist:
                        raise forms.ValidationError(
                            f"Department '{detected_dept}' detected for unit '{referred_to_unit}' not found. "
                            f"Please select the target department explicitly."
                        )
            
            # If still no department, raise validation error
            if not cleaned_data.get('referred_to_department'):
                raise forms.ValidationError(
                    "Target Department is REQUIRED. Please explicitly select the department "
                    "that should receive this referral. This ensures the referral is routed "
                    "to the correct clinical area."
                )

        # Validate based on referral type
        if referral_type == 'department':
            if not referred_to_department:
                raise forms.ValidationError("Please select a department for department referral.")
        
        elif referral_type == 'specialty':
            if not referred_to_specialty:
                raise forms.ValidationError("Please specify specialty.")
            
            # Auto-detect department from specialty if not selected
            if not referred_to_department:
                auto_detected_dept = get_department_for_specialty(referred_to_specialty)
                if auto_detected_dept:
                    from accounts.models import Department
                    try:
                        dept = Department.objects.get(name=auto_detected_dept)
                        cleaned_data['referred_to_department'] = dept
                    except Department.DoesNotExist:
                        raise forms.ValidationError(f"Auto-detected department '{auto_detected_dept}' not found. Please select department manually.")
                else:
                    raise forms.ValidationError(f"Could not auto-detect department for specialty '{referred_to_specialty}'. Please select department manually.")
        
        elif referral_type == 'unit':
            if not referred_to_unit:
                raise forms.ValidationError("Please specify unit.")
            
            # Auto-detect department from unit if not selected
            if not referred_to_department:
                auto_detected_dept = get_department_for_unit(referred_to_unit)
                if auto_detected_dept:
                    from accounts.models import Department
                    try:
                        dept = Department.objects.get(name=auto_detected_dept)
                        cleaned_data['referred_to_department'] = dept
                    except Department.DoesNotExist:
                        raise forms.ValidationError(f"Auto-detected department '{auto_detected_dept}' not found. Please select department manually.")
                else:
                    raise forms.ValidationError(f"Could not auto-detect department for unit '{referred_to_unit}'. Please select department manually.")
        
        elif referral_type == 'doctor':
            if not referred_to_doctor:
                raise forms.ValidationError("Please select a doctor for doctor referral.")

        # Validate department consistency (case-insensitive comparison)
        if referred_to_department and referred_to_unit:
            mapped_dept = get_department_for_unit(referred_to_unit)
            if mapped_dept and mapped_dept.lower() != referred_to_department.name.lower():
                # Auto-correct the department instead of raising an error
                from accounts.models import Department
                try:
                    correct_dept = Department.objects.get(name__iexact=mapped_dept)
                    cleaned_data['referred_to_department'] = correct_dept
                except Department.DoesNotExist:
                    raise forms.ValidationError(
                        f"Unit '{referred_to_unit}' belongs to department '{mapped_dept}', "
                        f"but you selected '{referred_to_department.name}'. Please correct the department selection."
                    )

        if referred_to_department and referred_to_specialty:
            mapped_dept = get_department_for_specialty(referred_to_specialty, preferred_unit=referred_to_unit)
            if mapped_dept and mapped_dept.lower() != referred_to_department.name.lower():
                # Auto-correct the department instead of raising an error
                from accounts.models import Department
                try:
                    correct_dept = Department.objects.get(name__iexact=mapped_dept)
                    cleaned_data['referred_to_department'] = correct_dept
                except Department.DoesNotExist:
                    raise forms.ValidationError(
                        f"Specialty '{referred_to_specialty}' belongs to department '{mapped_dept}', "
                        f"but you selected '{referred_to_department.name}'. Please correct the department selection."
                    )

        return cleaned_data

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
        fields = ['patient', 'doctor', 'vitals', 'consultation_date', 'status', 'chief_complaint', 'symptoms', 'diagnosis', 'consultation_notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select select2'}),
            'doctor': forms.Select(attrs={'class': 'form-select select2'}),
            'vitals': forms.Select(attrs={'class': 'form-select select2'}),
            'consultation_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'chief_complaint': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'symptoms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'consultation_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        # Extract current user from initial data if provided
        current_user = kwargs.get('initial', {}).get('doctor') if 'initial' in kwargs else None
        
        super().__init__(*args, **kwargs)
        # Set querysets for dropdowns
        self.fields['patient'].queryset = Patient.objects.all().order_by('first_name', 'last_name')
        
        # Build doctor queryset - include current user even if not in standard doctor filter
        base_qs = CustomUser.objects.filter(is_active=True)
        doctor_qs = base_qs.filter(
            Q(profile__role='doctor') |
            Q(profile__specialization__isnull=False)
        ).order_by('first_name', 'last_name')
        
        # If no doctors found with role filter, use all active users
        if not doctor_qs.exists():
            doctor_qs = base_qs.order_by('first_name', 'last_name')
        
        # Add current user to queryset if not already included
        if current_user and current_user.id:
            if not doctor_qs.filter(id=current_user.id).exists():
                doctor_qs = (doctor_qs | base_qs.filter(id=current_user.id)).distinct()
        
        self.fields['doctor'].queryset = doctor_qs
        self.fields['vitals'].queryset = Vitals.objects.all().order_by('-date_time')

        # Set empty labels
        self.fields['doctor'].empty_label = "Select Doctor (Optional)"
        self.fields['vitals'].empty_label = "Select Vitals (Optional)"
        
        # Auto-fetch authorization code for NHIA patients
        patient = self.initial.get('patient') if hasattr(self, 'initial') else None
        if patient and hasattr(patient, 'patient_type') and patient.patient_type == 'nhia':
            self._auto_fetch_authorization_code(patient)

    def _auto_fetch_authorization_code(self, patient):
        """Auto-fetch active authorization code for NHIA patient"""
        try:
            from nhia.models import AuthorizationCode
            # Get the most recent active authorization code for this patient
            auth_code = AuthorizationCode.objects.filter(
                patient=patient,
                status='active'
            ).order_by('-generated_at').first()
            
            if auth_code:
                # Pre-populate the field with the authorization code string
                self.fields['authorization_code_input'].initial = auth_code.code
        except ImportError:
            # NHIA app not available, skip auto-fetch
            pass
        except Exception:
            # Silently ignore any errors during auto-fetch
            pass

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
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        """Create a prescription from the form data"""
        if not self.consultation:
            raise ValueError("Consultation is required to create a prescription")

        from pharmacy.models import Prescription

        # Determine the doctor - use consultation doctor or fallback to current user
        doctor = self.consultation.doctor or self.user
        if not doctor:
            raise ValueError("A doctor must be specified for the prescription")

        # Create the prescription
        prescription = Prescription(
            patient=self.consultation.patient,
            doctor=doctor,
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