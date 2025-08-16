from django import forms
from django.utils import timezone
from .models import Ward, Bed, Admission, DailyRound, NursingNote, ClinicalRecord
from patients.models import Patient
from django.contrib.auth import get_user_model
User = get_user_model()
from doctors.models import Specialization, Doctor
from accounts.models import Department # Import Department model
from billing.models import Service # Import Service model

def get_specialization_choices():
    return [(s.id, s.name) for s in Specialization.objects.all()]

class WardForm(forms.ModelForm):
    class Meta:
        model = Ward
        fields = ['name', 'ward_type', 'floor', 'description', 'capacity', 'charge_per_day', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'ward_type': forms.Select(attrs={'class': 'form-select'}),
            'floor': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'charge_per_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class BedForm(forms.ModelForm):
    class Meta:
        model = Bed
        fields = ['ward', 'bed_number', 'description', 'is_active']
        widgets = {
            'ward': forms.Select(attrs={'class': 'form-select'}),
            'bed_number': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        ward = cleaned_data.get('ward')
        bed_number = cleaned_data.get('bed_number')
        
        # Check if this bed number already exists in the ward
        if ward and bed_number:
            if Bed.objects.filter(ward=ward, bed_number=bed_number).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(f"Bed number {bed_number} already exists in {ward.name}")
        
        return cleaned_data

class AdmissionForm(forms.ModelForm):
    # Authorization code field
    authorization_code = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Authorization Code (Optional)"
    )
    
    class Meta:
        model = Admission
        fields = ['patient', 'admission_date', 'bed', 'diagnosis', 'attending_doctor',
                  'reason_for_admission', 'admission_notes', 'admission_service']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select select2'}),
            'admission_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'bed': forms.Select(attrs={'class': 'form-select'}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'attending_doctor': forms.Select(attrs={'class': 'form-select select2'}),
            'reason_for_admission': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'admission_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'admission_service': forms.Select(attrs={'class': 'form-select'}),
        }

    admission_service = forms.ModelChoiceField(
        queryset=Service.objects.filter(name='Admission Fee'),
        empty_label=None,  # Ensures a service is always selected
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Admission Service'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show available beds
        if not self.instance.pk:  # Only for new admissions
            self.fields['bed'].queryset = Bed.objects.filter(is_occupied=False, is_active=True)
        
        # Filter doctors (users with doctor role)
        self.fields['attending_doctor'].queryset = User.objects.filter(profile__specialization__isnull=False)
        
        # Set initial admission date to now
        if not self.instance.pk and not self.initial.get('admission_date'):
            self.initial['admission_date'] = timezone.now().strftime('%Y-%m-%dT%H:%M')
            
        # Set authorization code queryset based on patient
        patient_id = self.initial.get('patient') or self.data.get('patient')
        if patient_id:
            try:
                patient_instance = Patient.objects.get(id=patient_id)
                if patient_instance.patient_type == 'nhia':
                    from nhia.models import AuthorizationCode
                    self.fields['authorization_code'].queryset = AuthorizationCode.objects.filter(
                        patient=patient_instance,
                        status='active'
                    ).order_by('-generated_at')
                else:
                    self.fields['authorization_code'].queryset = AuthorizationCode.objects.none()
            except Patient.DoesNotExist:
                self.fields['authorization_code'].queryset = AuthorizationCode.objects.none()
        else:
            self.fields['authorization_code'].queryset = AuthorizationCode.objects.none()

class DischargeForm(forms.ModelForm):
    class Meta:
        model = Admission
        fields = ['discharge_date', 'discharge_notes', 'status']
        widgets = {
            'discharge_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'discharge_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial discharge date to now
        if not self.initial.get('discharge_date'):
            self.initial['discharge_date'] = timezone.now().strftime('%Y-%m-%dT%H:%M')
        
        # Limit status choices to discharged, transferred, or deceased
        self.fields['status'].choices = [
            ('discharged', 'Discharged'),
            ('transferred', 'Transferred'),
            ('deceased', 'Deceased'),
        ]

class DailyRoundForm(forms.ModelForm):
    class Meta:
        model = DailyRound
        fields = ['date_time', 'doctor', 'notes', 'treatment_instructions', 
                  'medication_instructions', 'diet_instructions']
        widgets = {
            'date_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'doctor': forms.Select(attrs={'class': 'form-select select2'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'treatment_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'medication_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'diet_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter doctors (users with doctor role)
        self.fields['doctor'].queryset = User.objects.filter(profile__specialization__isnull=False)
        
        # Set initial date_time to now
        if not self.instance.pk and not self.initial.get('date_time'):
            self.initial['date_time'] = timezone.now().strftime('%Y-%m-%dT%H:%M')

class NursingNoteForm(forms.ModelForm):
    class Meta:
        model = NursingNote
        fields = ['date_time', 'nurse', 'notes', 'vital_signs', 'medication_given']
        widgets = {
            'date_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'nurse': forms.Select(attrs={'class': 'form-select select2'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'vital_signs': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'medication_given': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter nurses (users with nurse role)
        try:
            nursing_department = Department.objects.get(name='Nursing')
            self.fields['nurse'].queryset = User.objects.filter(profile__department=nursing_department)
        except Department.DoesNotExist:
            self.fields['nurse'].queryset = User.objects.none()
            print("Warning: 'Nursing' department not found. No nurses will be available.")
        
        # Set initial date_time to now
        if not self.instance.pk and not self.initial.get('date_time'):
            self.initial['date_time'] = timezone.now().strftime('%Y-%m-%dT%H:%M')

class AdmissionSearchForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Search by patient name or ID'
    }))
    
    status = forms.ChoiceField(required=False, choices=[('', 'All Statuses')] + list(Admission.STATUS_CHOICES),
                              widget=forms.Select(attrs={'class': 'form-select'}))
    
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={
        'class': 'form-control',
        'type': 'date',
        'placeholder': 'From Date'
    }))
    
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={
        'class': 'form-control',
        'type': 'date',
        'placeholder': 'To Date'
    }))
    
    doctor = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.filter(profile__specialization__isnull=False),
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    
    ward = forms.ModelChoiceField(
        required=False,
        queryset=Ward.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class ClinicalRecordForm(forms.ModelForm):
    class Meta:
        model = ClinicalRecord
        fields = [
            'record_type', 'date_time', 'notes',
            'temperature', 'blood_pressure_systolic', 'blood_pressure_diastolic',
            'heart_rate', 'respiratory_rate', 'oxygen_saturation',
            'medication_name', 'dosage', 'route',
            'treatment_description', 'patient_condition',
        ]
        widgets = {
            'record_type': forms.Select(attrs={'class': 'form-select'}),
            'date_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'blood_pressure_systolic': forms.NumberInput(attrs={'class': 'form-control'}),
            'blood_pressure_diastolic': forms.NumberInput(attrs={'class': 'form-control'}),
            'heart_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'respiratory_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'oxygen_saturation': forms.NumberInput(attrs={'class': 'form-control'}),
            'medication_name': forms.TextInput(attrs={'class': 'form-control'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control'}),
            'route': forms.TextInput(attrs={'class': 'form-control'}),
            'treatment_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'patient_condition': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get('date_time'):
            self.initial['date_time'] = timezone.now().strftime('%Y-%m-%dT%H:%M')

class PatientTransferForm(forms.Form):
    to_ward = forms.ModelChoiceField(queryset=Ward.objects.filter(is_active=True), required=True, label="Transfer to Ward")
    to_bed = forms.ModelChoiceField(queryset=Bed.objects.filter(is_active=True, is_occupied=False), required=True, label="Transfer to Bed")
    notes = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        self.current_bed = kwargs.pop('current_bed', None)
        super().__init__(*args, **kwargs)
        self.fields['to_bed'].queryset = Bed.objects.none() # Initialize with empty queryset

        # Get the ward_id from either submitted data or initial data
        ward_id = None
        if 'to_ward' in self.data:
            ward_id = self.data.get('to_ward')
        elif self.initial.get('to_ward'):
            # If initial data is a Ward object, get its ID
            ward_id = self.initial.get('to_ward').id if isinstance(self.initial.get('to_ward'), Ward) else self.initial.get('to_ward')

        if ward_id:
            try:
                ward_id = int(ward_id)
                self.fields['to_bed'].queryset = Bed.objects.filter(ward_id=ward_id, is_active=True, is_occupied=False).order_by('bed_number')
            except (ValueError, TypeError):
                pass # Handle invalid ward_id gracefully
